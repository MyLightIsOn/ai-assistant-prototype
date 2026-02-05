#!/usr/bin/env python3
"""
Manual database backup trigger.

Usage:
    python manual_backup.py [--no-drive] [--no-vacuum]

Options:
    --no-drive    Skip Google Drive upload
    --no-vacuum   Skip database VACUUM operation
    --help        Show this help message

This script allows you to manually trigger a database backup for testing
or on-demand backup needs.
"""

import sys
import argparse
from pathlib import Path

from backup import run_backup_task, BackupManager, BackupConfig, upload_backup_to_drive
from logger import get_logger

logger = get_logger()


def manual_backup(skip_drive: bool = False, skip_vacuum: bool = False):
    """
    Run manual database backup.

    Args:
        skip_drive: Skip Google Drive upload
        skip_vacuum: Skip VACUUM operation
    """
    try:
        print("=" * 60)
        print("Manual Database Backup")
        print("=" * 60)

        # Create backup manager
        config = BackupConfig()
        manager = BackupManager(config)

        print(f"\nDatabase: {config.database_path}")
        print(f"Backup directory: {config.backup_dir}")

        # Create backup
        print("\nCreating backup...")
        backup_path = manager.create_backup(vacuum=not skip_vacuum)

        backup_size_mb = backup_path.stat().st_size / (1024 * 1024)
        print(f"✓ Backup created: {backup_path.name}")
        print(f"  Size: {backup_size_mb:.2f} MB")

        # Upload to Drive if requested
        if not skip_drive:
            print("\nUploading to Google Drive...")
            try:
                drive_file = upload_backup_to_drive(backup_path)
                print(f"✓ Upload complete")
                print(f"  Drive ID: {drive_file.get('id')}")
                print(f"  Link: {drive_file.get('webViewLink')}")
            except FileNotFoundError as e:
                print(f"⚠ Google Drive credentials not found")
                print(f"  Run google_auth_setup.py to configure Drive integration")
            except Exception as e:
                print(f"✗ Drive upload failed: {e}")
        else:
            print("\n⊘ Skipping Google Drive upload (--no-drive)")

        # Rotate backups
        print("\nRotating old backups...")
        deleted = manager.rotate_backups()
        if deleted:
            print(f"✓ Deleted {len(deleted)} old backups:")
            for filename in deleted:
                print(f"  - {filename}")
        else:
            print("  No old backups to delete")

        print("\n" + "=" * 60)
        print("✓ Backup complete!")
        print("=" * 60)

        return True

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ Backup failed: {e}")
        print("=" * 60)
        logger.exception("Manual backup failed")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manually trigger database backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manual_backup.py                 # Full backup with Drive upload
  python manual_backup.py --no-drive      # Local backup only
  python manual_backup.py --no-vacuum     # Skip VACUUM (faster)
        """
    )

    parser.add_argument(
        '--no-drive',
        action='store_true',
        help='Skip Google Drive upload'
    )

    parser.add_argument(
        '--no-vacuum',
        action='store_true',
        help='Skip database VACUUM operation'
    )

    args = parser.parse_args()

    success = manual_backup(
        skip_drive=args.no_drive,
        skip_vacuum=args.no_vacuum
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
