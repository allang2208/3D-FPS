"""Bake the three wedge-cell preview ghost meshes (2026-10-15).

SM_VoxelWedge45 / SM_VoxelWedge26L / SM_VoxelWedge26U are authored for the +X
rising direction through the same surface generator that meshes placed buildings
(UVoxelSurfaceLibrary::CreateExampleMeshCut), so the preview geometry matches the
placed result exactly, bevel included. The component rotates instances per cut
direction at runtime; no per-direction assets are needed.

Usage (editor closed):
    UnrealEditor-Cmd <uproject> -run=pythonscript -script=Tools/Building/bake_wedge_ghosts_20261015.py -nullrhi -unattended
"""
import unreal as u

EAL = u.EditorAssetLibrary
DEST = '/Game/Building/Voxels/Rounded'
edge_radius = 1.4
preview_material = u.load_asset(DEST + '/M_Voxel_PlacementPreview.M_Voxel_PlacementPreview')
mesh_editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)

# VoxelCut::Make(dir=1(+X), pattern) 的编码值(与 C++ 同式,值=1+((dir-1)|pattern<<2))
KINDS = [
    ('SM_VoxelWedge45', 1 + (0 << 2)),   # 45° 整格
    ('SM_VoxelWedge26L', 1 + (1 << 2)),  # 26° 下半格 0→10
    ('SM_VoxelWedge26U', 1 + (2 << 2)),  # 26° 上半格 10→20
    ('SM_VoxelTent', 1 + (0 << 2) + 12), # 帐篷(pattern3, Dir1=脊沿 Y)=13
]

for name, cut in KINDS:
    path = DEST + '/' + name
    dynamic = u.VoxelSurfaceLibrary.create_example_mesh_cut(edge_radius, cut)
    if not dynamic:
        raise RuntimeError('mesher returned nothing for ' + name)
    mesh = u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset('/Engine/BasicShapes/Cube', path)
    settings = mesh_editor.get_lod_build_settings(mesh, 0)
    settings.set_editor_property('build_scale3d', u.Vector(1, 1, 1))
    mesh_editor.set_lod_build_settings(mesh, 0, settings)
    options = u.GeometryScriptCopyMeshToAssetOptions()
    options.set_editor_property('enable_recompute_normals', False)
    options.set_editor_property('enable_recompute_tangents', True)
    options.set_editor_property('replace_materials', True)
    options.set_editor_property('new_materials', [preview_material] if preview_material else [])
    options.set_editor_property('use_build_scale', False)
    _, outcome = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic, mesh, options, u.GeometryScriptMeshWriteLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('copy failed for ' + name)
    if preview_material:
        mesh.set_material(0, preview_material)
    mesh_editor.remove_collisions(mesh)   # ghost 专用,无碰撞
    if not EAL.save_loaded_asset(mesh, False):
        raise RuntimeError('save failed for ' + name)
    back = u.load_asset(path)
    u.log('[wedge] %s cut=%d tris=%d extent=%s' % (name, cut, back.get_num_triangles(0), str(back.get_bounds().box_extent)))
u.log('[wedge] DONE')
