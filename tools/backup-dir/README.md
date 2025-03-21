# Git-Aware Backup

A Python tool to create compressed backups of directories while respecting .git directories and .gitignore patterns.

## Features

- Respects .gitignore patterns
- Automatically excludes .git directories
- Supports multiple compression formats (gz, bz2, xz)
- Generates backup manifest with file metadata (in verbose mode)
- Progress tracking
- SHA-256 checksums for files (in verbose mode)

## Usage

Basic usage:

```bash
python tools/backup-gitignore.py /path/to/source/directory
```

Options:

- `-o, --output`: Specify output file name (default: source_timestamp.tar.gz)
- `-c, --compression`: Choose compression algorithm (gz, bz2, xz, or none)
- `-v, --verbose`: Enable verbose output with detailed manifest

Example:

```bash
python tools/backup-gitignore.py /path/to/project -o backup.tar.gz -c gz -v
```

## License

MIT License
