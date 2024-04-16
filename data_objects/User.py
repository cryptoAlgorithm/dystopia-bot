class User:
    def __init__(self, _id: str, username: str, persona: str, token: str | None = None, **_kwargs):
        self.id = _id
        self.username = username
        self.personality = persona
        self.token = token

    def __repr__(self) -> str:
        return f'<User: {self.username}>'
