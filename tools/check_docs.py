#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


EXPLICIT_ANCHOR_PATTERN = re.compile(
    r"""<a\s+(?:id|name)=["'](?P<id>[^"']+)["']\s*></a>""",
    re.IGNORECASE,
)
HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+(?P<heading>.+?)\s*#*\s*$")
LINK_PATTERN = re.compile(
    r"""\[[^\]]+\]\((?P<target><[^>]+>|[^)\s]+)(?:\s+["'][^"']*["'])?\)"""
)
EXTERNAL_TARGET_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
UNFINISHED_MARKER_PATTERN = re.compile(
    r"\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b",
    re.IGNORECASE,
)
NORMATIVE_METADATA = (
    "Статус",
    "Владелец фактов",
    "Читать когда",
    "Связанные документы",
)
IGNORED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".idea",
        ".pytest_cache",
        ".venv",
        "__pycache__",
    }
)


@dataclass(frozen=True, order=True)
class Issue:
    code: str
    path: str
    detail: str


def normalized_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def relative_workspace_path(workspace: Path, path: Path) -> str:
    full_path = path.resolve()
    try:
        return full_path.relative_to(workspace).as_posix()
    except ValueError:
        return full_path.as_posix()


def is_in_ignored_directory(workspace: Path, path: Path) -> bool:
    relative_path = path.resolve().relative_to(workspace)
    return any(
        part in IGNORED_DIRECTORY_NAMES for part in relative_path.parts[:-1]
    )


def content_outside_fences(content: str) -> str:
    result: list[str] = []
    inside_fence = False
    fence_marker: str | None = None

    for line in content.splitlines():
        match = re.match(r"^\s*(```|~~~)", line)
        if match:
            marker = match.group(1)
            if not inside_fence:
                inside_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                inside_fence = False
                fence_marker = None
            continue

        if not inside_fence:
            result.append(line)

    return "\n".join(result)


def heading_slug(heading: str) -> str:
    slug = heading.casefold()
    slug = re.sub(r"<[^>]+>", "", slug)
    slug = re.sub(r"[`*_~]", "", slug)
    slug = "".join(
        character
        for character in slug
        if character.isalnum() or character.isspace() or character == "-"
    )
    slug = re.sub(r"\s+", "-", slug.strip())
    return re.sub(r"-{2,}", "-", slug)


def document_anchors(
    workspace: Path,
    path: Path,
    content: str,
    issues: list[Issue],
) -> set[str]:
    anchors: set[str] = set()
    explicit_anchors: set[str] = set()

    for match in EXPLICIT_ANCHOR_PATTERN.finditer(content):
        anchor = match.group("id")
        key = anchor.casefold()
        if key in explicit_anchors:
            issues.append(
                Issue(
                    "duplicate-anchor",
                    relative_workspace_path(workspace, path),
                    anchor,
                )
            )
        else:
            explicit_anchors.add(key)
            anchors.add(key)

    heading_counts: dict[str, int] = {}
    for line in content_outside_fences(content).splitlines():
        match = HEADING_PATTERN.match(line)
        if not match:
            continue

        base_slug = heading_slug(match.group("heading"))
        if not base_slug:
            continue

        count = heading_counts.get(base_slug, -1) + 1
        heading_counts[base_slug] = count
        anchor = base_slug if count == 0 else f"{base_slug}-{count}"
        anchors.add(anchor.casefold())

    return anchors


def resolve_documentation_target(
    workspace: Path,
    source_path: Path,
    raw_target: str,
) -> tuple[Path, str] | None:
    value = raw_target.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1]

    if EXTERNAL_TARGET_PATTERN.match(value) or value.startswith("//"):
        return None

    path_value, separator, anchor_value = value.partition("#")
    path_part = unquote(path_value)
    anchor = unquote(anchor_value) if separator else ""

    if not path_part:
        target_path = source_path
    elif path_part.startswith(("/", "\\")):
        target_path = workspace.joinpath(path_part.lstrip("/\\"))
    else:
        target_path = source_path.parent.joinpath(path_part)

    target_path = target_path.resolve()
    if target_path.is_dir():
        target_path = target_path / "README.md"

    return target_path, anchor


def is_normative_document(workspace: Path, path: Path) -> bool:
    try:
        parts = path.resolve().relative_to(workspace).parts
    except ValueError:
        return False

    return (
        len(parts) >= 3
        and parts[0] == "doc"
        and parts[1] in {"product", "architecture", "technical"}
        and path.name != "README.md"
    )


