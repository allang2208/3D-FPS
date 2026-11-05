"""Save the shared equip track and merge only its opening right-hand contacts."""
from pathlib import Path
import ast,hashlib,json,gzip,shutil,gc
import unreal as u
O=Path(__file__).resolve().parent;project=O.parents[1]
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(project/'Content').resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('PIE active; preserve current session')
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'live profile serializer','exec'))
draw=json.loads((O/'draw_keys.json').read_text());src=json.load(gzip.open(O/'grip_inputs.json.gz','rt'));fixes=json.load(gzip.open(O/'grip_patch.json.gz','rt'))
E=u.EditorAssetLibrary;eq=draw['asset']
def file(path):return project/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
rfile=O/'publish_receipt.json';token=[sha(O/'draw_keys.json'),sha(O/'grip_patch.json.gz')]
R=json.loads(rfile.read_text()) if rfile.is_file() else {'complete':False,'inputs':token,'saved':{},'runtime_tested':False}
if R['inputs']!=token:raise RuntimeError('Different production inputs')
def record():
    tmp=rfile.with_suffix('.tmp');tmp.write_text(json.dumps(R,indent=2));tmp.replace(rfile)
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def candidate(path):
    if path in dirty:raise RuntimeError('Unsaved edits preserved: '+path)
    if path in R['saved']:
        if sha(file(path))!=R['saved'][path]:raise RuntimeError('Published asset subsequently changed: '+path)
        return False
    return True
def backup(path):
    srcfile=file(path);dst=O/'Before'/srcfile.name;dst.parent.mkdir(exist_ok=True)
    if dst.exists():
        if sha(srcfile)!=sha(dst):raise RuntimeError('Conflicting backup '+path)
    else:shutil.copy2(srcfile,dst)
def save(path,a):
    E.set_metadata_tag(a,'M24EquipReference','BV1JK421y7Q5 02:52.53-02:53.20 / M24EquipReference20261104')
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+path)
    R['saved'][path]=sha(file(path));record()
needs_base=candidate(eq)
if needs_base and sha(file(eq))!=draw['source_sha256']:raise RuntimeError('Equip data changed')
for path,h in src['sha'].items():
    if path!=eq and (path in dirty or sha(file(path))!=h):raise RuntimeError('Pose dependency changed '+path)
to_write=[]
for family,path in src['paths'].items():
    if not candidate(path):continue
    asset=u.load_asset(path);clips=asset.get_editor_property('clips')
    if any(c.get_editor_property('retained') for c in clips):raise RuntimeError('Alternate retained clip '+path)
    for role,before in src['profiles'][family].items():
        c=next(c for c in clips if c.get_editor_property('base').get_name()=='A_M24_'+role)
        live={str(t.get_editor_property('bone')):{'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks') if str(t.get_editor_property('bone')) in src['parents']}
        if live!=before:raise RuntimeError('Concurrent '+role+' pose change: '+path)
    to_write.append((family,path,asset,sha(file(path))))
if needs_base:
    backup(eq);a=u.load_asset(eq);ctrl=a.get_editor_property('controller')
    if not ctrl:ctrl=u.AnimDataController();ctrl.set_model(a.get_editor_property('data_model_interface'))
    keys=draw['keys'];bone=draw['bone'];ctrl.open_bracket('M24 equip rise and settle',False)
    try:
        if not ctrl.set_bone_track_keys(bone,[u.Vector(*v[:3]) for v in keys],[u.Quat(*v[3:7]) for v in keys],[u.Vector(*v[7:10]) for v in keys],False):raise RuntimeError('Draw track refused')
    finally:ctrl.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(a):raise RuntimeError('Equip animation compression failed')
    save(eq,a)
for family,path,a,h in to_write:
    if sha(file(path))!=h:raise RuntimeError('Concurrent asset change '+path)
    backup(path);cur=packed(a,str(a.get_editor_property('family')))
    clip=next(c for c in cur['clips'] if c['base'].split('.')[0]==eq);replace=dict(fixes[family])
    clip['tracks']=[replace.pop(t['bone'],t) for t in clip['tracks']]
    clip['tracks'].extend(replace.values())
    if not a.set_shared_clips_from_json(json.dumps(cur,separators=(',',':'))):raise RuntimeError('Pose merge refused '+family)
    save(path,a);del cur;gc.collect()
R['complete']=True;R['base_seconds']=len(draw['keys'][1:])/draw['frame_rate']
R['draw_end_frame']=18;R['grip_release_blend_frames']=[6,15];R['pull_closed_frames']=[25,40];record()
print('M24_EQUIP_REFERENCE_SAVED',len(R['saved']),flush=True)
