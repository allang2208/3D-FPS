"""Save ReceiverGrip08 using native geometry copy; preserve current paths/rig.

Run through ../WeaponSurface20260930/run_ue.ps1. No game preview is started.
"""
import array,hashlib,json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve()
if P!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project')
META=json.loads((O/'Input/current.json').read_text());PLAN=json.loads((O/'authoring.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
AU,Q,LU=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List
ED,UVS,NRM,MATS,BW=u.GeometryScript_MeshEdits,u.GeometryScript_UVs,u.GeometryScript_Normals,u.GeometryScript_Materials,u.GeometryScript_BoneWeights
ROOT='/Game/Weapons/A762/ReceiverGrip20261001';VERSION='ReceiverGrip08-20261001'
RP=O/'install_receipt.json';receipt=json.loads(RP.read_text()) if RP.exists() else {'version':VERSION,'materials':{},'saved':{},'complete':False,'runtime_tested':False}
def record():RP.write_text(json.dumps(receipt,indent=2))
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def pick(result,cls):return next(x for x in result if isinstance(x,cls)) if isinstance(result,tuple) else result
def ids(fn,*a):return LU.convert_index_list_to_array(pick(fn(*a),u.GeometryScriptIndexList))
def weights(dm,v):return next(x for x in BW.get_vertex_bone_weights(dm,v) if isinstance(x,(list,u.Array)))
def success(result,label):
    pins=[x for x in result if isinstance(x,u.GeometryScriptOutcomePins)] if isinstance(result,tuple) else []
    if pins and pins[0]!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(label+' failed')
def load(path):
    ob=u.load_asset(path)
    if not ob:raise RuntimeError('Missing '+path)
    return ob
def save(ob):
    if not E.save_loaded_asset(ob,False):raise RuntimeError('Save failed '+ob.get_path_name())
def read_mesh(mesh,body):
    dm=u.DynamicMesh();fn=AU.copy_mesh_from_skeletal_mesh if body else AU.copy_mesh_from_static_mesh
    success(fn(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0)),'Read source')
    return dm

dirty=set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('PIE active; geometry prepared, no asset writes')
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(ROOT) for p in dirty):raise RuntimeError('Unsaved revision assets')
for key,row in META.items():
    path=row['path'].split('.')[0]
    if path in dirty:raise RuntimeError('Unsaved target '+path)
    expected=receipt['saved'].get(path,{}).get('sha256',row['sha256'])
    if sha(disk(path))!=expected:raise RuntimeError('Concurrent asset edit '+path)
    if path not in receipt['saved']:
        ob=load(path);slots=ob.materials if key=='Body' else ob.static_materials
        if [str(s.material_slot_name) for s in slots]!=row['slots'] or [s.material_interface.get_path_name() for s in slots]!=row['materials']:
            raise RuntimeError('Current material bindings changed '+key)
        backup=O/'Before'/(path.removeprefix('/Game/')+'.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(disk(path),backup)

# Duplicate the live finish instances, retaining their shared master/weather path.
# Newly built surfaces use physical-scale micro normals instead of the Meshy atlas.
body=META['Body'];mapping={
 'M_A762_R08_Receiver':body['materials'][body['slots'].index('M_A762_Receiver')],
 'M_A762_R08_Mechanism':body['materials'][body['slots'].index('M_A762_Bolt')],
 'M_A762_FactoryRearGrip_Clean08':body['materials'][body['slots'].index('M_A762_FactoryRearGrip')]}
for key,row in META.items():
    if key!='Body':mapping['A762_'+key+'_Body08']=row['materials'][row['slots'].index('A762_'+key+'_0')]
mapping['A762_phantom_reargrip_Neck08']=META['phantom_reargrip']['materials'][1]
newmat={}
for slot,source in mapping.items():
    path=ROOT+'/Materials/MI_'+slot.removeprefix('M_')
    if source.split('.')[0] in dirty:raise RuntimeError('Unsaved finish input '+source)
    if slot in receipt['materials']:mi=load(path)
    else:
        if E.does_asset_exist(path):raise RuntimeError('Unowned material '+path)
        mi=A.duplicate_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],load(source))
        preset=mi.get_editor_property('parent').get_name()
        family='Rubber' if preset.endswith('Rubber') else 'Polymer' if 'Polymer' in preset else 'Metal'
        for name,value in {'SourceColorWeight':0.,'SourceRoughnessWeight':0.,'MaskUVChannel':0.,'BeadScale':6.99,'EdgeWear':0.,'EdgeHighlight':0.,'CavityDarken':0.,'CavityRoughness':0.}.items():
            L.set_material_instance_scalar_parameter_value(mi,name,value)
        for name,texture in {'SourceBaseColor':'/Game/Weapons/WeaponSurface/Textures/T_WS_White',
                'SourceRoughness':'/Game/Weapons/WeaponSurface/Textures/T_WS_GreyLinear',
                'SurfaceMask':'/Game/Weapons/WeaponSurface/Textures/T_WS_MaskNeutral',
                'SurfaceNormal':'/Game/Weapons/A762/SurfaceStandard08/Refine06/Textures/T_A762_R06_'+family+'_N'}.items():
            L.set_material_instance_texture_parameter_value(mi,name,load(texture))
        L.update_material_instance(mi);E.set_metadata_tag(mi,'A762DetailRevision',VERSION);save(mi)
        receipt['materials'][slot]={'path':path,'source':source,'family':family,'parent':mi.get_editor_property('parent').get_path_name(),'base':mi.get_base_material().get_path_name()};record()
    newmat[slot]=mi

