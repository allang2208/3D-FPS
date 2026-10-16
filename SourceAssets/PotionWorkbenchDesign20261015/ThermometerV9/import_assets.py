"""Save V9 assets in a separate commandlet host; no live project/editor writes."""
from pathlib import Path
import unreal as u
import json, re

ROOT=Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve()!=(ROOT/'UEImportHost').resolve():
    raise RuntimeError('Wrong import host')
DEST='/Game/Building/PotionWorkbench20261015/ThermometerV9'
BASE='/Game/Building/PotionWorkbench20261015/V1/Materials/'
A=u.AssetToolsHelpers.get_asset_tools(); E=u.EditorAssetLibrary; M=u.MaterialEditingLibrary
report={'stage':'importing','packages':[],'runtime_tested':False}
def save(obj):
    E.set_metadata_tag(obj,'Alchemy.Owner','ThermometerV9')
    if not E.save_loaded_asset(obj,False): raise RuntimeError('Save failed '+obj.get_path_name())
    report['packages'].append(obj.get_path_name())
    (ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),'utf8')

# Keep the engine's distance-field font and edge treatment; make its text
# self-lit, so the meter remains legible in the shaded cauldron interior.
path=DEST+'/M_AlchemyTemperatureText'
if E.does_asset_exist(path):
    mat=u.load_asset(path)
    if E.get_metadata_tag(mat,'Alchemy.Owner')!='ThermometerV9': raise RuntimeError('Unowned '+path)
else:
    mat=E.duplicate_asset('/Engine/EngineMaterials/DefaultTextMaterialOpaque',path)
if not mat: raise RuntimeError('Could not create temperature text material')
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
color=M.create_material_expression(mat,u.MaterialExpressionVertexColor)
if not M.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR):
    raise RuntimeError('Could not connect display text color')
M.recompile_material(mat); save(mat)

u.load_module('StaticMeshEditor')
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI(); opt.import_mesh=True; opt.import_as_skeletal=False
opt.import_materials=False; opt.import_textures=False; opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
d=opt.static_mesh_import_data; d.combine_meshes=True; d.auto_generate_collision=False; d.generate_lightmap_u_vs=False
d.convert_scene=True; d.convert_scene_unit=True; d.force_front_x_axis=False; d.transform_vertex_to_absolute=True
d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS; d.remove_degenerates=False
canon=lambda s:re.sub('[^a-z0-9]','',str(s).lower())
for spec in json.loads((ROOT/'asset-manifest.json').read_text('utf8'))['parts']:
    asset_path=DEST+'/'+spec['name']
    if E.does_asset_exist(asset_path) and E.get_metadata_tag(u.load_asset(asset_path),'Alchemy.Owner')!='ThermometerV9':
        raise RuntimeError('Unowned '+asset_path)
    task=u.AssetImportTask(); task.filename=spec['lods'][0]['source']; task.destination_path=DEST; task.destination_name=spec['name']
    task.automated=True; task.replace_existing=True; task.save=False; task.options=opt
    A.import_asset_tasks([task]); mesh=next((o for o in task.get_objects() if isinstance(o,u.StaticMesh)),None)
    if not mesh: raise RuntimeError('Import failed '+spec['name'])
    mats={canon(n):u.load_asset(BASE+'M_'+n) for n in spec['materials']}
    for i,s in enumerate(mesh.static_materials):
        material=mats.get(canon(s.material_slot_name))
        if not material: raise RuntimeError('Missing material '+str(s.material_slot_name))
        mesh.set_material(i,material)
    for i,lod in enumerate(spec['lods'][1:],1):
        if SM.import_lod(mesh,i,lod['source'])<0: raise RuntimeError('LOD import failed')
    for i in range(SM.get_lod_count(mesh)):
        settings=SM.get_lod_build_settings(mesh,i)
        settings.use_full_precision_u_vs=True; settings.use_high_precision_tangent_basis=True
        settings.generate_lightmap_u_vs=False; settings.recompute_normals=False
        settings.recompute_tangents=True; settings.remove_degenerates=False
        SM.set_lod_build_settings(mesh,i,settings)
    SM.set_lod_screen_sizes(mesh,[1,.45,.18])
    nan=mesh.get_editor_property('nanite_settings'); nan.enabled=False; SM.set_nanite_settings(mesh,nan,True)
    save(mesh)
report['stage']='assets_saved'
(ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),'utf8')
u.log('ALCHEMY_THERMOMETER_ASSETS_SAVED')
