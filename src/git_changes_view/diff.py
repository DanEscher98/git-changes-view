em"""Git diff logic using GitPython."""

from dataclasses import dataclass

from git import Repo
from git.exc import GitCommandError


class MergeBaseNotFoundError(Exception):
    """Raised when merge base cannot be found."""

    pass


@dataclass
class FileChange:
    """Represents a file change with insertion/deletion counts."""

    path: str
    insertions: int
    deletions: int
    loc: int | None = None  # Current lines of code (None if file deleted or binary)

    @property
    def net(self) -> int:
        """Net change (insertions - deletions)."""
        return self.insertions - self.deletions

    @property
    def total(self) -> int:
        """Total lines changed."""
        return self.insertions + self.deletions


def get_merge_base(repo: Repo, target: str = "main") -> str:
    """Find common ancestor between HEAD and target branch.

    Tries main, then falls back to origin/main, master, origin/master.

    Raises:
        MergeBaseNotFoundError: If no merge base can be found
    """
    candidates = [target, f"origin/{target}", "master", "origin/master"]

    for branch in candidates:
        try:
            return repo.git.merge_base("HEAD", branch).strip()
        except GitCommandError:
            continue

    raise MergeBaseNotFoundError(
        f"Could not find merge base with any of: {', '.join(candidates)}"
    )


def parse_numstat(output: str) -> list[FileChange]:
    """Parse git diff --numstat output.

    Format: <insertions>\t<deletions>\t<filepath>
    Binary files show '-' for insertions/deletions.
    """
    if not output or not output.strip():
        return []

    changes = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            # Binary files have '-' for stats
            ins = int(parts[0]) if parts[0] != "-" else 0
            dels = int(parts[1]) if parts[1] != "-" else 0
            # Handle renamed files: path might contain " => "
            path = parts[2]
            if " => " in path:
                # For renames like "{old => new}/file.txt", take the new path
                path = path.replace("{", "").replace("}", "")
                if " => " in path:
                    path = path.split(" => ")[1]
            changes.append(FileChange(path, ins, dels))
    return changes


def get_changes(repo: Repo, mode: str) -> list[FileChange]:
    """Get file changes based on mode.

    Args:
        repo: GitPython Repo instance
        mode: One of "default", "uncommitted", or "since-last"

    Returns:
        List of FileChange objects

    Raises:
        MergeBaseNotFoundError: If merge base cannot be found (default mode)
        GitCommandError: If git command fails
    """
    if mode == "uncommitted":
        # Staged + unstaged vs HEAD
        output = repo.git.diff("--numstat", "HEAD")
    elif mode == "since-last":
        # HEAD vs HEAD~1
        output = repo.git.diff("--numstat", "HEAD~1", "HEAD")
    else:
        # Default: since merge base with main
        base = get_merge_base(repo)
        output = repo.git.diff("--numstat", base, "HEAD")

    changes = parse_numstat(output)

    # Add line counts for each file
    for change in changes:
        change.loc = get_file_loc(repo, change.path, mode)

    return changes


def get_file_loc(repo: Repo, path: str, mode: str) -> int | None:
    """Get current line count for a file.

    For uncommitted mode, counts lines in working tree.
    Otherwise, counts lines at HEAD.
    Returns None if file doesn't exist or is binary.
    """
    try:
        if mode == "uncommitted":
            # Count lines in working tree
            import os
            full_path = os.path.join(repo.working_dir, path)
            if not os.path.isfile(full_path):
                return None
            with open(full_path, "r", errors="ignore") as f:
                return sum(1 for _ in f)
        else:
            # Count lines at HEAD
            try:
                blob = repo.head.commit.tree / path
                content = blob.data_stream.read().decode("utf-8", errors="ignore")
                return content.count("\n") + (1 if content and not content.endswith("\n") else 0)
            except KeyError:
                # File doesn't exist at HEAD (new file)
                return None
    except Exception:
        return None


def get_base_ref(repo: Repo, mode: str) -> str | None:
    """Get the base reference used for comparison.

    Returns None for uncommitted mode.
    """
    if mode == "uncommitted":
        return "HEAD"
    elif mode == "since-last":
        return "HEAD~1"
    else:
        try:
            return get_merge_base(repo)
        except MergeBaseNotFoundError:
            return None


@dataclass
class CommitInfo:
    """Short commit info for display."""

    short_hash: str
    message: str
    date: str  # YYYY-MM-DD HH:MM:SS

    def format(self, max_msg_len: int = 50) -> str:
        """Format as 'YYYY-MM-DD HH:MM:SS abc123 commit message...'"""
        msg = self.message
        if len(msg) > max_msg_len:
            msg = msg[: max_msg_len - 3] + "..."
        return f"{self.date} {self.short_hash} {msg}"


def get_commit_info(repo: Repo, ref: str) -> CommitInfo:
    """Get short hash, date, and message for a commit reference."""
    commit = repo.commit(ref)
    short_hash = commit.hexsha[:6]
    date = commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S")
    message = commit.message.split("\n")[0].strip()
    return CommitInfo(short_hash, message, date)


@dataclass
class ComparisonInfo:
    """Info about what's being compared."""

    base: CommitInfo | None  # None for uncommitted
    head: CommitInfo | str  # str "uncommitted" for working tree

    def format(self) -> str:
        """Format the comparison string."""
        if isinstance(self.head, str):
            # Uncommitted mode
            head_str = self.head
        else:
            head_str = self.head.format()

        if self.base is None:
            return f"Comparing: {head_str}"

        base_str = self.base.format()
        return f"Comparing: {base_str} -> {head_str}"


def get_comparison_info(repo: Repo, mode: str) -> ComparisonInfo:
    """Get info about what commits are being compared."""
    if mode == "uncommitted":
        head_info = get_commit_info(repo, "HEAD")
        return ComparisonInfo(base=head_info, head="uncommitted")
    elif mode == "since-last":
        base_info = get_commit_info(repo, "HEAD~1")
        head_info = get_commit_info(repo, "HEAD")
        return ComparisonInfo(base=base_info, head=head_info)
    else:
        # Default: merge base to HEAD
        base_ref = get_merge_base(repo)
        base_info = get_commit_info(repo, base_ref)
        head_info = get_commit_info(repo, "HEAD")
        return ComparisonInfo(base=base_info, head=head_info)
