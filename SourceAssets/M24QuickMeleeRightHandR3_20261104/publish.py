"""Save right-hand R3 over current advanced-stock quick-melee entries."""
import unreal as u,json,gzip,ast,hashlib,shutil
from pathlib import Path
O=Path(__file__).resolve().parent
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'profile serializer','exec'))
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; profiles retained')
assets=json.loads((O/'input_assets.json').read_text());expected=json.load(gzip.open(O/'input_motion.json.gz','rt'))['profiles']
patch=json.load(gzip.open(O/'quick_melee_patch.json.gz','rt'))
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def disk(path):return Path(u.Paths.project_content_dir())/(path[6:].split('.')[0]+'.uasset')
def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
for path,digest in json.loads((O/'input_dependency_hashes.json').read_text()).items():
    if path.split('.')[0] in dirty or sha(disk(path))!=digest:raise RuntimeError('Changed authoring dependency retained '+path)
for value in json.loads((O/'assembly.json').read_text()).values():
    if value['path'] in dirty or sha(disk(value['path']))!=value['sha256']:raise RuntimeError('Changed assembly retained '+value['path'])
class InputRoles:
    def __init__(self,asset):self.asset=asset
    def get_editor_property(self,key):
        return [c for c in self.asset.get_editor_property('clips') if c.get_editor_property('base').get_name() in ('A_M24_idle','A_M24_quick_melee')]
live={};hashes={}
for family,info in assets.items():
    path=info['path']
    if path in dirty:raise RuntimeError('Unsaved profile retained '+path)
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing profile '+path)
    if packed(InputRoles(asset),family)!=expected[family]:raise RuntimeError('Concurrent idle/quick-melee edit retained '+path)
    if family not in patch:continue
    if any(c.get_editor_property('retained') for c in asset.get_editor_property('clips')):raise RuntimeError('Retained animation requires separate publication '+path)
    live[family]=asset;hashes[family]=sha(disk(path))
backup=O/'BeforePublish';backup.mkdir(exist_ok=True)
for family in live:
    src=disk(assets[family]['path']);dest=backup/src.name
    if dest.exists():raise RuntimeError('Existing backup retained; publication is not replayed')
    shutil.copy2(src,dest)
R={'complete':False,'saved':[],'role':'quick_melee','duration':.9,'contact':.25,'scope':'Right chain and fingers only over current R2; left arm and weapon tracks retained','factory_profiles_changed':False,'runtime_tested':False,'focused_preview_rendered':True,'native_build_required':False,'patch_sha256':sha(O/'quick_melee_patch.json.gz')}
def record():(O/'publish_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
record();saved={}
for family,asset in live.items():
    file=disk(assets[family]['path'])
    if sha(file)!=hashes[family]:raise RuntimeError('Concurrent profile publication retained '+family)
    current=packed(asset,family)
    for i,clip in enumerate(current['clips']):
        if clip['base']==patch[family]['base']:current['clips'][i]=patch[family];break
    else:raise RuntimeError('Quick-melee role missing '+family)
    if not asset.set_shared_clips_from_json(json.dumps(current,separators=(',',':'))):raise RuntimeError('Profile conversion failed '+family)
    del current
    u.EditorAssetLibrary.set_metadata_tag(asset,'M24QuickMeleeAuthor','M24QuickMeleeRightHandR3_20261104: natural thumb, native right hinge and actual-skin regrip clearance; factory R2 gun path retained; 0.9s contact .25s')
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Profile save failed '+family)
    saved[family]=packed(InputRoles(asset),family)
    R['saved'].append({'family':family,'asset':asset.get_path_name(),'sha256':sha(file),'tracks':len(patch[family]['tracks'])});record()
    print('M24_FACTORY_REGRIP_SAVED',family,flush=True)
with gzip.open(O/'saved_motion.json.gz','wt',compresslevel=1) as fp:json.dump(saved,fp,separators=(',',':'))
R['complete']=True;record();print('M24_FACTORY_REGRIP_PUBLISH_COMPLETE',len(R['saved']),flush=True)
