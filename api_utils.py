from typing import Iterable
from requests import get

from config import API_BASE
from data_objects import Post


def get_posts() -> Iterable[Post]:
    return get(API_BASE + '/posts').json(object_hook=lambda d: Post.Post(**d))
