"""Publish the fitted carbon shoulders and the original-material factory wrist."""
from pathlib import Path
import json,hashlib,shutil,uuid,unreal as u
O=Path(__file__).resolve().parent
meta=json.loads((O/'Inputs/current.json').read_text());patch=json.loads((O/'Exports/factory-patch.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
Q,G,L,M=u.GeometryScript_MeshQueries,u.GeometryScript_AssetUtils,u.GeometryScript_List,u.GeometryScript_MeshEdits
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE_ACTIVE: preserve the user play session')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def disk(path):return Path(u.Paths.project_content_dir())/(path[6:]+'.uasset')
def check(k):
    row=meta[k];p=row['path']
    if p in dirty or hashlib.sha256(disk(p).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Concurrent target: '+p)
def load(p):
    o=u.load_asset(p)
    if not o:raise RuntimeError('Missing '+p)
    return o
for k in meta:check(k)
receipt={'complete':False,'meshes':{},'in_game_test':False}
def record():(O/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def labels(mesh):return {str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials}
def backup(k):
    p=disk(meta[k]['path']);dest=O/'Before'/p.name
    if dest.exists():
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=meta[k]['sha256']:raise RuntimeError('Backup differs '+str(p))
    else:shutil.copy2(p,dest)
def stage_carbon(k,kind,temp):
    p=O/'Exports'/('SM_M24_CarbonSpine_'+kind+'.fbx')
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.override_full_name=True
    imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False
    imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    t=u.AssetImportTask();t.filename=str(p);t.destination_name=p.stem;t.destination_path=temp;t.automated=True;t.replace_existing=False;t.save=False;t.options=opt;t.factory=u.FbxFactory()
    A.import_asset_tasks([t]);items=t.get_objects()
    if len(items)!=1:raise RuntimeError('FBX import '+str(p))
    m=items[0];slots=meta[k]['slots']
    if {str(s.material_slot_name) for s in m.static_materials}!=set(slots):raise RuntimeError('Carbon slots changed')
    for i,s in enumerate(m.static_materials):m.set_material(i,load(slots[str(s.material_slot_name)]))
    bs=SM.get_lod_build_settings(m,0);bs.recompute_normals=False;bs.recompute_tangents=False;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True
    u.ASH12AttachmentAssetTools.disable_runtime_fast_build(m);SM.set_lod_build_settings(m,0,bs)
    lod=u.StaticMeshReductionOptions();lod.auto_compute_lod_screen_size=False
    lod.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in ((1.,1.),(.5,.18),(.2,.075))]
    if SM.set_lods(m,lod)!=3 or not u.M24ChassisAssetTools.bake_stock_tangent_basis(m):raise RuntimeError('Carbon LOD build '+k)
    return m,p
temp='/Temp/M24R2_'+uuid.uuid4().hex[:12]
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    carbon={k:stage_carbon(k,kind,temp) for k,kind in [('native','Native'),('advanced','Advanced')]}
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
action=load(meta['action']['path']);new_idx=len(action.static_materials)
if action.get_num_lods()!=len(patch['remove']):raise RuntimeError('Action LOD layout changed')
factory=load(meta['host']['slots']['M24_FactoryStock'])
factory_lods=[]
for li,remove in enumerate(patch['remove']):
    dm,status=G.copy_mesh_from_static_mesh(action,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,use_build_scale=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=li))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Action source geometry')
    uvn=Q.get_num_uv_sets(dm)
    for entry in remove:
        valid,a,b,c=Q.get_triangle_positions(dm,entry['i'])
        if not valid or max(abs((getattr(a,ax)+getattr(b,ax)+getattr(c,ax))/3-entry['c'][j]) for j,ax in enumerate(('x','y','z')))>.001:raise RuntimeError('Action triangle identities changed')
    for entry in remove:
        _,ok=M.delete_triangle_from_mesh(dm,entry['i'],True)
        if not ok:raise RuntimeError('Action local removal')
    vertices=[];normals=[];triangles=[];uvs=[[] for _ in range(uvn)]
    for tri in patch['insert']:
        i=len(vertices);triangles.append(u.IntVector(i,i+1,i+2))
        vertices.extend(u.Vector(*v) for v in tri['pos']);normals.extend(u.Vector(*n) for n in tri['norm'])
        for j,vals in enumerate(uvs):vals.extend(u.Vector2D(*v) for v in tri['uv'][j])
    kw={'vertices':vertices,'normals':normals,'triangles':triangles}
    for j,arr in enumerate(uvs):kw['uv'+str(j)]=arr
    _,created=M.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(**kw),new_idx,True)
    ids=L.convert_index_list_to_array(created)
    if len(ids)!=len(triangles) or min(ids)<0:raise RuntimeError('Factory wrist append failed')
    factory_lods.append(dm)
# Only now bind final assets. The former coordinate mask also hit the metal sidewalls.
# Reuse the unmodified coating instance recipe for those faces.
coating='/Game/Weapons/M24/FactoryStockSeam20261105/MI_M24_ActionCoating_R2'
original='/Game/Weapons/M24/FinishUnified20261103/Materials/MI_M24_metal_c3b2cd1c02'
if E.does_asset_exist(coating):
    coat=load(coating)
    if E.get_metadata_tag(coat,'M24JunctionSource')!=original:raise RuntimeError('Occupied coating')
else:
    coat=E.duplicate_asset(original,coating)
    if not coat:raise RuntimeError('Coating creation')
    E.set_metadata_tag(coat,'M24JunctionSource',original)
    if not E.save_loaded_asset(coat,False):raise RuntimeError('Coating save')
for k in ('action','native','advanced'):check(k);backup(k)
slots=list(action.static_materials)
s=u.StaticMaterial();s.material_interface=factory;s.material_slot_name='M24_FactoryStockContinuation'
slots.append(s);action.set_editor_property('static_materials',slots)
idx=next(i for i,s in enumerate(slots) if str(s.material_slot_name)=='M24_AAS_CoatedMetal');action.set_material(idx,coat)
opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,enable_remove_degenerates=False,replace_materials=False,use_original_vertex_order=True)
for li,dm in enumerate(factory_lods):
    _,status=G.copy_mesh_to_static_mesh(dm,action,opts,u.GeometryScriptMeshWriteLOD(lod_index=li))
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Action source write')
    bs=SM.get_lod_build_settings(action,li);bs.recompute_normals=False;bs.recompute_tangents=True;bs.use_high_precision_tangent_basis=True;bs.use_full_precision_u_vs=True;SM.set_lod_build_settings(action,li,bs)
