"""Resume after textures/material saved; native FBX import creates collision headlessly."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpoiledFood20261016')
DEST='/Game/Items/Consumables/SpoiledFood20261016'
EAL=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
names=['T_SpoiledFood_BaseColor','T_SpoiledFood_Roughness','T_SpoiledFood_NormalGL','M_SpoiledFood']
assets=[u.load_asset(DEST+'/'+name) for name in names]
if any(a is None for a in assets):raise RuntimeError('Saved first-stage assets missing')
if EAL.does_asset_exist(DEST+'/SM_SpoiledFood'):raise RuntimeError('Unexpected saved mesh; preserve it')
opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False
opts.import_as_skeletal=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opts.automated_import_should_detect_type=False
d=opts.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=True
d.generate_lightmap_u_vs=True;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
t=u.AssetImportTask();t.filename=str(ROOT/'SM_SpoiledFood.fbx');t.destination_path=DEST;t.destination_name='SM_SpoiledFood'
t.automated=True;t.replace_existing=False;t.save=False;t.options=opts
AT.import_asset_tasks([t]);mesh=u.load_asset(DEST+'/SM_SpoiledFood')
if mesh is None:raise RuntimeError('Mesh import failed')
mesh.set_material(0,assets[-1])
if not EAL.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed')
b=mesh.get_bounds()
report={'saved_packages':[a.get_path_name() for a in assets]+[mesh.get_path_name()],
    'mesh':mesh.get_path_name(),'material':assets[-1].get_path_name(),
    'dimensions_cm':[2*b.box_extent.x,2*b.box_extent.y,2*b.box_extent.z],
    'texture_maps':['BaseColor','Roughness','NormalGL'],'normal_green_flipped':True,
    'collision':'FBX auto_generate_collision; pickup uses its existing box body',
    'resume_from':'asset-import-blocks-02; textures and material saved before subsystem error',
    'game_or_pie_started':False,'runtime_test_performed':False}
(ROOT/'ue-assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('SPOILED_FOOD_SAVED',json.dumps(report))
