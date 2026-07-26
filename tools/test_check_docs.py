#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path


CHECKER = Path(__file__).with_name("check_docs.py")
Arrange = Callable[[Path], None]


def write_utf8_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def new_valid_workspace(path: Path) -> None:
    write_utf8_file(
        path / "README.md",
        "# Test project\n\n[Documentation](doc/README.md)\n",
    )
    write_utf8_file(
        path / "AGENTS.md",
        "# Agent instructions\n\n[Documentation](doc/README.md)\n",
    )
    write_utf8_file(
        path / "doc" / "README.md",
        "# Documentation\n\n[Product rule](product/rule.md)\n",
    )
    write_utf8_file(
        path / "doc" / "product" / "rule.md",
        """# Product rule

**Статус:** утверждено
**Владелец фактов:** тестовое правило
**Читать когда:** проверяется документация
**Связанные документы:** [индекс](../README.md)

## Rule

The rule is explicit.
""",
    )


def invoke_checker(workspace: Path) -> tuple[int, str]:
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--workspace-root",
            str(workspace),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    return result.returncode, result.stdout


def assert_pass(name: str, arrange: Arrange) -> None:
    with tempfile.TemporaryDirectory(prefix=f"feeds-docs-check-{name}-") as temp:
        case_root = Path(temp)
        new_valid_workspace(case_root)
        arrange(case_root)
        exit_code, output = invoke_checker(case_root)
        if exit_code != 0 or "DOCS_CHECK=PASS" not in output:
            raise AssertionError(
                f"Scenario '{name}' expected success.\n{output}"
            )
    print(f"{name}=PASS")


def assert_failure(name: str, expected_code: str, arrange: Arrange) -> None:
    with tempfile.TemporaryDirectory(prefix=f"feeds-docs-check-{name}-") as temp:
        case_root = Path(temp)
        new_valid_workspace(case_root)
        arrange(case_root)
        exit_code, output = invoke_checker(case_root)
        if exit_code == 0 or expected_code not in output:
            raise AssertionError(
                f"Scenario '{name}' expected '{expected_code}'.\n{output}"
            )
    print(f"{name}=PASS")


def append_text(path: Path, content: str) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(content)


def arrange_broken_link(root: Path) -> None:
    append_text(root / "doc" / "README.md", "\n[Missing](missing.md)\n")


def arrange_broken_anchor(root: Path) -> None:
    append_text(
        root / "doc" / "README.md",
        "\n[Missing anchor](product/rule.md#absent)\n",
    )


def arrange_duplicate_anchor(root: Path) -> None:
    append_text(
        root / "doc" / "product" / "rule.md",
        '\n<a id="same"></a>\n<a id="same"></a>\n',
    )


def arrange_missing_metadata(root: Path) -> None:
    path = root / "doc" / "product" / "rule.md"
    content = path.read_text(encoding="utf-8")
    path.write_text(
        content.replace("**Владелец фактов:** тестовое правило\n", ""),
        encoding="utf-8",
    )


def arrange_orphan_document(root: Path) -> None:
    write_utf8_file(root / "doc" / "orphan.md", "# Orphan\n")


def arrange_temporary_file(root: Path) -> None:
    write_utf8_file(root / "doc" / "draft.tmp", "temporary")


def arrange_unfinished_marker(root: Path) -> None:
    append_text(
        root / "doc" / "product" / "rule.md",
        "\nTODO: unfinished\n",
    )


def no_changes(_: Path) -> None:
    return


def main() -> int:
    assert_pass("valid-workspace", no_changes)
    assert_failure("broken-link", "broken-link", arrange_broken_link)
    assert_failure("broken-anchor", "broken-anchor", arrange_broken_anchor)
    assert_failure(
        "duplicate-anchor",
        "duplicate-anchor",
        arrange_duplicate_anchor,
    )
    assert_failure(
        "missing-metadata",
        "missing-metadata",
        arrange_missing_metadata,
    )
    assert_failure(
        "orphan-document",
        "orphan-document",
        arrange_orphan_document,
    )
    assert_failure(
        "temporary-file",
        "temporary-file",
        arrange_temporary_file,
    )
    assert_failure(
        "unfinished-marker",
        "unfinished-marker",
        arrange_unfinished_marker,
    )
    print("CHECK_DOCS_TESTS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