if not u.M24ChassisAssetTools.bake_stock_tangent_basis(action):raise RuntimeError('Action tangent frame build')
E.set_metadata_tag(action,'M24FactoryStockSource',str(O/'publish.py'))
objects={'action':action}
for k,(incoming,p) in carbon.items():
    dest=load(meta[k]['path']);dest.set_editor_property('static_materials',list(incoming.static_materials))
    for li in range(3):
        if SM.set_lod_from_static_mesh(dest,li,incoming,li,True)!=li:raise RuntimeError('Carbon LOD transfer')
    dest.get_editor_property('asset_import_data').scripted_add_filename(str(p),0,'')
    E.set_metadata_tag(dest,'Source',str(O/'M24_Meshy_JunctionR2.blend'));E.set_metadata_tag(dest,'M24CarbonSpineEdition','Meshy1105135808-JunctionR2')
    objects[k]=dest
for k,asset in objects.items():
    receipt['meshes'][k]={'path':asset.get_path_name(),'slots':labels(asset),'triangles':[asset.get_num_triangles(i) for i in range(asset.get_num_lods())]}
if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost() for a in objects.values()],False):raise RuntimeError('Could not save meshes')
receipt['complete']=True;receipt['factory_cut_distance_mm']=patch['max_cut_error_cm']*10;record();print('M24_JUNCTION_R2_SAVED',list(objects))
