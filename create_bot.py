from requests import post

from config import API_BASE, USER_AUTH_COOKIE

# System Messages
PERSONALITY_GEN_SYSTEM = open('user_templates/personality_gen.txt').read()


def _create_bot(username: str, personality: str):
    print('Creating bot user:', username, personality)
    resp = post(API_BASE + '/users',
                json={'username': username, 'persona': personality},
                cookies=USER_AUTH_COOKIE).json()
    if 'error' in resp:
        print('Failed to create user:', resp['error'])
    else:
        print('User created: id=' + resp['id'])


def create_bots(n: int = 1):
    from main import client
    response = client.chat.completions.create(
        model='gpt-4-turbo-2024-04-09',
        messages=[{
            'role': 'user_templates',
            'content': PERSONALITY_GEN_SYSTEM
        }],
        temperature=1.1,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0.5,
        presence_penalty=0.5,
        n=n
    )
    for resp in response.choices:
        for persona in resp.message.content.split('\n\n'):
            print(persona)
            username, personality = persona.split('\n', 1)
            _create_bot(username.strip(), personality.strip())
    print('Done!')
