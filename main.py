from random import choice

from openai import OpenAI

import api_utils
from Agent import Agent

# Make sure OPENAI_API_KEY is present in environment!
client = OpenAI(organization='org-DrgppktFvIb3ZHGMN0Jyd0cg')


def create_agents() -> list[Agent]:
    bot_users = api_utils.get_bot_users()
    initial_posts = api_utils.get_posts()
    agents: list[Agent] = []
    for bot_user in bot_users:
        agents += [Agent(bot_user.id, bot_user.personality, initial_posts)]
    return agents


def main():
    agents = create_agents()
    for _ in range(10):
        choice(agents).run_agent_turn()


if __name__ == '__main__':
    # create_bots(5)
    main()
