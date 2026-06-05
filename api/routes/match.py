from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from core.matcher import EpisodeMatcher
from api.deps import get_matcher

router = APIRouter()


class MatchRequest(BaseModel):
    concern: str

    @field_validator("concern")
    @classmethod
    def concern_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("concern must not be empty")
        return v


@router.post("/match")
def match(body: MatchRequest, matcher: EpisodeMatcher = Depends(get_matcher)):
    episodes = matcher.match(body.concern, top_n=3)
    return [
        {
            "episode_id": ep["subtitle"],
            "subtitle": ep["subtitle"],
            "situation": ep.get("situation", ""),
        }
        for ep in episodes
    ]
