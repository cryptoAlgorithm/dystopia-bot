from openai import OpenAI
from requests import get, post

import api_utils
from Agent import Agent
from create_bot import create_bots

# Make sure OPENAI_API_KEY is present in environment!
client = OpenAI(organization='org-DrgppktFvIb3ZHGMN0Jyd0cg')


if __name__ == '__main__':
    # create_bots(5)
    test = Agent('Optimistic Overthinker: An insatiably hopeful life coach grappling with overthinking tendencies, often drowning in endless possibilities and crippling perfectionism—styles dialogue as encouraging yet perpetually anxious.')
    for i in range(3):
        test.take_action()
    # print(api_utils.get_posts())
