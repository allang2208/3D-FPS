"""Import saved assembly components, original finishes and a ghost material."""
import json,re
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/GunWorkbench20260927'
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Exit PIE to import')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
def norm(s):return re.sub('[^a-z0-9]','',re.sub(r'[._][0-9]{3}$','',str(s)).lower())
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
rifle=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
mats={norm(s.material_slot_name):s.material_interface for s in rifle.get_editor_property('materials')}
manifest=json.loads((ROOT/'Assembly/manifest.json').read_text(encoding='utf-8'));saved=[]
for row in manifest['meshes']:
    task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=row['path'].rsplit('/',1)[0];task.destination_name=row['name']
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
    d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(row['path'])
    if not mesh:raise RuntimeError('Missing import '+row['path'])
    for i,s in enumerate(mesh.get_editor_property('static_materials')):
        mat=mats.get(norm(s.material_slot_name))
        if not mat:raise RuntimeError('Unmapped M4 material: '+str(s.material_slot_name))
        mesh.set_material(i,mat)
    save(mesh);saved.append(mesh.get_path_name())
dest='/Game/Building/GunWorkbench20260927/Assembly';mat=u.load_asset(dest+'/M_AssemblyGhost')
if not mat:mat=A.create_asset('M_AssemblyGhost',dest,u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(mat);mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT);mat.set_editor_property('two_sided',True)
color=L.create_material_expression(mat,u.MaterialExpressionVectorParameter);color.set_editor_property('parameter_name','Tint');color.set_editor_property('default_value',u.LinearColor(.6,.7,.75,1))
opacity=L.create_material_expression(mat,u.MaterialExpressionConstant);opacity.set_editor_property('r',.22)
L.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR);L.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
L.recompile_material(mat);L.get_statistics(mat);save(mat)
(ROOT/'Receipts/assembly-import.json').write_text(json.dumps({'saved':saved,'ghost':mat.get_path_name(),'tests_run':False,'renders_run':False},indent=2),encoding='utf-8')
print('ASSEMBLY_ASSETS_SAVED '+str(len(saved)))
