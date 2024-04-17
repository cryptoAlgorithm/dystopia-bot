class Comment:
    def __init__(self, _id: str, content: str, parent: str, user: str, username: str, at: str, **_kwargs):
        self.id = _id
        self.username = username
        self.content = content
        self.user = user
        self.at = at

    def __repr__(self) -> str:
        return f'<Comment: {self.content}>'
