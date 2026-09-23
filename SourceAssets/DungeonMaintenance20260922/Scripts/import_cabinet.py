"""Build precise maintenance cabinet assets and physical material families."""
import unreal as u,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/AtmosphereV2/Maintenance'
MAN=json.loads((ROOT/'Authored/manifest.json').read_text());A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Wrong project')
allowed=set(globals().get('MAINTENANCE_RESUME_ASSETS',[]))
if any(p.get_path_name().startswith(BASE+'/') and p.get_path_name() not in allowed for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved maintenance assets')
textures={k:u.load_asset('/Game/Dungeons/AtmosphereV2/Services/Textures/T_Service_'+k) for k in ('AgeMask','Normal')}
if not all(textures.values()):raise RuntimeError('Authored service texture dependency missing')
def expr(name):return L.create_material_expression(mat,getattr(u,'MaterialExpression'+name))
def wire(a,ao,b,bi):
    if not L.connect_material_expressions(a,ao,b,bi):raise RuntimeError(bi)
def output(a,ao,prop):
    if not L.connect_material_property(a,ao,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError(prop)
def scalar(x):n=expr('Constant');n.set_editor_property('r',x);return n
def color(c):n=expr('Constant3Vector');n.set_editor_property('constant',u.LinearColor(*c,1));return n
def blend(a,b,mask):
    n=expr('LinearInterpolate');wire(a,'',n,'A');wire(b,'',n,'B');wire(mask,'',n,'Alpha');return n
materials={}
for key,r in MAN['materials'].items():
    name='M_Maintenance_'+key;mat=u.load_asset(BASE+'/Materials/'+name)
    if not mat:mat=A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat);base=color(r['color']);rough=scalar(r['roughness']);metal=scalar(r['metallic'])
    if key in ('Enamel','Interior','Steel','Bakelite'):
        noise=expr('TextureSample');noise.set_editor_property('texture',textures['AgeMask']);noise.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        vc=expr('VertexColor');sub=expr('Subtract');wire(noise,'R',sub,'A');wire(scalar(.62),'',sub,'B')
        scale=expr('Multiply');wire(sub,'',scale,'A');wire(scalar(6),'',scale,'B');clamp=expr('Saturate');wire(scale,'',clamp,'')
        edge=expr('Multiply');wire(clamp,'',edge,'A');wire(vc,'R',edge,'B')
        base=blend(base,color([.11,.118,.11] if key in ('Enamel','Interior') else [v*.6 for v in r['color']]),edge)
        rough=blend(rough,scalar(.44 if key in ('Enamel','Interior') else .70),edge)
        if key in ('Enamel','Interior'):metal=blend(metal,scalar(.78),edge)
        grime=expr('ComponentMask');wire(vc,'',grime,'');grime.set_editor_property('g',True);grime.set_editor_property('r',False)
        base=blend(base,color([v*.60 for v in r['color']]),grime);rough=blend(rough,scalar(.81),grime)
        nm=expr('TextureSample');nm.set_editor_property('texture',textures['Normal']);nm.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL);output(nm,'RGB','NORMAL')
    output(base,'','BASE_COLOR');output(rough,'','ROUGHNESS');output(metal,'','METALLIC')
    if r.get('emission'):output(color([v*.6 for v in r['emission']]),'','EMISSIVE_COLOR')
    L.layout_material_expressions(mat);L.recompile_material(mat)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Material save '+key)
    materials['Maintenance_'+key]=mat
task=u.AssetImportTask();task.filename=MAN['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=MAN['name']
task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
d=options.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
d.generate_lightmap_u_vs=False;d.auto_generate_collision=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
d.vertex_color_import_option=u.VertexColorImportOption.REPLACE;task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task])
mesh=u.load_asset(BASE+'/Meshes/'+MAN['name'])
for i,slot in enumerate(mesh.get_editor_property('static_materials')):
    key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mesh.set_material(i,materials[key])
# Small text, thin cables and breaker geometry retain their authored silhouette.
ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;mesh.set_editor_property('nanite_settings',ns)
mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cabinet mesh save')
(ROOT/'Receipts').mkdir(exist_ok=True)
(ROOT/'Receipts/cabinet-import.json').write_text(json.dumps(dict(mesh=mesh.get_path_name(),materials=[m.get_path_name() for m in materials.values()],stage='assets_saved',tests_run=False),indent=2),encoding='utf-8')
print('MAINTENANCE_CABINET_ASSETS_SAVED')
