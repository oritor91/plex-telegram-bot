from pydantic import BaseModel
import libtorrent as lt
from typing import List
import time


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


class TorrentData(BaseModel):
    torrent_link: str | None = None


class MovieData(BaseModel):
    movie_name: str | None = None
    movie_link: str | None = None


class UserData(BaseModel):
    parsed: List[ParsedURL] | None = None
    show_name: str | None = None
    episode_name: str | None = None
    torrent_data: TorrentData | None = None
    movie_data: MovieData | None = None


def download_torrent(torrent_link: str, save_path: str):
    ses = lt.session()
    ses.listen_on(6881, 6891)
    params = {
        "save_path": save_path,
        "storage_mode": lt.storage_mode_t(2),
    }

    handle = lt.add_magnet_uri(ses, torrent_link, params)
    ses.start_dht()

    while not handle.has_metadata():
        time.sleep(1)

    while handle.status().state != lt.torrent_status.seeding:
        time.sleep(5)
