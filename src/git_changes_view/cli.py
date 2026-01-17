"""CLI interface for git-changes-view."""

import json
import os
import sys

import click
from git import InvalidGitRepositoryError, Repo
from git.exc import GitCommandError

from .diff import get_base_ref, get_changes, get_comparison_info, MergeBaseNotFoundError
from .output import to_flat, to_json
from .tree import build_tree, render_tree


@click.command()
@click.option("--since-last", is_flag=True, help="Compare HEAD vs previous commit")
@click.option("--uncommitted", is_flag=True, help="Show uncommitted changes (staged + unstaged)")
@click.option("--flat", is_flag=True, help="Flat list instead of tree view")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option(
    "--sort",
    type=click.Choice(["name", "changes", "path"]),
    default="name",
    help="Sort order: name (default), changes, or path",
)
@click.option("--no-color", is_flag=True, help="Disable colored output")
def main(
    since_last: bool,
    uncommitted: bool,
    flat: bool,
    as_json: bool,
    sort: str,
    no_color: bool,
) -> None:
    """Display changed files with line counts in tree view.

    By default, compares current branch against main since divergence.
    """
    # Find git repository
    try:
        repo = Repo(os.getcwd(), search_parent_directories=True)
    except InvalidGitRepositoryError:
        click.echo("Error: Not a git repository", err=True)
        click.echo("Run this command from within a git repository.", err=True)
        sys.exit(1)

    # Check for empty repository
    try:
        repo.head.commit
    except ValueError:
        click.echo("Error: Repository has no commits yet.", err=True)
        sys.exit(1)

    # Determine mode
    mode = "default"
    if since_last:
        mode = "since-last"
    elif uncommitted:
        mode = "uncommitted"

    # Get changes with specific error handling
    try:
        changes = get_changes(repo, mode)
    except MergeBaseNotFoundError:
        click.echo("Error: Could not find merge base with main branch.", err=True)
        click.echo("Tip: Make sure 'main' or 'master' branch exists, or use --uncommitted.", err=True)
        sys.exit(1)
    except GitCommandError as e:
        if "HEAD~1" in str(e) or "unknown revision" in str(e).lower():
            click.echo("Error: Not enough commits for --since-last comparison.", err=True)
            click.echo("Tip: Repository needs at least 2 commits.", err=True)
        else:
            click.echo(f"Git error: {e.stderr.strip() if e.stderr else e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if not changes:
        click.echo("No changes found.")
        return

    # Sort
    if sort == "changes":
        changes.sort(key=lambda c: -c.total)
    elif sort == "path":
        changes.sort(key=lambda c: c.path)
    else:  # name (default)
        changes.sort(key=lambda c: c.path.split("/")[-1].lower())

    # Determine color usage
    use_color = not no_color and not as_json and os.environ.get("NO_COLOR") is None

    # Get comparison info for header
    try:
        comparison = get_comparison_info(repo, mode)
    except Exception:
        comparison = None

    # Output
    if as_json:
        base_ref = get_base_ref(repo, mode)
        output = to_json(changes, mode, base_ref)
        click.echo(json.dumps(output, indent=2))
    else:
        # Tree/flat view
        if flat:
            for line in to_flat(changes, use_color):
                click.echo(line)
        else:
            tree = build_tree(changes)
            for line in render_tree(tree, use_color=use_color):
                click.echo(line)

        # Summary stats
        total_ins = sum(c.insertions for c in changes)
        total_dels = sum(c.deletions for c in changes)
        net = total_ins - total_dels

        click.echo("")
        sign = "+" if net >= 0 else ""
        click.echo(f"Total: +{total_ins} -{total_dels} (net: {sign}{net})")
        click.echo(f"Files: {len(changes)}")

        # Comparison info at the end
        if comparison:
            click.echo("")
            click.echo("Compare:")
            if comparison.base:
                click.echo(f"    {comparison.base.format()}")
            if isinstance(comparison.head, str):
                click.echo(f"    {comparison.head}")
            else:
                click.echo(f"    {comparison.head.format()}")


if __name__ == "__main__":
    main()
