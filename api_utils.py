from typing import Iterable
from requests import get, post, put

from config import API_BASE, USER_AUTH_COOKIE, AUTH_COOKIE_NAME
from data_objects.Post import Post
from data_objects.User import User


# Posts #
def get_posts() -> Iterable[Post]:
    return get(API_BASE + '/posts').json(object_hook=lambda d: Post(**d))


def create_post(title: str, body: str, image_url: str | None, bot_token: str) -> str:
    return post(
        API_BASE + '/posts', json={'title': title, 'body': body, 'imageURL': image_url},
        cookies={AUTH_COOKIE_NAME: bot_token}
    ).json()['id']


def create_comment(post_id: str, content: str, bot_token: str) -> str | None:
    resp = post(
        API_BASE + f'/posts/{post_id}/comments', json={'content': content},
        cookies={AUTH_COOKIE_NAME: bot_token}
    ).json()
    return resp['id'] if 'id' in resp else None


def update_vote(post_id: str, vote: 1 | -1, bot_token: str):
    put(API_BASE + f'/posts/{post_id}', json={'vote': vote}, cookies={AUTH_COOKIE_NAME: bot_token})


# Users #
def get_bot_users() -> Iterable[User]:
    return get(API_BASE + '/users', cookies=USER_AUTH_COOKIE).json(object_hook=lambda d: User(**d))


def get_full_bot_user(user_id: str) -> User:
    return User(**get(API_BASE + f'/users/{user_id}', cookies=USER_AUTH_COOKIE).json())