def append_part(dm,part,slotindex,donors):
    with (O/'Exports'/(part['name']+'.bin')).open('rb') as f:
        head=json.loads(f.readline());nv,nt=head['vertices'],head['triangles']
        def read(code,count):
            a=array.array(code);a.fromfile(f,count);return a
        pos=read('f',nv*3);tri=read('i',nt*3);ns=read('f',nt*9);uvs=[read('f',nt*6) for _ in range(head['uv_sets'])]
    vertices=ids(ED.add_vertices_to_mesh,dm,LU.convert_array_to_vector_list([u.Vector(*pos[3*i:3*i+3]) for i in range(nv)]),True)
    if head['bone']:
        donor=donors[head['bone']]
        for vid in vertices:BW.set_vertex_bone_weights(dm,vid,donor)
    triangles=ids(ED.add_triangles_to_mesh,dm,LU.convert_array_to_triangle_list([u.IntVector(*(vertices[j] for j in tri[3*i:3*i+3])) for i in range(nt)]),0,True)
    if len(triangles)!=nt or any(t<0 for t in triangles):raise RuntimeError('Append failed '+part['name'])
    for i,tid in enumerate(triangles):
        MATS.set_triangle_material_id(dm,tid,slotindex,True)
        for channel,values in enumerate(uvs):
            tex=u.GeometryScriptUVTriangle();base=i*6
            tex.uv0=u.Vector2D(*values[base:base+2]);tex.uv1=u.Vector2D(*values[base+2:base+4]);tex.uv2=u.Vector2D(*values[base+4:base+6])
            UVS.set_mesh_triangle_u_vs(dm,channel,tid,tex,True)
        normal=u.GeometryScriptTriangle();base=i*9
        normal.vector0=u.Vector(*ns[base:base+3]);normal.vector1=u.Vector(*ns[base+3:base+6]);normal.vector2=u.Vector(*ns[base+6:base+9])
        NRM.set_mesh_triangle_normals(dm,tid,normal,True)

for key,row in META.items():
    target=row['path'].split('.')[0]
    if target in receipt['saved']:continue
    body=key=='Body';mesh=load(target);dm=read_mesh(mesh,body)
    if Q.get_has_vertex_id_gaps(dm) or Q.get_has_triangle_id_gaps(dm):raise RuntimeError('Input IDs changed '+key)
    if dm.get_triangle_count()!=row['triangles']:raise RuntimeError('Input topology changed '+key)
    parts=[p for p in PLAN['parts'] if p['target']==key]
    names=list(row['slots']);materials=[load(s) for s in row['materials']]
    for part in parts:
        if part['slot'] not in names:names.append(part['slot']);materials.append(newmat[part['slot']])
    donors={}
    if body:
        bi={b.index:str(b.name) for b in next(x for x in BW.get_all_bones_info(dm) if isinstance(x,(list,u.Array)))}
        data=json.loads((O/'Input/Body_bones.json').read_text())
        for name in {p['bone'] for p in parts}:
            index=data['bones'].index(name);vid=data['dominant'].index(index);donors[name]=[w for w in weights(dm,vid) if w.weight>1e-7]
            if len(donors[name])!=1 or bi[donors[name][0].bone_index]!=name:raise RuntimeError('Rigid bone donor changed '+name)
    doomed=PLAN['Body']['delete_triangles'] if body else ids(Q.get_all_triangle_i_ds,dm)
    ED.delete_triangles_from_mesh(dm,LU.convert_array_to_index_list(doomed),True)
    for part in parts:append_part(dm,part,names.index(part['slot']),donors)
    expected=row['triangles']-len(doomed)+sum(p['triangles'] for p in parts)
    if dm.get_triangle_count()!=expected:raise RuntimeError('Production face count mismatch '+key)
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,new_material_slot_names=names,
        enable_recompute_normals=False,enable_recompute_tangents=True,enable_remove_degenerates=False,use_original_vertex_order=True)
    write=AU.copy_mesh_to_skeletal_mesh if body else AU.copy_mesh_to_static_mesh
    candidate=ROOT+'/Meshes/'+target.rsplit('/',1)[1]+'_R08'
    if E.does_asset_exist(candidate):
        if candidate not in receipt['saved']:raise RuntimeError('Unowned candidate '+candidate)
        candidate_mesh=load(candidate)
    else:candidate_mesh=A.duplicate_asset(candidate.rsplit('/',1)[1],candidate.rsplit('/',1)[0],mesh)
    for path,asset in [(candidate,candidate_mesh),(target,mesh)]:
        success(write(dm,asset,opts,u.GeometryScriptMeshWriteLOD(lod_index=0)),'Save source geometry '+key)
        stored=read_mesh(asset,body)
        if stored.get_triangle_count()!=expected or Q.get_num_uv_sets(stored)!=row['uv_sets']:
            raise RuntimeError('Stored source mesh differs from authored mesh '+key)
        E.set_metadata_tag(asset,'A762DetailRevision',VERSION)
        E.set_metadata_tag(asset,'A762DetailSource','SourceAssets/A762ReceiverGrip20261001/README.md')
        if not body:
            source=O/'Exports'/('SM_A762_'+key+'_R08.fbx')
            if source.exists():asset.get_editor_property('asset_import_data').scripted_add_filename(str(source),0,'ReceiverGrip08 continuous grip')
        save(asset)
        receipt['saved'][path]={'sha256':sha(disk(path)),'triangles':expected,'slots':names,'materials':[m.get_path_name() for m in materials],
            'uv_sets':Q.get_num_uv_sets(dm),'added':sum(p['triangles'] for p in parts),'removed':len(doomed)};record()
        print('A762_SURFACE_DETAIL_SAVED',key,path,expected,flush=True)
receipt['complete']=all(row['path'].split('.')[0] in receipt['saved'] for row in META.values());record()
print('A762_SURFACE_DETAIL_COMPLETE',receipt['complete'],flush=True)
