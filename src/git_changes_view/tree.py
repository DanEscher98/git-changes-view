"""Tree view rendering for file changes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .diff import FileChange


@dataclass
class TreeNode:
    """A node in the file tree."""

    name: str
    is_file: bool = False
    insertions: int = 0
    deletions: int = 0
    loc: int | None = None
    children: dict[str, TreeNode] = field(default_factory=dict)


def build_tree(changes: list[FileChange]) -> TreeNode:
    """Build tree structure from flat file paths."""
    root = TreeNode(name=".")

    for change in changes:
        parts = change.path.split("/")
        node = root

        for i, part in enumerate(parts):
            is_file = i == len(parts) - 1

            if part not in node.children:
                node.children[part] = TreeNode(
                    name=part,
                    is_file=is_file,
                    insertions=change.insertions if is_file else 0,
                    deletions=change.deletions if is_file else 0,
                    loc=change.loc if is_file else None,
                )
            node = node.children[part]

    return root


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


@dataclass
class _TreeLine:
    """Internal representation of a tree line before final formatting."""

    text: str
    stats: tuple[int | None, int, int] | None = None  # (loc, insertions, deletions) or None for dirs


def _collect_lines(node: TreeNode, prefix: str = "") -> list[_TreeLine]:
    """Collect tree lines with their stats for later alignment."""
    lines: list[_TreeLine] = []

    # Sort: directories first, then files, alphabetically within each
    children = sorted(node.children.values(), key=lambda n: (n.is_file, n.name))

    for i, child in enumerate(children):
        is_last = i == len(children) - 1
        connector = "\u2514\u2500\u2500 " if is_last else "\u251c\u2500\u2500 "

        if child.is_file:
            lines.append(_TreeLine(
                text=f"{prefix}{connector}{child.name}",
                stats=(child.loc, child.insertions, child.deletions),
            ))
        else:
            lines.append(_TreeLine(text=f"{prefix}{connector}{child.name}/"))
            extension = "    " if is_last else "\u2502   "
            lines.extend(_collect_lines(child, prefix + extension))

    return lines


def render_tree(
    node: TreeNode, prefix: str = "", use_color: bool = True
) -> list[str]:
    """Render tree with box-drawing characters and right-aligned stats.

    Args:
        node: Root TreeNode to render
        prefix: Current indentation prefix (unused, kept for API compat)
        use_color: Whether to use ANSI color codes

    Returns:
        List of formatted lines
    """
    # First pass: collect all lines
    tree_lines = _collect_lines(node)

    if not tree_lines:
        return []

    # Calculate max text width (for lines with stats)
    max_text_width = max(
        len(line.text) for line in tree_lines if line.stats is not None
    ) if any(line.stats for line in tree_lines) else 0

    # Calculate max width for each stats column separately
    max_loc_width = 1
    max_ins_width = 1
    max_dels_width = 1

    for line in tree_lines:
        if line.stats:
            loc, ins, dels = line.stats
            loc_str = str(loc) if loc is not None else "-"
            max_loc_width = max(max_loc_width, len(loc_str))
            max_ins_width = max(max_ins_width, len(str(ins)))
            max_dels_width = max(max_dels_width, len(str(dels)))

    # Second pass: format with right-aligned columns
    result: list[str] = []
    for line in tree_lines:
        if line.stats is None:
            result.append(line.text)
        else:
            text_padding = " " * (max_text_width - len(line.text))
            loc, ins, dels = line.stats
            stats = format_stats_aligned(
                loc, ins, dels, max_loc_width, max_ins_width, max_dels_width, use_color
            )
            result.append(f"{line.text}{text_padding}  {stats}")

    return result
