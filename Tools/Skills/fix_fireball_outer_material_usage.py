"""Persist missing Niagara sprite usage without rebuilding the effect graph."""
from pathlib import Path
import sys
import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fireball_outer_flame import DEST, LIB, save, enable_sprite_usage

mat = unreal.load_asset(DEST + '/M_FireballOuterFireFlame')
instance = unreal.load_asset(DEST + '/MI_FireballOuterFireFlame')
if not mat or not instance:
    raise RuntimeError('Missing installed outer-flame material')

enable_sprite_usage(mat, instance)
errors = LIB.recompile_material(mat)
if errors:
    raise RuntimeError('Outer-flame material compilation failed: ' + '; '.join(errors))
LIB.update_material_instance(instance)
save(mat)
save(instance)
unreal.log('FIREBALL_OUTER_NIAGARA_SPRITE_USAGE_SAVED')
