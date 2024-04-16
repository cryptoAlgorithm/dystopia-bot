import os

API_BASE = 'http://localhost:3000/api'
AUTH_COOKIE_NAME = 'd-session'
USER_AUTH_COOKIE = {
    AUTH_COOKIE_NAME: os.environ['USER_AUTH_TOKEN']
}
