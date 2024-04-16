import json
import logging
from typing import Iterable, Any

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionMessage

import api_utils
from data_objects.Post import Post

AGENT_SYSTEM = open('user_templates/agent.txt').read()
ACTIONS = json.load(open('user_templates/actions.json'))
INSTRUCTIONS = json.load(open('user_templates/instructions.json'))


def _parse_raw_action(raw_action: str) -> (str, str):
    action, payload = raw_action.split('\n', 1)
    return action, payload


def _format_post(post: Post) -> str:
    return f'ID: {post.id}\nVotes: {post.votes}\n<<TITLE>>\n{post.title}\n<<BODY>>\n{post.content}'


def _get_formatted_posts(posts: Iterable[Post]) -> str:
    return '\n\n'.join([_format_post(post) for post in posts])


def _get_model_message(messages: Iterable[ChatCompletionMessageParam]) -> (ChatCompletionMessage, Any):
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
        print('WARN: Completion did not finish normally: ' + response.choices[0].finish_reason)
    return choice.message, json.loads(choice.message.content)


def _truncate_to_max_length(in_str: str, n: int = 100) -> str:
    if len(in_str) <= n:  # Already short enough
        return in_str
    return in_str[:n] + '...'


# Shrink response to reduce context usage
def _summarise_response(action: str, response: Any) -> str:
    match action:
        case 'CREATE':
            response['body'] = _truncate_to_max_length(response['body'])
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
        self.last_read = 0
        # This is lazily fetched once required
        self.token: str | None = None

    def get_token(self) -> str:
        self.log.debug('Token does not exist, requesting...')
        if self.token is None:
            self.token = api_utils.get_full_bot_user(self.user_id).token
        return self.token

    def get_actions(self) -> Iterable[str]:
        actions = ['COMMENT', 'VOTE', 'CREATE']
        if self.last_read > 5:
            actions += ['READ']
        actions += ['footer']
        return 'Actions:\n' + '\n'.join([ACTIONS[act] for act in actions])

    def handle_action(self, action: Any, payload: Any | None):
        match action['action']:
            case 'READ':
                self.last_read = 0
            case 'COMMENT':
                self.log.info('Created comment with ID: %s',
                              api_utils.create_comment(action['id'], payload, self.get_token()))
            case 'CREATE':
                self.log.info('Created post with ID: %s',
                              api_utils.create_post(payload['title'], payload['body'], self.get_token()))

    def run_agent_turn(self):
        self.log.info('Running turn...')
        # Maintain our own copy of messages because we do not want to overly
        # inflate the context of the "master" messages.
        messages = self.messages[:]
        if len(messages) != 1:
            messages += [{
                'role': 'user',
                'content': self.get_actions()
            }]

        # Get action
        action_msg, action = _get_model_message(messages)
        logging.debug('Took action: %s', action)
        if action['action'] not in INSTRUCTIONS:
            logging.error('Model returned invalid action!')
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
        payload_msg, payload = _get_model_message(messages)
        logging.debug('Action payload:', payload)
        self.handle_action(action, payload)

        # Update master messages state with the minimum of what's required to maintain stateful-ness
        self.last_read += 1
        self.messages += [{
            'role': 'user',
            'content': 'Actions removed'
        }, {
            'role': action_msg.role,
            'content': action_msg.content
        }, {
            'role': 'user',
            'content': 'Instructions removed'
        }, {
            'role': payload_msg.role,
            'content': _summarise_response(action['action'], payload)
        }]
        print(json.dumps(self.messages, indent=2, ensure_ascii=False))
