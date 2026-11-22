from pathlib import Path
import json,os,sys,shutil,hashlib
W=Path('F:/FPSGAMEData/ArtProduction/M249Orpind20261107/ApprovedRecovery20261121');R=Path('D:/FPS3D/FPSGAME')
try:import unreal as u
except ImportError:u=None
if u:
 assert Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()==R.resolve()
else:
 # Offline caller owns the shared gate and has established that the production editor is closed.
 assert '--offline' in sys.argv
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((W/'publish-plan.json').read_bytes())
previous=json.loads((W/'installed.json').read_bytes()) if (W/'installed.json').exists() else {}
pending={k:r for k,r in plan.items() if k not in previous}
protected={}
if u:
 dirty={x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
 opened_assets=u.get_editor_subsystem(u.AssetEditorSubsystem)
 opened={x.get_path_name().split('.')[0] for x in opened_assets.get_all_edited_assets()} if hasattr(opened_assets,'get_all_edited_assets') else set()
 for k,r in pending.items():
  pkg=r['package'];obj=u.find_object(None,pkg+'.'+pkg.rsplit('/',1)[-1])
  if obj or pkg in dirty or pkg in opened:protected[k]='dirty' if pkg in dirty else 'loaded'
if protected:
 (W/'protected.json').write_text(json.dumps(protected,indent=2));raise RuntimeError('Active M249 packages preserved: '+str(protected))
for rel,r in pending.items():
 p=R/rel;s=p.stat()
 if s.st_size!=r['original_size'] or s.st_mtime_ns!=r['original_mtime_ns'] or digest(p)!=r['baseline']:raise RuntimeError('Changed during production: '+rel)
updates={}
try:
 for rel,r in pending.items():
  p=R/rel;src=Path(r['stage_file']);assert src.is_file() and src.resolve().is_relative_to(W/'Pending')
  os.replace(src,p);updates[rel]=dict(stage=r['stage'],before=r['baseline'],after=r['target'])
 for rel,d in updates.items():
  if digest(R/rel)!=d['after']:raise RuntimeError('Package publication '+rel)
except BaseException:
 for rel,d in reversed(list(updates.items())):
  p=R/rel
  if digest(p)==d['after']:
   os.replace(p,Path(plan[rel]['stage_file']));shutil.copy2(W/'Before'/rel,p)
 raise
(W/'installed.json').write_text(json.dumps({**previous,**updates},indent=2))
print('M249_PACKAGES_PUBLISHED',len(updates),flush=True)
