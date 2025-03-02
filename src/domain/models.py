from pydantic import BaseModel, StrictStr


class Paper(BaseModel):
    title: StrictStr
    category: list[StrictStr]
    brief_digest: StrictStr
    url: StrictStr
    summary: dict[StrictStr, StrictStr]
