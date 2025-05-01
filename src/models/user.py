from pydantic import BaseModel


class User(BaseModel):
    room: str
    name: str
    messages: list
