from pydantic import ValidationError
import pytest

from feeds.contracts import (
    ContentItem,
    ContentMetadata,
    ForwardAttribution,
    MetadataOnlyContent,
    OriginReference,
    SemanticTextContent,
)


pytestmark = pytest.mark.protected


def _semantic_item() -> ContentItem:
    return ContentItem(
        item_id="item-1",
        batch_id="batch-1",
        stream_id="stream-1",
        normalized_content=SemanticTextContent(
            semantic_text="Вышла новая версия продукта.",
            metadata=ContentMetadata(
                content_type="link",
                media_count=0,
                links=("https://example.com/release",),
                forward_attribution=ForwardAttribution(
                    username_snapshot="forwarded_source",
                ),
            ),
        ),
        origin=OriginReference(
            username_snapshot="source_channel",
            title_snapshot="Source Channel",
            message_ids=(101,),
            public_url="https://t.me/source_channel/101",
        ),
    )


def test_creates_semantic_item_through_the_public_contract() -> None:
    item = _semantic_item()

    assert item.item_id == "item-1"
    assert item.normalized_content.semantic_text == "Вышла новая версия продукта."
    assert item.origin.message_ids == (101,)


def test_metadata_only_content_rejects_semantic_text() -> None:
    with pytest.raises(ValidationError):
        MetadataOnlyContent(
            semantic_text="Этот текст не должен быть представим.",
            metadata=ContentMetadata(
                content_type="photo",
                media_count=1,
            ),
        )


def test_creates_metadata_only_content_without_a_text_field() -> None:
    content = MetadataOnlyContent(
        metadata=ContentMetadata(
            content_type="photo",
            media_count=1,
        ),
    )

    assert content.mode == "metadata_only"
    assert "semantic_text" not in type(content).model_fields


def test_content_item_is_immutable_after_creation() -> None:
    item = _semantic_item()

    with pytest.raises(ValidationError):
        item.item_id = "changed-item"


def test_nested_contract_values_are_immutable() -> None:
    item = _semantic_item()

    with pytest.raises(ValidationError):
        item.origin.title_snapshot = "Changed title"


def test_ordered_collections_reject_mutable_inputs() -> None:
    with pytest.raises(ValidationError):
        OriginReference(
            username_snapshot="source_channel",
            title_snapshot="Source Channel",
            message_ids=[101],
            public_url="https://t.me/source_channel/101",
        )


@pytest.mark.parametrize("field_name", ("item_id", "batch_id", "stream_id"))
def test_application_identifiers_are_nonempty(field_name: str) -> None:
    item_data = _semantic_item().model_dump()
    item_data[field_name] = ""

    with pytest.raises(ValidationError):
        ContentItem.model_validate(item_data)


@pytest.mark.parametrize(
    "field_name",
    ("username_snapshot", "title_snapshot"),
)
def test_origin_snapshots_are_nonempty(field_name: str) -> None:
    origin_data = _semantic_item().origin.model_dump()
    origin_data[field_name] = ""

    with pytest.raises(ValidationError):
        OriginReference.model_validate(origin_data)


def test_forward_attribution_requires_a_visible_snapshot() -> None:
    with pytest.raises(ValidationError):
        ForwardAttribution()


def test_media_count_is_nonnegative() -> None:
    with pytest.raises(ValidationError):
        ContentMetadata(
            content_type="photo",
            media_count=-1,
        )


@pytest.mark.parametrize(
    "message_ids",
    ((), (0,), (101, 101), (102, 101)),
)
def test_origin_message_ids_are_positive_unique_and_ascending(
    message_ids: tuple[int, ...],
) -> None:
    with pytest.raises(ValidationError):
        OriginReference(
            username_snapshot="source_channel",
            title_snapshot="Source Channel",
            message_ids=message_ids,
            public_url="https://t.me/source_channel/101",
        )


@pytest.mark.parametrize(
    "public_url",
    (
        "http://t.me/source_channel/101",
        "https://user:password@t.me/source_channel/101",
        "https://t.me/other_channel/101",
        "https://t.me/source_channel/102",
    ),
)
def test_origin_url_is_canonical_and_has_no_credentials(
    public_url: str,
) -> None:
    with pytest.raises(ValidationError):
        OriginReference(
            username_snapshot="source_channel",
            title_snapshot="Source Channel",
            message_ids=(101, 102),
            public_url=public_url,
        )


def test_semantic_variant_requires_nonempty_text() -> None:
    with pytest.raises(ValidationError):
        SemanticTextContent(
            semantic_text="",
            metadata=ContentMetadata(
                content_type="text",
                media_count=0,
            ),
        )


def test_public_contract_exposes_only_the_normative_fields() -> None:
    assert tuple(ContentItem.model_fields) == (
        "item_id",
        "batch_id",
        "stream_id",
        "normalized_content",
        "origin",
    )
    assert tuple(OriginReference.model_fields) == (
        "username_snapshot",
        "title_snapshot",
        "message_ids",
        "public_url",
    )
