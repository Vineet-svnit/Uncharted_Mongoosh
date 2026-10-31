"""pytest configuration for the data_layer tests."""
import sys
import os

# Ensure 'backend' directory and root are on the path
cur_dir = os.path.abspath(os.path.dirname(__file__))
parent_dir = os.path.abspath(os.path.join(cur_dir, ".."))
for p in [cur_dir, parent_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)


