# git-changes-view

A CLI tool that displays changed files in a tree view with line counts (+/-), designed for AI-driven workflows to track what files were modified.

## Features

- **Tree view** of changed files with directory structure
- **Line counts**: LoC (lines of code), insertions (+), deletions (-)
- **Multiple comparison modes**:
  - Default: current branch vs main (since divergence)
  - `--since-last`: HEAD vs HEAD~1
  - `--uncommitted`: working tree vs HEAD
- **Output formats**: tree (default), flat list, JSON
- **Sorting**: by name, changes, or path
- **Colors**: green for additions, red for deletions (respects `NO_COLOR`)

## Installation

### Using uv (recommended)

```bash
uv tool install git+https://github.com/DanEscher98/git-changes-view
```

### From source

```bash
git clone https://github.com/DanEscher98/git-changes-view
cd git-changes-view
uv tool install .
```

### Git alias (optional)

Add a shorter alias:

```bash
git config --global alias.cv '!git-changes-view'
```

## Usage

```bash
# Tree view of changes since diverging from main
git-changes-view

# Or with the alias
git cv

# Compare HEAD vs previous commit
git cv --since-last

# Show uncommitted changes
git cv --uncommitted

# Flat list instead of tree
git cv --flat

# JSON output
git cv --json

# Sort by total changes (most changed first)
git cv --sort changes
```

## Example Output

### Tree View (default)

```
└── web/
    └── src/
        ├── app/
        │   └── api/
        │       └── route.ts              360  +110 -18
        └── lib/
            └── db/
                ├── schemas.ts            342  +342 -  0
                └── validation.ts         458  +458 -  0

Total: +910 -18 (net: +892)
Files: 3

Compare:
    2024-01-15 17:36:59 c2e7d7 Merge pull request #173...
    2024-01-16 16:17:27 a1c1cb fix(validation): use type-safe...
```

### Flat View (`--flat`)

```
web/src/app/api/route.ts       360  +110 -18
web/src/lib/db/schemas.ts      342  +342 -  0
web/src/lib/db/validation.ts   458  +458 -  0

Total: +910 -18 (net: +892)
Files: 3
```

## Options

| Option | Description |
|--------|-------------|
| `--since-last` | Compare HEAD vs previous commit |
| `--uncommitted` | Show uncommitted changes (staged + unstaged) |
| `--flat` | Flat list instead of tree view |
| `--json` | Output as JSON |
| `--sort [name\|changes\|path]` | Sort order (default: name) |
| `--no-color` | Disable colored output |
| `--help` | Show help message |

## Requirements

- Python 3.11+
- Git repository

## License

MIT
