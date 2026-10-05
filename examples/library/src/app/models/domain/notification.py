from pydantic import BaseModel, ConfigDict


class Notification(BaseModel):
    model_config = ConfigDict(frozen=True)

    recipient: str
    subject: str
    body: str
