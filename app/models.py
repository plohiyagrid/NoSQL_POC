from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class ActivityType(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    PAGE_VIEW = "page_view"
    SEARCH = "search"
    PURCHASE = "purchase"
    PROFILE_UPDATE = "profile_update"


@dataclass(frozen=True)
class ActivityLog:
    user_id: UUID
    activity_id: UUID
    activity_type: str
    timestamp: datetime
    details: str | None = None

    def to_dict(self) -> dict:
        return {
            "user_id": str(self.user_id),
            "activity_id": str(self.activity_id),
            "activity_type": self.activity_type,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }
