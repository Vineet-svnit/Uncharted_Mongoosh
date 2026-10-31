"""
Export binary assets (PDFs and PNGs) from MongoDB GridFS to a local folder
so you can visually inspect them.

Run:
    python -m data_layer.tests.export_assets
"""
from __future__ import annotations

import os
from pathlib import Path

from data_layer.mongo import get_db, get_gridfs

OUTPUT_DIR = Path(__file__).parent.parent / "exported_assets"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gfs = get_gridfs()

    print(f"Exporting files from GridFS to: {OUTPUT_DIR.resolve()}\n")
    exported_count = 0

    for grid_out in gfs.find():
        filename = grid_out.filename
        file_path = OUTPUT_DIR / filename
        data = grid_out.read()
        file_path.write_bytes(data)
        print(f"  ✓ Saved: {filename} ({len(data):,} bytes)")
        exported_count += 1

    if exported_count == 0:
        print("  No files found in GridFS.")
    else:
        print(f"\nSuccessfully exported {exported_count} files to {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()

