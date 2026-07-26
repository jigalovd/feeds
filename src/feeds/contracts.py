from typing import Annotated, Literal, Self

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    StringConstraints,
    field_validator,
    model_validator,
)


ContentType = Literal[
    "text",
    "link",
    "poll",
    "photo",
    "video",
    "audio",
    "voice",
    "document",
    "album",
    "other_media",
]
NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
OpaqueId = NonEmptyString


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ForwardAttribution(ContractModel):
    username_snapshot: NonEmptyString | None = None
    title_snapshot: NonEmptyString | None = None

    @model_validator(mode="after")
    def require_visible_snapshot(self) -> Self:
        if self.username_snapshot is None and self.title_snapshot is None:
            raise ValueError("forward attribution requires a visible snapshot")
        return self


class ContentMetadata(ContractModel):
    content_type: ContentType
    media_count: NonNegativeInt
    links: tuple[AnyHttpUrl, ...] = ()
    forward_attribution: ForwardAttribution | None = None


class SemanticTextContent(ContractModel):
    mode: Literal["semantic_text"] = "semantic_text"
    semantic_text: NonEmptyString
    metadata: ContentMetadata


class MetadataOnlyContent(ContractModel):
    mode: Literal["metadata_only"] = "metadata_only"
    metadata: ContentMetadata


NormalizedContent = Annotated[
    SemanticTextContent | MetadataOnlyContent,
    Field(discriminator="mode"),
]


class OriginReference(ContractModel):
    username_snapshot: NonEmptyString
    title_snapshot: NonEmptyString
    message_ids: tuple[PositiveInt, ...]
    public_url: AnyHttpUrl

    @field_validator("message_ids")
    @classmethod
    def require_unique_ascending_message_ids(
        cls,
        value: tuple[int, ...],
    ) -> tuple[int, ...]:
        if not value:
            raise ValueError("origin requires at least one message ID")
        if tuple(sorted(set(value))) != value:
            raise ValueError("message IDs must be unique and ascending")
        return value

    @model_validator(mode="after")
    def require_canonical_public_url(self) -> Self:
        expected_url = (
            f"https://t.me/{self.username_snapshot}/{self.message_ids[0]}"
        )
        if str(self.public_url) != expected_url:
            raise ValueError("public URL must match the canonical origin URL")
        return self


class ContentItem(ContractModel):
    item_id: OpaqueId
    batch_id: OpaqueId
    stream_id: OpaqueId
    normalized_content: NormalizedContent
    origin: OriginReference
