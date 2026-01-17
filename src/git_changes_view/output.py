"""Output formatters for different output modes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .diff import FileChange


def format_stats_aligned(
    loc: int | None,
    ins: int,
    dels: int,
    loc_width: int,
    ins_width: int,
    dels_width: int,
    use_color: bool,
) -> str:
    """Format LoC +X -Y with each column right-aligned."""
    loc_str = str(loc) if loc is not None else "-"

    # Right-align each column
    loc_padded = loc_str.rjust(loc_width)
    ins_padded = str(ins).rjust(ins_width)
    dels_padded = str(dels).rjust(dels_width)

    if use_color:
        green = "\033[32m"
        red = "\033[31m"
        reset = "\033[0m"
        return f"{loc_padded}  {green}+{ins_padded}{reset} {red}-{dels_padded}{reset}"
    return f"{loc_padded}  +{ins_padded} -{dels_padded}"


def to_flat(changes: list[FileChange], use_color: bool = True) -> list[str]:
    """Format changes as flat list with right-aligned columns.

    Args:
        changes: List of FileChange objects
        use_color: Whether to use ANSI color codes

    Returns:
        List of formatted lines
    """
    if not changes:
        return []

    # Calculate max width for each column
    max_path_len = max(len(c.path) for c in changes)
    max_loc_width = 1
    max_ins_width = 1
    max_dels_width = 1

    for c in changes:
        loc_str = str(c.loc) if c.loc is not None else "-"
        max_loc_width = max(max_loc_width, len(loc_str))
        max_ins_width = max(max_ins_width, len(str(c.insertions)))
        max_dels_width = max(max_dels_width, len(str(c.deletions)))

    lines = []
    for change in changes:
        path_padding = " " * (max_path_len - len(change.path))
        stats = format_stats_aligned(
            change.loc,
            change.insertions,
            change.deletions,
            max_loc_width,
            max_ins_width,
            max_dels_width,
            use_color,
        )
        lines.append(f"{change.path}{path_padding}  {stats}")

    return lines


def to_json(changes: list[FileChange], mode: str, base_ref: str | None = None) -> dict[str, Any]:
    """Format changes as JSON-serializable dict.

    Args:
        changes: List of FileChange objects
        mode: The comparison mode used
        base_ref: The base reference used for comparison

    Returns:
        Dictionary suitable for JSON serialization
    """
    total_ins = sum(c.insertions for c in changes)
    total_dels = sum(c.deletions for c in changes)

    result: dict[str, Any] = {
        "mode": mode,
        "files": [
            {
                "path": c.path,
                "loc": c.loc,
                "insertions": c.insertions,
                "deletions": c.deletions,
            }
            for c in changes
        ],
        "summary": {
            "total_insertions": total_ins,
            "total_deletions": total_dels,
            "net": total_ins - total_dels,
            "file_count": len(changes),
        },
    }

    if base_ref:
        result["base"] = base_ref

    return result
