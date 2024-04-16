class Post:
    def __init__(self, _id: str, title: str, content: str, voteCount: int, at: str, user: str, username: str, **_kwargs):
        self.id = _id
        self.title = title
        self.content = content
        self.votes = voteCount
        self.postedAt = at
        self.author_id = user
        self.author_username = username

    def __repr__(self):
        return f'<Post: id={self.id}, title={self.title}, content={self.content}>'
