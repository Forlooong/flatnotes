from helpers import CustomBaseModel


class AttachmentCreateResponse(CustomBaseModel):
    filename: str
    url: str


class DraftAttachments(CustomBaseModel):
    content: str = ""
    settled: list[str] = []
    discard: bool = False
