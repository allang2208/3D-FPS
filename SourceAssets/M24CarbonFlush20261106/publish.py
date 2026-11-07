"""Save both directly joined carbon-stock variants at their existing game paths."""
from pathlib import Path
import json,hashlib,shutil,uuid,unreal as u
O=Path(__file__).resolve().parent
meta=json.loads((O/'current.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE_ACTIVE: preserve the user play session')

def disk(path):return Path(u.Paths.project_content_dir())/(path[6:]+'.uasset')
def available(k):
    row=meta[k];p=row['path']
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if p in dirty or hashlib.sha256(disk(p).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Concurrent target: '+p)
def load(p):
    o=u.load_asset(p)
    if not o:raise RuntimeError('Missing '+p)
    return o
def backup(k):
    p=disk(meta[k]['path']);dest=O/'Before'/p.name
    if dest.exists():
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=meta[k]['sha256']:raise RuntimeError('Backup differs '+str(p))
    else:shutil.copy2(p,dest)

for k in meta:available(k)
receipt={'complete':False,'meshes':{},'in_game_test':False,'source':'M24_Carbon_DirectFlush.blend'}
(O/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')

def stage(k,kind,temp):
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

temp='/Temp/M24CarbonFlush_'+uuid.uuid4().hex[:12]
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    staged={k:stage(k,kind,temp) for k,kind in [('native','Native'),('advanced','Advanced')]}
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
for k in staged:available(k);backup(k)
objects={}
for k,(incoming,p) in staged.items():
    dest=load(meta[k]['path']);dest.set_editor_property('static_materials',list(incoming.static_materials))
    for li in range(3):
        if SM.set_lod_from_static_mesh(dest,li,incoming,li,True)!=li:raise RuntimeError('Carbon LOD transfer')
    dest.get_editor_property('asset_import_data').scripted_add_filename(str(p),0,'')
    E.set_metadata_tag(dest,'Source',str(O/'M24_Carbon_DirectFlush.blend'))
    E.set_metadata_tag(dest,'M24CarbonSpineEdition','Meshy1105135808-DirectFlush20261106')
    objects[k]=dest
    receipt['meshes'][k]={'path':dest.get_path_name(),
        'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in dest.static_materials},
        'triangles':[dest.get_num_triangles(i) for i in range(dest.get_num_lods())]}
if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost() for a in objects.values()],False):raise RuntimeError('Could not save meshes')
receipt['complete']=True
receipt['construction']=json.loads((O/'construction.json').read_text())
(O/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('M24_DIRECT_FLUSH_SAVED',list(objects))
