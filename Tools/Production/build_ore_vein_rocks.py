"""Rebuild mineral surfaces and four shape variants per mineral; no map or game."""
from pathlib import Path
import runpy

ROOT=Path(__file__).parent
surface=runpy.run_path(str(ROOT/'build_ore_surface.py'))
surface['build_materials']()
variants=runpy.run_path(str(ROOT/'build_ore_rock_variants.py'))
variants['build_variants'].__globals__['ROOT']=surface['ROOT']
variants['build_variants']()
