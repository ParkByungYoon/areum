from fastapi import APIRouter, Depends
from pydantic import BaseModel
from api.deps import get_db_path
from storage.prayer_store import save_prayer, find_connection

router = APIRouter()


class PrayerRequest(BaseModel):
    user_id: str
    concern: str
    episode_id: str
    subtitle: str
    passage_ref: str


class ConnectionRequest(BaseModel):
    user_id: str
    concern: str
    episode_id: str


@router.post("/prayer")
def post_prayer(body: PrayerRequest, db_path: str = Depends(get_db_path)):
    return save_prayer(
        body.user_id, body.concern, body.episode_id, body.subtitle, body.passage_ref, db_path
    )


@router.post("/connection")
def post_connection(body: ConnectionRequest, db_path: str = Depends(get_db_path)):
    return find_connection(body.user_id, body.concern, body.episode_id, db_path)
