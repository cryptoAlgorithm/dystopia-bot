from typing import Iterable
from requests import get, post

from config import API_BASE, USER_AUTH_COOKIE, AUTH_COOKIE_NAME
from data_objects.Post import Post
from data_objects.User import User


# Posts #
def get_posts() -> Iterable[Post]:
    return get(API_BASE + '/posts').json(object_hook=lambda d: Post(**d))


def create_post(title: str, body: str, bot_token: str) -> str:
    return post(
        API_BASE + '/posts', json={'title': title, 'body': body},
        cookies={AUTH_COOKIE_NAME: bot_token}
    ).json()['id']


def create_comment(post_id: str, content: str, bot_token: str) -> str:
    return post(
        API_BASE + f'/posts/{post_id}/comments', json={'content': content},
        cookies={AUTH_COOKIE_NAME: bot_token}
    ).json()['id']


# Users #
def get_bot_users() -> Iterable[User]:
    return get(API_BASE + '/users', cookies=USER_AUTH_COOKIE).json(object_hook=lambda d: User(**d))


def get_full_bot_user(user_id: str) -> User:
    return User(**get(API_BASE + f'/users/{user_id}', cookies=USER_AUTH_COOKIE).json())
