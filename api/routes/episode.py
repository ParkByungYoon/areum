from fastapi import APIRouter, Depends, HTTPException
from core.matcher import EpisodeMatcher
from api.deps import get_matcher

router = APIRouter()


@router.get("/episode/{episode_id:path}")
def get_episode(episode_id: str, matcher: EpisodeMatcher = Depends(get_matcher)):
    for ep in matcher.episodes:
        if ep["subtitle"] == episode_id:
            return {"episode_id": ep["subtitle"], **ep}
    raise HTTPException(status_code=404, detail="Episode not found")
