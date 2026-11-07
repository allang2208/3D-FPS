"""Install two rigid carbon-stock assemblies and two fitted rail seats."""
from pathlib import Path
import unreal as u,json,hashlib,shutil,uuid
O=Path(__file__).resolve().parent
meta=json.loads((O/'Inputs/current.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; preserve session')
def disk(path):return Path(u.Paths.project_content_dir())/(path[6:]+'.uasset')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    return a
def available(k):
    r=meta[k];dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if r['path'] in dirty or hashlib.sha256(disk(r['path']).read_bytes()).hexdigest()!=r['sha256']:raise RuntimeError('Concurrent edit '+k)
def import_mesh(f,folder,slots,stock):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.override_full_name=True
    imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    t=u.AssetImportTask();t.filename=str(f);t.destination_path=folder;t.destination_name=f.stem;t.automated=True;t.replace_existing=False;t.save=False;t.options=opt;t.factory=u.FbxFactory()
    A.import_asset_tasks([t]);objects=t.get_objects()
    if len(objects)!=1:raise RuntimeError('Import '+str(f))
    m=objects[0]
    if {str(s.material_slot_name) for s in m.static_materials}!=set(slots):raise RuntimeError('Material slots changed '+str(f))
    for i,s in enumerate(m.static_materials):m.set_material(i,load(slots[str(s.material_slot_name)]))
    u.ASH12AttachmentAssetTools.disable_runtime_fast_build(m)
    bs=SM.get_lod_build_settings(m,0);bs.recompute_normals=False;bs.recompute_tangents=False;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True;SM.set_lod_build_settings(m,0,bs)
    lod=u.StaticMeshReductionOptions();lod.auto_compute_lod_screen_size=False
    lod.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in ((1.,1.),(.5,.18),(.2,.075))] if stock else [u.StaticMeshReductionSettings(percent_triangles=1.,screen_size=1.)]
    SM.set_lods(m,lod)
    if not u.M24ChassisAssetTools.bake_stock_tangent_basis(m):raise RuntimeError('Tangent build '+str(f))
    return m
for k in ('carbon_native','carbon_advanced'):available(k)
for kind in ('native','advanced'):
    path='/Game/Weapons/M24/RailSeats20261106/Meshes/SM_M24_m24_rail_seat_'+kind
    if E.does_asset_exist(path):raise RuntimeError('Existing rail seat retained '+path)
receipt={'complete':False,'assets':{},'runtime_tested':False}
(O/'saved.json').write_text(json.dumps(receipt,indent=2))
staged={};temp='/Temp/M24NaturalStock_'+uuid.uuid4().hex[:10]
flag='Interchange.FeatureFlags.Import.FBX';prev=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    for kind in ('Native','Advanced'):
        k='carbon_'+kind.lower();f=O/'Exports'/('SM_M24_CarbonSpine_'+kind+'.fbx');slots={s['name']:s['material'] for s in meta[k]['slots']}
        staged[k]=import_mesh(f,temp,slots,True)
    for kind in ('native','advanced'):
        k='rail_'+kind;f=O/'Exports'/('SM_M24_m24_rail_seat_'+kind+'.fbx')
        material=meta['carbon_native']['slots'][0]['material'] if kind=='native' else meta['advanced_front']['slots'][0]['material']
        staged[k]=import_mesh(f,'/Game/Weapons/M24/RailSeats20261106/Meshes',{'RailSeat_'+kind:material},False)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prev))
for k in ('carbon_native','carbon_advanced'):
    available(k);f=disk(meta[k]['path']);dest=O/'Before'/f.name
    if not dest.exists():shutil.copy2(f,dest)
objects={}
for k,inc in staged.items():
    if k.startswith('carbon_'):
        m=load(meta[k]['path']);m.set_editor_property('static_materials',list(inc.static_materials))
        for li in range(inc.get_num_lods()):
            if SM.set_lod_from_static_mesh(m,li,inc,li,True)!=li:raise RuntimeError('LOD transfer '+k)
        source=O/'Exports'/('SM_M24_CarbonSpine_'+k.split('_')[1].title()+'.fbx')
        m.get_editor_property('asset_import_data').scripted_add_filename(str(source),0,'')
        E.set_metadata_tag(m,'Source',str(O/'M24_NaturalStock.blend'))
        E.set_metadata_tag(m,'M24CarbonSpineEdition','Meshy1105135808-RigidNatural20261106')
    else:
        m=inc;E.set_metadata_tag(m,'Source',str(O/'M24_RailSeats.blend'))
    objects[k]=m;receipt['assets'][k]={'path':m.get_path_name(),'triangles':[m.get_num_triangles(li) for li in range(m.get_num_lods())],'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in m.static_materials}}
if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost() for a in objects.values()],False):raise RuntimeError('Save failed')
receipt['complete']=True
(O/'saved.json').write_text(json.dumps(receipt,indent=2));print('M24_NATURAL_STOCK_RAIL_SAVED',list(objects))
