from typing import Iterable

from openai.types.chat import ChatCompletionMessageParam

import api_utils
from data_objects import Post

AGENT_SYSTEM = open('system/agent.txt').read()
ACTIONS = {
    'COMMENT': 'COMMENT on a post - include post ID, then follow COMMENT INSTRUCTIONS',
    'VOTE': 'VOTE a post up or down - include post ID, then follow VOTE INSTRUCTIONS',
    'CREATE': 'CREATE a post - follow POST INSTRUCTIONS',
    'READ': 'READ latest curated posts'
}


def _parse_raw_action(raw_action: str) -> (str, str):
    action, payload = raw_action.split('\n', 1)
    return action, payload


def _format_post(post: Post.Post) -> str:
    return f'ID: {post.id}\nVotes: {post.votes}\n<<TITLE>>\n{post.title}\n<<BODY>>\n{post.content}'


def _get_formatted_posts() -> str:
    return '\n\n'.join([_format_post(post) for post in api_utils.get_posts()])


class Agent:
    def __init__(self, personality: str):
        self.messages: Iterable[ChatCompletionMessageParam] = [{
            'role': 'system',
            'content': AGENT_SYSTEM
            .replace('{{PERSONALITY}}', personality)
            .replace('{{POSTS}}', _get_formatted_posts())
        }]
        self.last_read = 0

    def get_actions(self) -> Iterable[str]:
        actions = ['COMMENT', 'VOTE', 'CREATE']
        if self.last_read > 5:
            actions += ['READ']
        return [ACTIONS[act] for act in actions]

    def take_action(self):
        from main import client
        response = client.chat.completions.create(
            model='gpt-4-turbo-2024-04-09',
            messages=self.messages,
            temperature=1.2,
            max_tokens=1024,
            top_p=1,
            frequency_penalty=0.3,
            presence_penalty=0.3
        )
        if response.choices[0].finish_reason != 'stop':
            print('WARN: Completion did not finish normally: ' + response.choices[0].finish_reason)
        message = response.choices[0].message
        print('Message', message)
        _parse_raw_action(message.content)
        self.last_read += 1
        self.messages += [{
            'role': message.role,
            'content': message.content
        }, {
            'role': 'user',
            'content': f'Actions:\n{'\n'.join(self.get_actions())}'
        }]
        print(self.messages)
