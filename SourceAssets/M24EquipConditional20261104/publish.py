"""Publish a short neutral equip and merge only the fitted shoulder tracks."""
from pathlib import Path
import unreal as u,json,gzip,hashlib,shutil,ast,gc
O=Path(__file__).resolve().parent;P=O.parents[1]
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(P/'Content').resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    lev=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if lev and lev.is_in_play_in_editor():raise RuntimeError('PIE active; preserve the live assets')
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'profile serializer','exec'))
D=json.load(gzip.open(O/'input_motion.json.gz','rt'));patch=json.load(gzip.open(O/'families.json.gz','rt'));paths=json.loads((O/'input_assets.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
READY='/Game/Weapons/M24/EquipConditional20261104/A_M24_equip_ready'
def disk(path):return P/'Content'/(path.split('.')[0][6:]+'.uasset')
def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for path,h in json.loads((O/'hashes.json').read_text()).items():
    if path.split('.')[0] in dirty or sha(disk(path))!=h:raise RuntimeError('Concurrent input change '+path)
if any(path in dirty for path in [READY]+[sp['path'] for sp in paths.values()]):raise RuntimeError('Dirty equip or profile asset')
rfile=O/'saved.json';token=sha(O/'families.json.gz')
R=json.loads(rfile.read_text()) if rfile.is_file() else {'complete':False,'recipe':token,'saved':{},'game_tested':False}
if R['recipe']!=token:raise RuntimeError('Different edit owns this receipt')
def record():
    tmp=rfile.with_suffix('.tmp');tmp.write_text(json.dumps(R,indent=2));tmp.replace(rfile)
def saved(path):
    if path not in R['saved']:return False
    if sha(disk(path))!=R['saved'][path]:raise RuntimeError('Published asset changed '+path)
    return True
def save(path,a):
    E.set_metadata_tag(a,'M24EquipConditional','20261104')
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+path)
    R['saved'][path]=sha(disk(path));record()
queue=[]
for family,p in paths.items():
    path=p['path']
    if saved(path):continue
    a=u.load_asset(path);cliprows=a.get_editor_property('clips')
    if any(c.get_editor_property('retained') for c in cliprows):raise RuntimeError('Alternate retained animation '+path)
    prior={c['base']:c for c in D['profiles'][family]['clips']}
    current=packed(a,str(a.get_editor_property('family')))
    for c in current['clips']:
        if c['base'].split('.')[0]==READY:raise RuntimeError('Occupied ready profile '+path)
        if c['base'] in prior and c!=prior[c['base']]:raise RuntimeError('Concurrent equip or idle change '+path)
    if not all(any(c['base']==key for c in current['clips']) for key in prior):raise RuntimeError('Missing source clip '+path)
    del current;queue.append((family,path,a,sha(disk(path))))
if not saved(READY):
    if E.does_asset_exist(READY):raise RuntimeError('Occupied ready animation '+READY)
    mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
    idle=next(v for k,v in D['clips'].items() if k.endswith('A_M24_idle'))
    bolt=next(v for k,v in D['clips'].items() if k.endswith('A_M24_equip'))
    source=u.load_asset(idle['path']);factory=u.AnimSequenceFactory();factory.target_skeleton=mesh.skeleton;factory.preview_skeletal_mesh=mesh
    a=A.create_asset('A_M24_equip_ready',READY.rsplit('/',1)[0],u.AnimSequence,factory)
    if not a:raise RuntimeError('Ready animation creation refused')
    a.set_preview_skeletal_mesh(mesh)
    a.set_editor_property('bone_compression_settings',source.get_editor_property('bone_compression_settings'))
    rate=u.FrameRate(numerator=30,denominator=1);a.get_editor_property('platform_target_frame_rate').set_editor_property('default',rate)
    ctrl=a.get_editor_property('controller') or u.AnimDataController()
    ctrl.set_model(a.get_editor_property('data_model_interface'))
    comp=u.new_object(u.SkeletalMeshComponent);comp.set_skeletal_mesh_asset(mesh)
    armature=str(comp.get_parent_bone('VM_Root'))
    names=list(D['names'])
    opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.SOURCE
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(source,0.,opts)
    if armature!='None' and armature not in names:names.insert(0,armature)
    ctrl.open_bracket('M24 ready draw with a closed bolt',False)
    try:
        ctrl.set_frame_rate(rate,False);ctrl.set_number_of_frames(u.FrameNumber(value=18),False)
        for n in names:
            if not ctrl.add_bone_curve(n,False):raise RuntimeError('Unable to add '+n)
            if n=='VM_Root':
                idx=D['names'].index(n);keys=[bolt['poses'][str(k)][idx] for k in range(19)]
                pos=[u.Vector(*v[:3]) for v in keys];rot=[u.Quat(*v[3:7]) for v in keys];sc=[u.Vector(*v[7:]) for v in keys]
            else:
                t=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)
                pos=[t.translation]*19;rot=[t.rotation]*19;sc=[t.scale3d]*19
            if not ctrl.set_bone_track_keys(n,pos,rot,sc,False):raise RuntimeError('Ready track failed '+n)
    finally:ctrl.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(a):raise RuntimeError('Ready animation compression failed')
    save(READY,a)
for family,path,a,h in queue:
    if sha(disk(path))!=h:raise RuntimeError('Concurrent write '+path)
    backup=O/'Before'/disk(path).name;backup.parent.mkdir(exist_ok=True)
    if backup.exists() and sha(backup)!=h:raise RuntimeError('Different source backup '+path)
    if not backup.exists():shutil.copy2(disk(path),backup)
    cur=packed(a,str(a.get_editor_property('family')));take=patch[family]
    if 'equip' in take:
        clip=next(c for c in cur['clips'] if c['base'].endswith('.A_M24_equip'));rep={t['bone']:t for t in take['equip']}
        clip['tracks']=[rep.pop(t['bone'],t) for t in clip['tracks']];clip['tracks'].extend(rep.values())
    cur['clips'].append(take['equip_ready'])
    if not a.set_shared_clips_from_json(json.dumps(cur,separators=(',',':'))):raise RuntimeError('Grip merge failed '+family)
    save(path,a);del cur;gc.collect()
R['complete']=True;R['ready_duration']=.6;R['conditional_duration']=58/30.;record()
print('M24_CONDITIONAL_EQUIP_SAVED',len(R['saved']),flush=True)
