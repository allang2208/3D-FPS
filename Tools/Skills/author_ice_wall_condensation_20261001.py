"""Serialized asset creation and saving only; no preview or gameplay run."""
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0, str(Path(u.Paths.project_dir()) / 'Tools/Skills'))
import build_ice_wall_gather_v2
import build_ice_wall_slam_v3

build_ice_wall_gather_v2.main()
build_ice_wall_slam_v3.main()
