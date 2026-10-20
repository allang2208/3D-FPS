"""Add native V9 right-hand correctives only; never rewrite base glove geometry."""
from pathlib import Path
import unreal as u,json,hashlib,shutil,math
O=Path(__file__).resolve().parent;P=Path(u.Paths.project_dir()).resolve();E=u.EditorAssetLibrary
d=json.loads((O/'glove-payload.json').read_text());path=d['path'];disk=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
digest=lambda:hashlib.sha256(disk.read_bytes()).hexdigest()
es=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if es and es.get_game_world():raise RuntimeError('Preserve active PIE')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty:raise RuntimeError('Preserve unsaved glove')
rp=O/'glove-install-receipt.json'
if rp.exists() and json.loads(rp.read_text()).get('sha256')==digest():
    print('GLOVE_CORRECTIVES_ALREADY_SAVED',flush=True)
else:
    if digest()!=d['sha256']:raise RuntimeError('Glove changed since production')
    backup=Path('D:/FPS3D/FPSGAME_Backups/SVCHQuickMeleeHandR3_20261019');backup.mkdir(exist_ok=True,parents=True)
    b=backup/('SVD_BlueMageGloves_'+digest()[:12]+'.uasset')
    if not b.exists():shutil.copy2(disk,b)
    asset=u.load_asset(path);G=u.GeometryScript_AssetUtils;N=u.GeometryScript_Normals;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List
    def copy():
        dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
        r=G.copy_mesh_from_skeletal_mesh(asset,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
        if u.GeometryScriptOutcomePins.SUCCESS not in r:raise RuntimeError('Cannot read glove')
        return dm
    def positions(dm):
        r=Q.get_all_vertex_positions(dm,False);v=next(x for x in r if isinstance(x,u.GeometryScriptVectorList));return L.convert_vector_list_to_array(v)
    original=positions(copy())
    if len(original)!=len(d['positions']):raise RuntimeError('Changed glove topology')
    err=max(max(abs(v.x-p[0]),abs(v.y-p[1]),abs(v.z-p[2])) for v,p in zip(original,d['positions']))
    if err>.0001:raise RuntimeError('Changed glove base surface')
    slots=[str(s.material_slot_name) for s in asset.get_editor_property('materials')]
    for index,(name,rows) in enumerate(d['morphs'].items()):
        dm=copy();r=N.get_mesh_per_vertex_normals(dm,True)
        ns=L.convert_vector_list_to_array(next(x for x in r if isinstance(x,u.GeometryScriptVectorList)))
        for vid,x,y,z,nx,ny,nz in rows:
            u.GeometryScript_MeshEdits.set_vertex_position(dm,vid,u.Vector(x,y,z),True)
            v=ns[vid];nn=(v.x+nx,v.y+ny,v.z+nz);length=max(1e-10,math.sqrt(sum(k*k for k in nn)))
            N.update_vertex_normal(dm,vid,True,u.Vector(*(k/length for k in nn)),False,u.Vector(1,0,0),u.Vector(0,1,0),False,True)
        opts=u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=True,emit_transaction=False,
            defer_mesh_post_edit_change=index<len(d['morphs'])-1,copy_normals=True)
        r=G.copy_morph_target_to_skeletal_mesh(dm,asset,name,opts,u.GeometryScriptMeshWriteLOD())
        if u.GeometryScriptOutcomePins.SUCCESS not in r:raise RuntimeError('Cannot add '+name)
        print('SVCH_GLOVE_CORRECTIVE',name,flush=True)
    E.set_metadata_tag(asset,'SVCHV9HandCorrectives','V9 right-hand fields; base mesh and binding preserved; 20261019 R3')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save glove')
    readback=positions(copy());err=max(max(abs(v.x-p[0]),abs(v.y-p[1]),abs(v.z-p[2])) for v,p in zip(readback,d['positions']))
    if err>.0001:raise RuntimeError('Unexpected base geometry change')
    if slots!=[str(s.material_slot_name) for s in asset.get_editor_property('materials')]:raise RuntimeError('Unexpected material change')
    installed=[m.get_name() for m in (asset.get_editor_property('morph_targets') or [])]
    if not set(d['morphs']).issubset(installed):raise RuntimeError('Missing saved glove correctives')
    rp.write_text(json.dumps({'complete':True,'path':path,'sha256':digest(),'backup':str(b),'morphs':installed,
        'base_position_error_cm':err,'V9_changed':False,'material_slots_unchanged':True},indent=2))
    print('SVCH_GLOVE_CORRECTIVES_SAVED',flush=True)
