import json
import logging
from typing import Iterable, Any

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionMessage

import api_utils
import image_utils
from data_objects.Post import Post

AGENT_SYSTEM = open('user_templates/agent.txt').read()
ACTIONS = json.load(open('user_templates/actions.json'))
INSTRUCTIONS = json.load(open('user_templates/instructions.json'))


def _parse_raw_action(raw_action: str) -> (str, str):
    action, payload = raw_action.split('\n', 1)
    return action, payload


def _format_post(post: Post, truncate_length: int | None = 100) -> str:
    return f'{post.id}:{{"votes":{post.votes},"title":"{post.title}","body":"{_truncate_to_max_length(post.content, 100) if truncate_length is not None else post.content}"}}'


def _get_formatted_posts(posts: Iterable[Post]) -> str:
    return '\n\n'.join([_format_post(post) for post in posts])


def _get_formatted_comments(post_id: str) -> str:
    return '\n\n'.join([f'{comment.username}: {comment.content}' for comment in api_utils.get_comments(post_id)])


def _truncate_to_max_length(in_str: str, n: int = 100) -> str:
    if len(in_str) <= n:  # Already short enough
        return in_str
    return in_str[:n] + '...'


# Shrink response to reduce context usage
def _summarise_response(action: str, response: Any) -> str:
    match action:
        case 'CREATE':
            response['body'] = _truncate_to_max_length(response['body'])
            response['image'] = _truncate_to_max_length(response['image'])
            return json.dumps(response)
    return str(response)  # Make sure we return strings, otherwise subsequent completions will fail


