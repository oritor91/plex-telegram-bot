from pydantic import BaseModel
from typing import List


class ParsedURL(BaseModel):
    chat_id: int | None = None
    message_id: int
    username: str | None = None

    def set_chat_id(cls, v, values):
        if "username" in values and values["username"]:
            return None
        return int(v) if v else None

    def set_username(cls, v, values):
        if "chat_id" in values and values["chat_id"]:
            return None
        return v


class MovieData(BaseModel):
    movie_name: str | None = None
    movie_link: str | None = None


class UserData(BaseModel):
    parsed: List[ParsedURL] | None = None
    show_name: str | None = None
    episode_name: str | None = None
    movie_data: MovieData | None = None
