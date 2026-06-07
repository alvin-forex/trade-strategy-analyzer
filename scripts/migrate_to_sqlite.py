#!/usr/bin/env python3
"""
Migration Script: Pickle → SQLite

Migrate legacy .pkl data files to SQLite database.

Usage:
    python scripts/migrate_to_sqlite.py           # Auto-detect and migrate
    python scripts/migrate_to_sqlite.py --v5      # Migrate v5 pickle only
    python scripts/migrate_to_sqlite.py --v4      # Migrate v4 pickle only
    python scripts/migrate_to_sqlite.py --all     # Migrate all found pickles
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_manager import migrate_from_pickle, get_database_stats, init_database


def find_pickle_files():
    """Find all DDE pickle files in common locations."""
    locations = [
        '/tmp/dde_v5_data.pkl',
        '/tmp/dde_v4_data.pkl',
        Path(__file__).parent.parent / 'output' / 'dde_v5_data.pkl',
        Path(__file__).parent.parent / 'output' / 'dde_v4_data.pkl',
        Path(__file__).parent.parent / 'data' / 'dde_v5_data.pkl',
        Path(__file__).parent.parent / 'data' / 'dde_v4_data.pkl',
    ]
    
    found = []
    for loc in locations:
        p = Path(loc)
        if p.exists():
            # Determine version from filename
            version = 'v5' if 'v5' in p.stem else 'v4'
            found.append((str(p), version))
    
    return found


def main():
    parser = argparse.ArgumentParser(description='Migrate pickle data to SQLite')
    parser.add_argument('--v5', action='store_true', help='Migrate v5 pickle only')
    parser.add_argument('--v4', action='store_true', help='Migrate v4 pickle only')
    parser.add_argument('--all', action='store_true', help='Migrate all found pickles')
    parser.add_argument('--stats', action='store_true', help='Show database stats after migration')
    parser.add_argument('--dry-run', action='store_true', help='Find pickles without migrating')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔄 TSA Migration: Pickle → SQLite")
    print("=" * 60)
    
    # Initialize database
    init_database()
    
    # Find pickle files
    found = find_pickle_files()
    
    if not found:
        print("\n⚠️ No pickle files found")
        print("   Expected locations:")
        print("   - /tmp/dde_v5_data.pkl")
        print("   - /tmp/dde_v4_data.pkl")
        return
    
    print(f"\n📦 Found {len(found)} pickle file(s):")
    for pkl_path, version in found:
        size_mb = Path(pkl_path).stat().st_size / 1024 / 1024
        print(f"   [{version}] {pkl_path} ({size_mb:.2f} MB)")
    
    if args.dry_run:
        print("\n⚠️ Dry run — no migration performed")
        return
    
    # Filter by version if specified
    to_migrate = []
    if args.v5:
        to_migrate = [(p, v) for p, v in found if v == 'v5']
    elif args.v4:
        to_migrate = [(p, v) for p, v in found if v == 'v4']
    elif args.all:
        to_migrate = found
    else:
        # Default: migrate latest version found
        if any(v == 'v5' for _, v in found):
            to_migrate = [(p, v) for p, v in found if v == 'v5']
        else:
            to_migrate = found
    
    if not to_migrate:
        print("\n⚠️ No files to migrate (check version filter)")
        return
    
    print(f"\n🚀 Migrating {len(to_migrate)} file(s)...")
    
    for pkl_path, version in to_migrate:
        print(f"\n[{version}] {pkl_path}")
        try:
            batch_id = migrate_from_pickle(pkl_path, version)
            print(f"   ✅ Success: batch_id = {batch_id}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    if args.stats:
        print("\n" + "=" * 60)
        print("📊 Database Statistics")
        print("=" * 60)
        stats = get_database_stats()
        for k, v in stats.items():
            if isinstance(v, dict):
                print(f"{k}:")
                for kk, vv in v.items():
                    print(f"   {kk}: {vv}")
            else:
                print(f"{k}: {v}")
    
    print("\n" + "=" * 60)
    print("✅ Migration complete!")
    print("=" * 60)
    print("\n📝 Notes:")
    print("   - Original pickle files are preserved (not deleted)")
    print("   - Run 'python db_manager.py stats' to check database")
    print("   - Run 'pytest tests/' to verify functionality")


if __name__ == '__main__':
    main()