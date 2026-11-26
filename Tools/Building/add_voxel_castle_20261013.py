"""Add the fourth voxel material "castle" (medieval stylized stone wall) to the palette.

Follows the marble precedent: reference an externally authored material instance
(MI_FreeStoneWall01A from the Fab Free Stylized Stone Wall 01A pack) and carry the
stone-class physics in the asset itself (bOverridePhysics), so UVoxelBuildPalette::Physical()
needs no code change. Append-only: the existing wood/stone/marble entries (marble was
hand-edited later) are preserved verbatim.

Also exports the BaseColor texture to a PNG for offline icon cropping.

Usage (editor ideally closed; palette is the only shared asset - reload it in a live editor):
    UnrealEditor-Cmd <uproject> -run=pythonscript -script=Tools/Building/add_voxel_castle_20261013.py -nullrhi -unattended
"""

import unreal as u

EAL = u.EditorAssetLibrary

PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette.DA_VoxelBuildPalette'
SURFACE = '/Game/FreeStoneWall01A/Materials/MI_FreeStoneWall01A.MI_FreeStoneWall01A'
TEX_C = '/Game/FreeStoneWall01A/Textures/T_FreeStoneWall01A_C.T_FreeStoneWall01A_C'
EXPORT_PNG = 'D:/FPS3D/FPSGAME/Saved/castle_icon_source.png'

pal = u.load_asset(PALETTE)
surface = u.load_asset(SURFACE)
tex_c = u.load_asset(TEX_C)
assert pal and surface and tex_c, 'palette/surface/texture missing'

entries = list(pal.get_editor_property('materials'))
if any(e.get_editor_property('id') == 'castle' for e in entries):
    u.log('[castle] already present, nothing to do')
else:
    entry = u.VoxelBuildMaterial()
    entry.set_editor_property('id', 'castle')
    entry.set_editor_property('display_name', u.Text('城墙石'))
    entry.set_editor_property('surface', surface)
    # Marble precedent: reuse the stone example mesh (icon/thumbnail purposes only).
    entry.set_editor_property('example_mesh', u.load_asset('/Game/Building/Voxels/Rounded/SM_Voxel20_Stone.SM_Voxel20_Stone'))
    entry.set_editor_property('override_physics', True)
    physics = u.VoxelPhysicalMaterial()
    physics.set_editor_property('density_kg_m3', 650.0)
    physics.set_editor_property('compression_pa', 6000000.0)
    physics.set_editor_property('tension_pa', 900000.0)
    physics.set_editor_property('shear_pa', 300000.0)
    physics.set_editor_property('durability', 500.0)
    physics.set_editor_property('joules_per_damage', 15.0)
    entry.set_editor_property('physics', physics)
    entries.append(entry)
    pal.set_editor_property('materials', entries)
    if not EAL.save_loaded_asset(pal, False):
        raise RuntimeError('could not save palette')
    u.log('[castle] palette entry added and saved')

for e in pal.get_editor_property('materials'):
    u.log('[castle] entry id=%s override=%s' % (e.get_editor_property('id'), e.get_editor_property('override_physics')))

task = u.AssetExportTask()
task.set_editor_property('object', tex_c)
task.set_editor_property('filename', EXPORT_PNG)
task.set_editor_property('automated', True)
task.set_editor_property('prompt', False)
ok = u.AssetToolsHelpers.get_asset_tools().export_asset_task(task)
u.log('[castle] texture export result=%s file=%s' % (ok, EXPORT_PNG))
