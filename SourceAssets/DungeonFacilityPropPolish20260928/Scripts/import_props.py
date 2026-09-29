"""Install and save only the two authorized production meshes and their atlas dependencies."""
import hashlib,json,sys,shutil
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/FacilityPropPolish20260928'
MESH_BASE='/Game/Dungeons/FacilityScenes20260927/Meshes'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active play; exit PIE before importing these two assets')
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
initial_dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
manifest=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
targets=[MESH_BASE+'/'+item['name'] for item in manifest['objects']]
for path in targets:
    if path in initial_dirty:raise RuntimeError('Preserve unsaved target '+path)
receipt_path=ROOT/'Receipts/install.json'
receipt=json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {'revision':'precision_prop_polish_20260928','saved':[],'meshes':{},'tests_run':False}
def write():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    path=asset.get_path_name()
    if path not in receipt['saved']:receipt['saved'].append(path)
    write()
def own(path):
    if path in initial_dirty:raise RuntimeError('Preserve unsaved dependency '+path)

# Keep the pre-edit packages and author inputs, without modifying their live objects.
backup=ROOT/'Backup';backup.mkdir(exist_ok=True)
for path in targets:
    local=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    for source in (local,local.with_suffix('.uexp'),local.with_suffix('.ubulk')):
        if source.exists() and not (backup/source.name).exists():shutil.copy2(source,backup/source.name)

textures={}
for suffix in ('BaseColor','NormalGL','ORM'):
    path=BASE+'/Textures/T_FacilityProp_'+suffix;own(path)
    task=u.AssetImportTask();task.filename=str(ROOT/'Authored/Textures'/('T_FacilityProp_'+suffix+'.png'))
    task.destination_path=BASE+'/Textures';task.destination_name='T_FacilityProp_'+suffix
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    A.import_asset_tasks([task]);texture=u.load_asset(path)
    if not texture:raise RuntimeError('Texture import failed '+path)
    texture.set_editor_property('srgb',suffix=='BaseColor')
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7 if suffix=='BaseColor' else u.TextureCompressionSettings.TC_NORMALMAP if suffix=='NormalGL' else u.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('never_stream',False)
    if suffix=='NormalGL':texture.set_editor_property('flip_green_channel',True)
    save(texture);textures[suffix]=texture

mat_path=BASE+'/Materials/M_FacilityProp_Atlas';own(mat_path)
mat=u.load_asset(mat_path) or A.create_asset('M_FacilityProp_Atlas',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
mat.modify();L.delete_all_material_expressions(mat)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
mat.set_editor_property('two_sided',False)
mat.set_editor_property('used_with_instanced_static_meshes',True)
mat.set_editor_property('used_with_nanite',True)
for suffix in ('BaseColor','NormalGL','ORM'):
    sample=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
    sample.set_editor_property('parameter_name',suffix);sample.set_editor_property('texture',textures[suffix])
    sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR if suffix=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if suffix=='NormalGL' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    outputs={'RGB':u.MaterialProperty.MP_BASE_COLOR} if suffix=='BaseColor' else {'RGB':u.MaterialProperty.MP_NORMAL} if suffix=='NormalGL' else {'R':u.MaterialProperty.MP_AMBIENT_OCCLUSION,'G':u.MaterialProperty.MP_ROUGHNESS,'B':u.MaterialProperty.MP_METALLIC}
    for channel,prop in outputs.items():
        if not L.connect_material_property(sample,channel,prop):raise RuntimeError('Material output failed '+suffix+'/'+channel)
L.layout_material_expressions(mat)
errors=L.recompile_material(mat)
if errors:raise RuntimeError('Atlas material compilation failed '+str(errors))
save(mat)

for item in manifest['objects']:
    name=item['name'];path=MESH_BASE+'/'+name
    receipt.setdefault('pending',{})[name]={'path':path,'fbx':item['fbx']};write()
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=MESH_BASE;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
    options.import_as_skeletal=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True
    data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task])
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Mesh import failed '+path)
    mesh.modify()
    # Keep the FBX importer's read-only ImportedMaterialSlotName metadata.
    slots=mesh.get_editor_property('static_materials')
    slot=next((entry for entry in slots if str(entry.get_editor_property('imported_material_slot_name'))=='FacilityProp_Atlas'),slots[0]).copy()
    slot.set_editor_property('material_interface',mat);slot.set_editor_property('material_slot_name','FacilityProp_Atlas')
    mesh.set_editor_property('static_materials',[slot])
    body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    nanite=mesh.get_editor_property('nanite_settings').copy();nanite.enabled=True;nanite.explicit_tangents=True
    nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED;nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    nanite.fallback_percent_triangles=1.;nanite.fallback_relative_error=0
    mesh.set_editor_property('nanite_settings',nanite)
    if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
    aggregate=body.get_editor_property('agg_geom')
    shapes=sum(len(aggregate.get_editor_property(key)) for key in ('box_elems','sphere_elems','sphyl_elems','convex_elems'))
    if shapes!=item['collision_boxes']:raise RuntimeError('Authored collision import incomplete '+path)
    save(mesh)
    receipt['meshes'][name]={'path':path,'source_sha256':hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest(),'source_triangles':item['triangles'],'collision_shapes':shapes,'material_slots':1,'nanite':True,'explicit_tangents':True,'fallback_fraction':1}
    receipt['pending'].pop(name,None);write()
    print('FACILITY_PROP_SAVED',name,'triangles',item['triangles'],'collision',shapes,flush=True)
receipt['stage']='assets_saved';receipt['map_saved']=False;write()
print('FACILITY_PROP_POLISH_INSTALLED',len(receipt['meshes']),flush=True)
