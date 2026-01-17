"""Tests for diff module."""

import pytest

from git_changes_view.diff import FileChange, parse_numstat


class TestFileChange:
    """Tests for FileChange dataclass."""

    def test_net_positive(self) -> None:
        change = FileChange("test.py", insertions=10, deletions=3)
        assert change.net == 7

    def test_net_negative(self) -> None:
        change = FileChange("test.py", insertions=3, deletions=10)
        assert change.net == -7

    def test_net_zero(self) -> None:
        change = FileChange("test.py", insertions=5, deletions=5)
        assert change.net == 0

    def test_total(self) -> None:
        change = FileChange("test.py", insertions=10, deletions=3)
        assert change.total == 13


class TestParseNumstat:
    """Tests for parse_numstat function."""

    def test_single_file(self) -> None:
        output = "10\t5\tsrc/file.py"
        changes = parse_numstat(output)
        assert len(changes) == 1
        assert changes[0].path == "src/file.py"
        assert changes[0].insertions == 10
        assert changes[0].deletions == 5

    def test_multiple_files(self) -> None:
        output = "10\t5\tsrc/file1.py\n3\t0\tsrc/file2.py"
        changes = parse_numstat(output)
        assert len(changes) == 2
        assert changes[0].path == "src/file1.py"
        assert changes[1].path == "src/file2.py"

    def test_empty_output(self) -> None:
        changes = parse_numstat("")
        assert changes == []

    def test_whitespace_output(self) -> None:
        changes = parse_numstat("   \n  ")
        assert changes == []

    def test_binary_file(self) -> None:
        output = "-\t-\timage.png"
        changes = parse_numstat(output)
        assert len(changes) == 1
        assert changes[0].insertions == 0
        assert changes[0].deletions == 0

    def test_renamed_file(self) -> None:
        output = "5\t3\t{old => new}/file.py"
        changes = parse_numstat(output)
        assert len(changes) == 1
        assert changes[0].path == "new/file.py"
