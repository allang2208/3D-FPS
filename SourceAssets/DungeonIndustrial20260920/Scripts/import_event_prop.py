"""Import an isolated copy of the existing local goddess candidate for the art slice."""
raise RuntimeError('Retired by user 2026-09-22: dungeon 5080 candidates are archived in trash/dungeon-5080-rejected-20260922; do not reimport this candidate.')
from pathlib import Path
import json
import unreal as u

root = Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonIndustrial20260920')
dest = '/Game/Dungeons/IndustrialV1/Props/GoddessCandidate'
eal = u.EditorAssetLibrary
assets = eal.list_assets(dest, True, False) if eal.does_directory_exist(dest) else []
meshes = [u.load_asset(p) for p in assets]
meshes = [m for m in meshes if isinstance(m,u.StaticMesh)]
if not meshes:
    task = u.AssetImportTask()
    task.set_editor_property('filename', 'D:/FPS3D/FPSGAME/SourceAssets/DungeonProps20260920/goddess_statue/textured_master_00001_.glb')
    task.set_editor_property('destination_path', dest)
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', False)
    task.set_editor_property('save', False)
    task.set_editor_property('async_', False)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    print('Import task paths: '+str(task.get_editor_property('imported_object_paths')))
    imported_objects=task.get_objects()
    assets = eal.list_assets(dest, True, False)
    meshes = [m for m in imported_objects if isinstance(m,u.StaticMesh)]
    if not meshes:
        meshes = [u.load_asset(p) for p in assets]
meshes = [a for a in meshes if isinstance(a,u.StaticMesh)]
if len(meshes) != 1:
    raise RuntimeError('Expected one imported statue mesh, got '+str(len(meshes)))
mesh = meshes[0]
# The generic GLB importer may return a transient MaterialInstanceDynamic.
# Persist the source GLB's explicit base color and G/B roughness/metalness in
# a real material asset before saving the static mesh; retain the generated UVs.
mat_path=dest+'/M_GoddessStone'
mat=u.load_asset(mat_path)
if not mat:
    mat=u.AssetToolsHelpers.get_asset_tools().create_asset('M_GoddessStone',dest,u.Material,u.MaterialFactoryNew())
    lib=u.MaterialEditingLibrary
    for index,links in [(0,[('RGB',u.MaterialProperty.MP_BASE_COLOR)]),
                        (1,[('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)])]:
        texture=u.load_asset(dest+'/textured_master_00001_/Textures/textured_master_00001__texture_'+str(index))
        if not texture:
            raise RuntimeError('Missing source statue texture '+str(index))
        if index==1:
            texture.set_editor_property('srgb',False)
            texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        if not eal.save_loaded_asset(texture,False):
            raise RuntimeError('Unable to persist statue texture '+str(index))
        sampler=lib.create_material_expression(mat,u.MaterialExpressionTextureSample)
        sampler.set_editor_property('texture',texture)
        sampler.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR if index==0 else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        for channel,pin in links:
            if not lib.connect_material_property(sampler,channel,pin):
                raise RuntimeError('Statue material input failed: '+str(pin))
    lib.recompile_material(mat)
    if not eal.save_loaded_asset(mat,False):
        raise RuntimeError('Unable to save statue material')
for index in range(len(mesh.get_editor_property('static_materials'))):
    mesh.set_material(index,mat)
nanite = mesh.get_editor_property('nanite_settings')
nanite.set_editor_property('enabled', True)
mesh.set_editor_property('nanite_settings', nanite)
body = mesh.get_editor_property('body_setup')
body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
if not eal.save_loaded_asset(mesh,False):
    raise RuntimeError('Unable to save imported statue mesh')
b = mesh.get_bounds()
info = {'mesh':mesh.get_path_name(),'origin':list(b.origin.to_tuple()),'extent':list(b.box_extent.to_tuple()),
        'source':'../DungeonProps20260920/goddess_statue/textured_master_00001_.glb',
        'status':'local candidate placed as art only; no event interaction', 'tests_run':False}
(root/'Receipts/event-prop.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
print(json.dumps(info))
for cls, names in [(u.SubobjectDataSubsystem,['k2_gather_subobject_data_for_instance','add_new_subobject']),
                   (u.SubobjectDataBlueprintFunctionLibrary,['get_data','get_object'])]:
    for name in names:
        print(cls.__name__+'.'+name+': '+str(getattr(getattr(cls,name,None),'__doc__',None)))
