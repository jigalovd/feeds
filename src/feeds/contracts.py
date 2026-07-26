from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
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


class MessageCursor(ContractModel):
    kind: Literal["message"] = "message"
    message_id: NonNegativeInt


class TimeCursor(ContractModel):
    kind: Literal["time"] = "time"
    after: AwareDatetime

    @field_validator("after")
    @classmethod
    def normalize_after_to_utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


CursorBefore = Annotated[
    MessageCursor | TimeCursor,
    Field(discriminator="kind"),
]


class _BatchContract(ContractModel):
    status: str
    batch_id: OpaqueId
    run_id: OpaqueId
    stream_id: OpaqueId
    cursor_before: CursorBefore
    cursor_after: MessageCursor
    captured_at: AwareDatetime

    @field_validator("captured_at")
    @classmethod
    def normalize_captured_at_to_utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_ordered_cursor_bounds(self) -> Self:
        if (
            isinstance(self.cursor_before, TimeCursor)
            and self.cursor_before.after >= self.captured_at
        ):
            raise ValueError(
                "time cursor lower bound must precede capture time",
            )
        if (
            isinstance(self.cursor_before, MessageCursor)
            and self.cursor_after.message_id < self.cursor_before.message_id
        ):
            raise ValueError(
                "message cursor upper bound must not precede lower bound",
            )
        return self


class CapturingBatch(_BatchContract):
    status: Literal["capturing"] = "capturing"


class CompleteBatch(_BatchContract):
    status: Literal["complete"] = "complete"
    items: tuple[ContentItem, ...]


CaptureBatch = Annotated[
    CapturingBatch | CompleteBatch,
    Field(discriminator="status"),
]
