from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


END_MARKER_KEY = "__activewatcher_end__"


class StateEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bucket: str = Field(min_length=1)
    source: str = Field(min_length=1)
    ts: datetime
    data: dict[str, Any]

    @field_validator("ts")
    @classmethod
    def _ts_tz_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("ts must be timezone-aware (include offset or Z)")
        return value
