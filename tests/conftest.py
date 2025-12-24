# tests/conftest.py
"""
Pytest configuration file for test setup.
This file is automatically loaded by pytest and sets up the Python path.
"""
import sys
from pathlib import Path

# Add backend directory to Python path for imports
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

