#!/usr/bin/env python3
"""
GitAwareBackup: A tool to create compressed backups of directories while
respecting .git directories and .gitignore patterns.
"""

import os
import sys
import tarfile
import argparse
import logging
import pathspec
from datetime import datetime
from typing import Dict, Optional, Set
import tempfile
import shutil
import hashlib

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("git-aware-backup")


class GitAwareBackup:
    """Creates backups while respecting .git directories and .gitignore patterns."""
    
    def __init__(self, source_dir: str, output_file: Optional[str] = None, 
                 compression: str = "gz", verbose: bool = False):
        """
        Initialize the backup tool.
        
        Args:
            source_dir: Directory to backup
            output_file: Output file path (optional)
            compression: Compression type ('gz', 'bz2', or 'xz')
            verbose: Whether to enable verbose logging
        """
        self.source_dir = os.path.abspath(source_dir)
        self.verbose = verbose
        self.compression = compression
        self.gitignore_specs: Dict[str, pathspec.PathSpec] = {}
        self.excluded_paths: Set[str] = set()
        self.total_files = 0
        self.processed_files = 0
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        # Validate source directory
        if not os.path.isdir(self.source_dir):
            raise ValueError(f"Source directory '{self.source_dir}' does not exist")
        
        # Set output file with proper extension based on compression
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.basename(self.source_dir)
            extension = self._get_extension(compression)
            self.output_file = f"{base_name}_{timestamp}.tar{extension}"
        else:
            self.output_file = output_file
    
    def _get_extension(self, compression: str) -> str:
        """Get the appropriate file extension based on compression type."""
        compression_extensions = {
            "gz": ".gz",
            "bz2": ".bz2",
            "xz": ".xz",
            "none": ""
        }
        return compression_extensions.get(compression.lower(), ".gz")
    
    def _get_compression_mode(self) -> str:
        """Get the appropriate tarfile mode based on compression type."""
        compression_modes = {
            "gz": "w:gz",
            "bz2": "w:bz2",
            "xz": "w:xz",
            "none": "w"
        }
        return compression_modes.get(self.compression.lower(), "w:gz")
    
    def _scan_directory(self) -> None:
        """Scan the directory to count files and collect gitignore specs."""
        logger.info("Scanning directory and collecting .gitignore files...")
        
        # First pass: count files and collect gitignore specs
        for root, dirs, files in os.walk(self.source_dir):
            # Skip .git directories during the walk
            if '.git' in dirs:
                self.excluded_paths.add(os.path.join(root, '.git'))
                dirs.remove('.git')
            
            # Process .gitignore if present
            if '.gitignore' in files:
                try:
                    gitignore_path = os.path.join(root, '.gitignore')
                    self.gitignore_specs[root] = self._read_gitignore(gitignore_path)
                    logger.debug(f"Processed .gitignore at {root}")
                except Exception as e:
                    logger.warning(f"Error reading .gitignore at {root}: {str(e)}")
            
            # Count total files
            self.total_files += len(files)
    
    def _read_gitignore(self, gitignore_path: str) -> pathspec.PathSpec:
        """Read .gitignore patterns from a file."""
        with open(gitignore_path, 'r', encoding='utf-8', errors='replace') as f:
            return pathspec.PathSpec.from_lines('gitwildmatch', f)
    
    def _should_exclude(self, path: str) -> bool:
        """Check if a path should be excluded based on .gitignore or .git dir."""
        # Skip if path is already in excluded_paths
        if path in self.excluded_paths:
            return True
        
        # Always exclude .git directories
        if os.path.basename(path) == '.git' and os.path.isdir(path):
            self.excluded_paths.add(path)
            return True
        
        # Check against gitignore patterns
        for dir_path, spec in self.gitignore_specs.items():
            if path.startswith(dir_path):
                rel_path = os.path.relpath(path, dir_path)
                if spec.match_file(rel_path):
                    self.excluded_paths.add(path)
                    return True
        
        return False
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def create_backup(self) -> str:
        """Create a compressed backup of the directory, respecting git files."""
        start_time = datetime.now()
        logger.info(f"Starting backup of {self.source_dir} to {self.output_file}")
        
        # Scan directory first to gather information
        self._scan_directory()
        
        try:
            # Create a temporary directory for metadata
            temp_dir = tempfile.mkdtemp()
            manifest_path = os.path.join(temp_dir, 'backup_manifest.txt')
            
            logger.info(f"Found {self.total_files} files to process.")
            
            # Create tar archive
            with tarfile.open(self.output_file, self._get_compression_mode()) as tar:
                # Initialize manifest file
                with open(manifest_path, 'w', encoding='utf-8') as manifest:
                    manifest.write(f"# Backup created: {datetime.now().isoformat()}\n")
                    manifest.write(f"# Source: {self.source_dir}\n")
                    manifest.write("# path,size,modified,sha256\n")
                
                # Add files
                for root, dirs, files in os.walk(self.source_dir):
                    # Filter out directories that should be excluded
                    dirs[:] = [d for d in dirs if not self._should_exclude(os.path.join(root, d))]
                    
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        if not self._should_exclude(file_path):
                            try:
                                # Get relative path for archive
                                arcname = os.path.relpath(file_path, os.path.dirname(self.source_dir))
                                
                                # Add to archive
                                tar.add(file_path, arcname=arcname)
                                
                                # Update manifest with file information
                                if self.verbose:
                                    file_stat = os.stat(file_path)
                                    file_size = file_stat.st_size
                                    file_mtime = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                                    checksum = self._calculate_checksum(file_path)
                                    
                                    with open(manifest_path, 'a', encoding='utf-8') as manifest:
                                        manifest.write(f"{arcname},{file_size},{file_mtime},{checksum}\n")
                                
                                self.processed_files += 1
                                if self.processed_files % 100 == 0 or self.processed_files == self.total_files:
                                    progress = (self.processed_files / self.total_files) * 100
                                    logger.info(f"Progress: {progress:.1f}% ({self.processed_files}/{self.total_files})")
                            
                            except Exception as e:
                                logger.warning(f"Error adding {file_path}: {str(e)}")
                
                # Add manifest to the archive
                if self.verbose:
                    tar.add(manifest_path, arcname="backup_manifest.txt")
                
            # Clean up
            shutil.rmtree(temp_dir)
            
            # Calculate final statistics
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            skipped = self.total_files - self.processed_files
            
            # Log success
            backup_size = os.path.getsize(self.output_file) / (1024 * 1024)  # Convert to MB
            logger.info(f"Backup completed successfully in {duration:.2f} seconds")
            logger.info(f"Backup size: {backup_size:.2f} MB")
            logger.info(f"Files processed: {self.processed_files}")
            logger.info(f"Files skipped (excluded): {skipped}")
            
            return os.path.abspath(self.output_file)
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            # Clean up partial backup file if it exists
            if os.path.exists(self.output_file):
                try:
                    os.remove(self.output_file)
                    logger.info(f"Removed partial backup file: {self.output_file}")
                except Exception:
                    pass
            raise


def main():
    """Command-line interface for GitAwareBackup."""
    parser = argparse.ArgumentParser(
        description='Create a compressed backup excluding .git directories and respecting .gitignore files'
    )
    parser.add_argument('source', help='Source directory to backup')
    parser.add_argument('-o', '--output', help='Output file name (default: source_timestamp.tar.gz)')
    parser.add_argument('-c', '--compression', choices=['gz', 'bz2', 'xz', 'none'], default='gz',
                        help='Compression algorithm to use (default: gz)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    try:
        backup_tool = GitAwareBackup(
            args.source,
            args.output,
            args.compression,
            args.verbose
        )
        backup_file = backup_tool.create_backup()
        logger.info(f"Backup created: {backup_file}")
        return 0
    except KeyboardInterrupt:
        logger.error("Backup interrupted by user.")
        return 130
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
