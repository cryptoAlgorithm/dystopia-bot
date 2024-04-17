import json
import logging
import threading
from random import choice

from openai import OpenAI

import api_utils
from Agent import Agent

logging.basicConfig()

# Ensure OPENAI_API_KEY is present in environment!
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

    def agent_runner():
        agent = choice(agents)
        for _ in range(10):
            agent.run_agent_turn()
        print('Final agent conversation:', json.dumps(agent.messages, indent=2, ensure_ascii=False))
        print('Total agent cost ($USD):', agent.cost)

    runner_threads = [threading.Thread(target=agent_runner) for _ in range(1)]
    for thread in runner_threads:
        thread.start()
    for thread in runner_threads:
        thread.join()


if __name__ == '__main__':
    # create_bots(5)
    main()
    # k = image_utils.generate_image_and_upload('A vivid scene depicting a small medieval army clad in historically accurate armor without fantasy elements, standing on a grassy field under a cloudy sky. The soldiers are in various stances, some mounting horses, others strategizing around a wooden table with primitive maps.')
    # print(k)
