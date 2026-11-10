"""One serialized editor production batch for the new flame assets and sources."""
import sys
import importlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_surface_profiles
import install
importlib.reload(build_surface_profiles)
importlib.reload(install)
build_surface_profiles.run()
install.run()
