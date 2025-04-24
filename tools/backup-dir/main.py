#!/usr/bin/env python3
"""
GitAwareBackup: A tool to create compressed backups of directories using git archive.
Creates a temporary git repository to respect .gitignore patterns.
"""

import os
import sys
import argparse
import logging
from datetime import datetime
import subprocess
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("git-aware-backup")


class GitAwareBackup:
    """Creates backups using git archive."""
    
    def __init__(self, source_dir: str, output_file: str = None, verbose: bool = False):
        """Initialize the backup tool."""
        self.source_dir = os.path.abspath(source_dir)
        self.verbose = verbose
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        if not os.path.isdir(self.source_dir):
            raise ValueError(f"Source directory '{self.source_dir}' does not exist")
        
        self.output_file = output_file or f"{os.path.basename(self.source_dir)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    def _run_git_command(self, args: list) -> subprocess.CompletedProcess:
        """Run a git command in the source directory."""
        if self.verbose:
            logger.debug(f"Running command: git {' '.join(args)}")
        return subprocess.run(['git'] + args, cwd=self.source_dir, check=True, capture_output=True)
    
    def create_backup(self) -> str:
        """Create a compressed backup of the directory using git archive."""
        start_time = datetime.now()
        logger.info(f"Starting backup of {self.source_dir} to {self.output_file}")
        
        try:
            # Initialize temporary git repository
            logger.info("Initializing temporary git repository...")
            self._run_git_command(['init'])
            
            # Stage all files (respecting .gitignore)
            logger.info("Staging files...")
            self._run_git_command(['add', '.'])
            
            # Create initial commit
            logger.info("Creating initial commit...")
            self._run_git_command(['commit', '-m', 'Temporary commit for backup'])
            
            # Create the output file in the current directory
            output_path = os.path.abspath(self.output_file)
            
            # Create archive
            logger.info("Creating archive...")
            self._run_git_command(['archive', '--format=zip', '-o', output_path, 'HEAD'])
            
            # Clean up temporary git repository
            logger.info("Cleaning up temporary git repository...")
            git_dir = os.path.join(self.source_dir, '.git')
            if os.path.exists(git_dir):
                shutil.rmtree(git_dir)
            
            duration = (datetime.now() - start_time).total_seconds()
            backup_size = os.path.getsize(output_path) / (1024 * 1024)
            
            logger.info(f"Backup completed successfully in {duration:.2f} seconds")
            logger.info(f"Backup size: {backup_size:.2f} MB")
            
            return output_path
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            # Clean up git repository in case of failure
            git_dir = os.path.join(self.source_dir, '.git')
            if os.path.exists(git_dir):
                shutil.rmtree(git_dir)
            if os.path.exists(self.output_file):
                try:
                    os.remove(self.output_file)
                    logger.info(f"Removed partial backup file: {self.output_file}")
                except Exception:
                    pass
            raise


def main():
    """Command-line interface for GitAwareBackup."""
    parser = argparse.ArgumentParser(description='Create a compressed backup using git archive')
    parser.add_argument('source', help='Source directory to backup')
    parser.add_argument('-o', '--output', help='Output file name (default: source_timestamp.zip)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    try:
        backup_tool = GitAwareBackup(args.source, args.output, args.verbose)
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
