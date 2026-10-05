from pydantic import BaseModel, ConfigDict


class Notification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    recipient: str
    subject: str
    body: str