def check_documentation(workspace: Path) -> tuple[list[Issue], int, int]:
    workspace = workspace.resolve()
    if not workspace.is_dir():
        raise ValueError(f"Workspace does not exist: {workspace}")

    issues: list[Issue] = []
    all_files = sorted(
        path
        for path in workspace.rglob("*")
        if path.is_file() and not is_in_ignored_directory(workspace, path)
    )
    markdown_files = [path for path in all_files if path.suffix == ".md"]

    for path in all_files:
        if path.suffix in {".tmp", ".bak", ".orig"} or path.name.endswith("~"):
            issues.append(
                Issue(
                    "temporary-file",
                    relative_workspace_path(workspace, path),
                    path.name,
                )
            )

    paths_by_key: dict[str, Path] = {}
    content_by_key: dict[str, str] = {}
    anchors_by_key: dict[str, set[str]] = {}
    adjacency: dict[str, set[str]] = {}

    for path in markdown_files:
        key = normalized_key(path)
        content = path.read_text(encoding="utf-8-sig")
        paths_by_key[key] = path
        content_by_key[key] = content
        anchors_by_key[key] = document_anchors(workspace, path, content, issues)
        adjacency[key] = set()

        if not is_normative_document(workspace, path):
            continue

        for field in NORMATIVE_METADATA:
            pattern = re.compile(
                rf"^\*\*{re.escape(field)}:\*\*\s*\S+",
                re.MULTILINE,
            )
            if not pattern.search(content):
                issues.append(
                    Issue(
                        "missing-metadata",
                        relative_workspace_path(workspace, path),
                        field,
                    )
                )

        if (
            re.search(r"^\*\*Статус:\*\*\s*утверждено", content, re.MULTILINE)
            and UNFINISHED_MARKER_PATTERN.search(content_outside_fences(content))
        ):
            issues.append(
                Issue(
                    "unfinished-marker",
                    relative_workspace_path(workspace, path),
                    "approved normative document",
                )
            )

    for path in markdown_files:
        source_key = normalized_key(path)
        content = content_outside_fences(content_by_key[source_key])

        for match in LINK_PATTERN.finditer(content):
            raw_target = match.group("target")
            target = resolve_documentation_target(workspace, path, raw_target)
            if target is None:
                continue

            target_path, anchor = target
            target_key = normalized_key(target_path)
            if target_key not in paths_by_key:
                issues.append(
                    Issue(
                        "broken-link",
                        relative_workspace_path(workspace, path),
                        raw_target,
                    )
                )
                continue

            adjacency[source_key].add(target_key)
            if anchor and anchor.casefold() not in anchors_by_key[target_key]:
                issues.append(
                    Issue(
                        "broken-anchor",
                        relative_workspace_path(workspace, path),
                        raw_target,
                    )
                )

    root_keys = [
        key
        for path in (
            workspace / "README.md",
            workspace / "AGENTS.md",
            workspace / "doc" / "README.md",
        )
        if (key := normalized_key(path)) in paths_by_key
    ]
    reachable: set[str] = set(root_keys)
    queue = deque(root_keys)

    while queue:
        source_key = queue.popleft()
        for target_key in adjacency[source_key]:
            if target_key not in reachable:
                reachable.add(target_key)
                queue.append(target_key)

    for path in markdown_files:
        if normalized_key(path) not in reachable:
            issues.append(
                Issue(
                    "orphan-document",
                    relative_workspace_path(workspace, path),
                    "not reachable from a documentation root",
                )
            )

    link_count = sum(len(targets) for targets in adjacency.values())
    return sorted(issues), len(markdown_files), link_count


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Проверяет структуру Markdown-документации feeds.",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Корень проверяемого workspace.",
    )
    return parser.parse_args(argv)


def configure_output_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    configure_output_encoding()
    args = parse_args(argv)
    try:
        issues, markdown_count, link_count = check_documentation(
            args.workspace_root
        )
    except (OSError, UnicodeError, ValueError) as error:
        print(f"docs-check-error: {error}", file=sys.stderr)
        return 2

    if issues:
        for issue in issues:
            print(f"{issue.code}: {issue.path}: {issue.detail}")
        print("DOCS_CHECK=FAIL")
        print(f"ISSUES={len(issues)}")
        return 1

    print("DOCS_CHECK=PASS")
    print(f"MARKDOWN_FILES={markdown_count}")
    print(f"LINKS={link_count}")
    print("ISSUES=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
