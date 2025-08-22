import sys
from pathlib import Path

# Add the project root to the sys.path so that the 'src' package is importable
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
