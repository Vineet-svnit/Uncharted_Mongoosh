"""pytest configuration for the data_layer tests."""
import sys
import os

# Ensure 'backend' directory is on the path so `from data_layer import ...` works
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

