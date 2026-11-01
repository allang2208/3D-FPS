import unreal as u,json,ast,copy,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;tree=ast.parse((O.parent/'M24SprintSupport20261028/install.py').read_text());exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
patch=json.loads((O/'profile_patch.json').read_text());expected=json.loads((O/'ue_before.json').read_text())['profiles'];names={'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'};prepared={}
for family,name in names.items():
    path='/Game/Weapons/M24/MotionPolish20261027/'+name
    if any(p.get_name()==path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved target profile retained: '+path)
    asset=u.load_asset(path);live=packed(asset,family);new=copy.deepcopy(live)
    for clip_path in patch['modified'][family]:
        old=next((c for c in live['clips'] if c['base']==clip_path),None);prior=next((c for c in expected[family] if c['base']==clip_path),None)
        if old!=prior:raise RuntimeError('Concurrent target clip change retained: '+clip_path)
        replacement=next(c for c in patch['profiles'][family] if c['base']==clip_path)
        target=next((c for c in new['clips'] if c['base']==clip_path),None)
        if target is None:new['clips'].append(replacement)
        else:target.update(replacement)
    prepared[family]=(asset,new)
receipt={'complete':False,'saved':[],'runtime_tested':False,'native_build_required':False,'scope':'V9 left held-pose correction in two live profiles; contact-aware release and return'}
after={}
for family,(asset,spec) in prepared.items():
    if not asset.set_shared_clips_from_json(json.dumps(spec)):raise RuntimeError('Profile update failed')
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Profile save failed')
    after[family]=packed(asset,family)['clips'];file=Path(u.Paths.project_content_dir())/('Weapons/M24/MotionPolish20261027/'+names[family]+'.uasset')
    receipt['saved'].append({'path':asset.get_path_name(),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'roles':len(patch['modified'][family])})
receipt['complete']=True;(O/'profiles_after.json').write_text(json.dumps(after));(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2));print('M24_IDLE_ARM_SAVED',json.dumps(receipt),flush=True)
