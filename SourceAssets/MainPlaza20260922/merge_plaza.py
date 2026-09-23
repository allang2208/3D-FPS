"""Compatibility entry: bounded Nanite instances replace the former whole-edge mesh merge.

The previous implementation collapsed LOD chains and widened culling bounds. Its source is
retained in MainScenePerformance20260923/Before. No existing merged actor is destroyed here.
"""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent.parent / 'MainScenePerformance20260923' / 'apply_scene.py'), run_name='__main__')
