"""Save stable local-front grip curves into the active M24 profiles."""
import unreal as u,json,gzip,ast,hashlib,shutil,copy
from pathlib import Path
O=Path(__file__).resolve().parent
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'profile serializer','exec'))
inputs=json.loads((O/'input_assets.json').read_text())
paths={family:a['path'] for family,a in inputs.items()}
for path,expected_hash in json.loads((O/'input_clip_hashes.json').read_text()).items():
    file=Path(u.Paths.project_content_dir())/(path[6:].split('.')[0]+'.uasset')
    if hashlib.sha256(file.read_bytes()).hexdigest()!=expected_hash:raise RuntimeError('Concurrent base animation change preserved: '+path)
recipe=json.loads((O/'authoring.json').read_text())
if hashlib.sha256((O/'candidate_profiles.json.gz').read_bytes()).hexdigest()!=recipe['candidate_sha256']:raise RuntimeError('Authoring output changed')
patch=json.load(gzip.open(O/'reload_patch.json.gz','rt'));expected=json.load(gzip.open(O/'expected_profiles.json.gz','rt'))
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; assets preserved')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
owned=set(recipe['owned_bones'])
live={};before={};after={}
R={'complete':False,'saved':[],'reload_clips':0,'scope':recipe['scope'],'runtime_tested':False,'offline_surface_review':False,'offline_preview_rendered':False,'candidate_sha256':recipe['candidate_sha256']}
def record():(O/'publish_receipt.json').write_text(json.dumps(R,indent=2))
for family,path in paths.items():
    if path in dirty:raise RuntimeError('Unsaved profile preserved '+path)
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing profile '+path)
    if any(c.get_editor_property('retained') for c in a.get_editor_property('clips')):raise RuntimeError('Retained clips preserved '+path)
    live[family]=a;before[family]=packed(a,str(a.get_editor_property('family')));after[family]=copy.deepcopy(before[family])
    for change,old in zip(patch[family],expected[family]):
        dst=next(c for c in after[family]['clips'] if c['base']==change['base'])
        if dst['duration']!=old['duration'] or change['duration']!=dst['duration']:raise RuntimeError('Concurrent clock change preserved '+family)
        a_tracks={t['bone']:t for t in dst['tracks']};b_tracks={t['bone']:t for t in old['tracks']}
        relevant={n for n in set(a_tracks)|set(b_tracks) if not n.endswith('_r')}
        if any(a_tracks.get(n)!=b_tracks.get(n) for n in relevant):raise RuntimeError('Concurrent source pose change preserved '+family)
        replacements={t['bone']:t for t in change['tracks']}
        if set(replacements)!=owned:raise RuntimeError('Patch contains unowned bones')
        dst['tracks']=[replacements.pop(t['bone'],t) for t in dst['tracks']]+list(replacements.values())
        R['reload_clips']+=1
backup=O/'BeforePublish';backup.mkdir(exist_ok=True)
for family,path in paths.items():
    file=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset');dest=backup/file.name
    if dest.exists():raise RuntimeError('Existing backup preserved; do not replay publication')
    shutil.copy2(file,dest)
with gzip.open(O/'live_before_publish.json.gz','wt',compresslevel=1) as f:json.dump(before,f,separators=(',',':'))
record()
saved={}
for family,a in live.items():
    if not a.set_shared_clips_from_json(json.dumps(after[family])):raise RuntimeError('Profile conversion failed '+family)
    if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Profile save failed '+family)
    saved[family]=packed(a,str(a.get_editor_property('family')))
    R['saved'].append({'family':family,'asset':a.get_path_name()});record()
    print('M24_LOCAL_GRIP_SAVED',family,flush=True)
with gzip.open(O/'saved_profiles.json.gz','wt',compresslevel=1) as f:json.dump(saved,f,separators=(',',':'))
R['complete']=True;record();print('M24_LOCAL_GRIP_COMPLETE',len(R['saved']),R['reload_clips'],flush=True)