class Agent:
    def __init__(self, bot_user_id: str, personality: str, initial_posts: Iterable[Post] = api_utils.get_posts()):
        self.log = logging.getLogger(f'Agent({bot_user_id})')
        self.log.setLevel(logging.DEBUG)  # Lower log level to debug, so we see all of our own messages

        self.user_id = bot_user_id
        self.messages: list[ChatCompletionMessageParam] = [{
            'role': 'system',
            'content': AGENT_SYSTEM
            .replace('{{PERSONALITY}}', personality)
            .replace('{{POSTS}}', 'Here are some posts to get you started:\n\n' + _get_formatted_posts(initial_posts))
        }]
        # This is lazily fetched once required
        self.token: str | None = None
        self.viewed_post_id: str | None = None

        # Keep track of cost incurred
        self.cost = 0

    def prune_history(self, target_n: int):
        # Remove excess history
        # noop
        """removed_n = 0
        while len(self.messages) > target_n or len(self.messages) % 4 != 0:
            self.messages.pop(1)
            removed_n += 1
        self.log.debug('Pruned %d messages', removed_n)"""

    def _get_model_message(self, messages: Iterable[ChatCompletionMessageParam]) -> (ChatCompletionMessage, Any):
        """
        Gets a response from the model
        :param messages: Previous messages to include
        :return: Tuple of returned message and parsed content
        """
        from main import client
        response = client.chat.completions.create(
            model='gpt-4-turbo-2024-04-09',
            messages=messages,
            temperature=1.2,
            max_tokens=512,
            top_p=1,
            frequency_penalty=0.3,
            presence_penalty=0.3,
            logit_bias={63: -100, 14196: -100, 74694: -100}  # Prevent including backticks in output
        )
        choice = response.choices[0]
        if choice.finish_reason != 'stop':
            self.log.warning('Completion did not finish normally: %s', response.choices[0].finish_reason)
        # Output usage for tracking purposes
        cost = response.usage.prompt_tokens * 0.00001 + response.usage.completion_tokens * 0.00003
        self.log.debug('Completion tokens: prompt=%d, response=%d, total=%d => cost=$%.4fUSD',
                       response.usage.prompt_tokens, response.usage.completion_tokens, response.usage.total_tokens,
                       cost)
        self.cost += cost
        return choice.message, json.loads(choice.message.content)

    def get_token(self) -> str:
        """
        Get a Dystopia API token for this bot user
        :return: A token that can be used to authenticate against the Dystopia API
        """
        if self.token is None:
            self.log.debug('Token does not exist, requesting...')
            self.token = api_utils.get_full_bot_user(self.user_id).token
        return self.token

    def get_actions(self) -> str:
        actions = ['VIEW', 'VOTE']
        # Let agent read new posts if it hasn't done so in 5 turns
        # Temporarily disabled (not implemented)
        # if self.last_read > 5:
        #     actions += ['READ']
        if self.viewed_post_id is not None:  # Agent currently 'viewing' a post
            actions += ['COMMENT']
        else:
            actions += ['CREATE']
        actions += ['footer']
        return 'You MUST reply with one of the following actions:\n' + '\n'.join([ACTIONS[act] for act in actions])

    def handle_action(self, action: Any, payload: Any | None):
        match action['action']:
            case 'COMMENT':
                if self.viewed_post_id is None:
                    self.log.error('Cannot comment without prior VIEW!')
                    return
                self.log.info('Created comment with ID: %s',
                              api_utils.create_comment(self.viewed_post_id, payload, self.get_token()))
                self.viewed_post_id = None
            case 'CREATE':
                image_url: str | None = None
                if 'image' in payload and isinstance(payload['image'], str) and payload['image'].strip() != '':
                    image_url = image_utils.generate_image_and_upload(payload['image'].strip())
                    self.cost += 0.08
                self.log.info('Created post with ID: %s',
                              api_utils.create_post(payload['title'], payload['body'], image_url, self.get_token()))
            case 'VOTE':
                api_utils.update_vote(action['id'], payload, self.get_token())
                self.log.info('Updated vote for post: id=%s, vote=%d', action['id'], payload)

    def run_agent_turn(self):
        self.log.info('Running turn...')
        # Maintain our own copy of messages because we do not want to overly
        # inflate the context of the "master" messages.
        messages = self.messages[:]
        if self.messages[-1]['role'] == 'assistant':  # Output actions if the previous message was from the assistant
            messages += [{
                'role': 'user',
                'content': self.get_actions()
            }]
            self.messages += [{
                'role': 'user',
                'content': 'Actions removed'
            }]

        # Get action
        action_msg, action = self._get_model_message(messages)
        self.log.debug('Took action: %s', str(action))
        if 'action' not in action:
            self.log.error('Payload does not contain action!')
            return

        self.messages += [{
            'role': action_msg.role,
            'content': action_msg.content
        }]

        # Specially handle VIEW action
        if action['action'] == 'VIEW':
            self.viewed_post_id = action['id']
            self.messages += [{
                'role': 'user',
                'content': _format_post(api_utils.get_post(self.viewed_post_id), None)
                + '\nComments:\n' + _get_formatted_comments(self.viewed_post_id)
                + '\n\n---\n\n'
                + self.get_actions()
            }]
            self.run_agent_turn()
            return

        if action['action'] not in INSTRUCTIONS:
            self.log.error('Model returned invalid action!')
            return

        # Add instructions
        messages += [{
            'role': action_msg.role,
            'content': action_msg.content
        }, {
            'role': 'user',
            'content': INSTRUCTIONS[action['action']]
        }]

        # Get action payload and handle action
        payload_msg, payload = self._get_model_message(messages)
        self.log.debug('Action payload: %s', str(payload))
        try:
            self.handle_action(action, payload)
        except Exception as e:
            self.log.error('Action handle error: %s, payload: %s', str(e), str(payload))
            return

        # Update master messages state with the minimum of what's required to maintain stateful-ness
        # self.last_read += 1
        self.messages += [{
            'role': 'user',
            'content': 'Instructions removed'
        }, {
            'role': payload_msg.role,
            'content': _summarise_response(action['action'], payload)
        }]
        self.prune_history(12)
        # print(json.dumps(self.messages, indent=2, ensure_ascii=False))
