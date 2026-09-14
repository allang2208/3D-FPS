"""Repair and compile the V9 smoke material's Niagara sprite shader permutation.

Asset authoring only: no map loading, gameplay, screenshots or preview rendering.
"""
import unreal

path = '/Game/Weapons/GunplayFX/M_MuzzleSmokeSheetV9'
material = unreal.load_asset(path)
if not material:
    raise RuntimeError('Missing current smoke material: ' + path)
lib = unreal.MaterialEditingLibrary
lib.set_base_material_usage(material, unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
errors = lib.recompile_material(material)
if errors:
    raise RuntimeError('Smoke sprite shader compilation failed: ' + '\n'.join(errors))
if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
    raise RuntimeError('Could not save smoke material: ' + path)
unreal.log('GUNPLAY_SMOKE_SPRITE_USAGE_REPAIRED ' + material.get_path_name())
