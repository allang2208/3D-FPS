"""Archive only unreferenced, unloaded M16 import failures through the editor."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parent.parent;T=P/'trash/m16-retired-20260920';E=u.EditorAssetLibrary
root='/Game/Weapons/M16A2/UniversalAttachments20260920/AuthoringRecovery';ar=u.AssetRegistryHelpers.get_asset_registry()
assets=ar.get_assets_by_path(root,recursive=True);byname={str(a.package_name):a for a in assets}
opts=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,include_searchable_names=False,include_soft_management_references=True,include_hard_management_references=True)
refs={p:set(map(str,ar.get_referencers(p,opts))) for p in byname}
keep={p for p,r in refs.items() if r-set(byname)}
while True:
 expanded=keep|{p for p,r in refs.items() if r&keep}
 if expanded==keep:break
 keep=expanded
retained=[]
for p in sorted(keep):
 external=sorted(refs[p]-set(byname));resolved=[]
 for ref in external:
  a=u.load_asset(ref);resolved.append({'reference':ref,'resolved_asset':a.get_path_name() if a else None,'class':a.get_class().get_name() if a else None})
 retained.append({'package':p,'referencers':sorted(refs[p]),'resolved':resolved})
(O/'retained-recovery-dependencies.json').write_text(json.dumps(retained,indent=2),encoding='utf-8')
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE to archive unused import packages; no packages removed.')
rows=[]
for p,a in byname.items():
 if p in keep:continue
 if a.is_asset_loaded():raise RuntimeError('Unused package became loaded; retained '+p)
 src=P/'Content'/(p.removeprefix('/Game/')+'.uasset');dst=T/src.relative_to(P)
 assert src.resolve().is_relative_to((P/'Content/Weapons/M16A2/UniversalAttachments20260920/AuthoringRecovery').resolve())
 assert dst.resolve().is_relative_to(T.resolve())
 sha=hashlib.sha256(src.read_bytes()).hexdigest();size=src.stat().st_size
 if dst.exists():raise RuntimeError('Archive target already exists '+str(dst))
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 assert dst.stat().st_size==size and hashlib.sha256(dst.read_bytes()).hexdigest()==sha
 if not E.delete_asset(p):raise RuntimeError('Editor could not remove archived package '+p)
 rows.append({'source':src.relative_to(P).as_posix(),'destination':dst.relative_to(P).as_posix(),'bytes':size,'sha256':sha,'reason':'unreferenced source-collision or incomplete import; active recovery dependencies retained','retained':'Content/Weapons/M16A2/UniversalAttachments20260920'})
 (O/'archive-assets.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('M16_IMPORT_FAILURES_ARCHIVED',len(rows),'RETAINED_DEPENDENCIES',len(keep))
