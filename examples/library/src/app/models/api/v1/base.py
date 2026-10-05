from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Base of every API schema: camelCase on the wire, snake_case in Python, frozen."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)
