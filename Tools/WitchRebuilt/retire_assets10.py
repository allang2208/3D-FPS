"""Archive the retired variants' exclusive UE packages, preserving live dependencies."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME').resolve();out=root/'SourceAssets/WitchRebuilt20260921/Revision10'
archive=(root/'trash/witch-variants-20260922').resolve()
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=root/'FPSGAME.uproject':raise RuntimeError('Wrong editor project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; preserved')
ar=u.AssetRegistryHelpers.get_asset_registry()
options=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,
 include_searchable_names=False,include_soft_management_references=True,include_hard_management_references=True)
scopes=('/Game/Monsters/WitchMeshy/OriginalRobeV05','/Game/Monsters/WitchMeshy/SpellSupportV07','/Game/Monsters/WitchFoundation/Animations')
assets={}
for folder in scopes:
 for a in ar.get_assets_by_path(folder,recursive=True):
  p=str(a.package_name)
  if '/Materials/' not in p:assets[p]=a
refs={p:set(map(str,ar.get_referencers(p,options))) for p in assets}
# A package referenced by current content (including rebuild templates) stays.
keep={p for p in assets if refs[p]-assets.keys()}
while True:
 expanded=keep|{p for p in assets if refs[p]&keep}
 if expanded==keep:break
 keep=expanded
retired=sorted(assets.keys()-keep)
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty&set(retired):raise RuntimeError('Unsaved retired assets retained: '+str(sorted(dirty&set(retired))))
plan={'retire':retired,'keep':[{'package':p,'referencers':sorted(refs[p])} for p in sorted(keep)],
 'retained_source_templates':'WitchFoundation mesh/skeleton/physics/materials plus original Witch source art are rebuild inputs, not spawnable variants'}
(out/'asset_retirement_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
if not globals().get('WITCH_RETIRE_EXECUTE',False):
 print(json.dumps(plan))
else:
 rows=[]
 for package in retired:
  stem=(root/'Content'/package.removeprefix('/Game/')).resolve()
  for extension in ('.uasset','.uexp','.ubulk','.uptnl'):
   src=stem.with_suffix(extension)
   if not src.exists():continue
   dst=(archive/src.relative_to(root)).resolve()
   if not any(src.is_relative_to(root/'Content'/s.removeprefix('/Game/')) for s in scopes) or not dst.is_relative_to(archive):raise RuntimeError('Path outside retired scope')
   data=src.read_bytes();sha=hashlib.sha256(data).hexdigest()
   if dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest()!=sha:raise RuntimeError('Archive conflict; current package preserved')
   if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
   if hashlib.sha256(dst.read_bytes()).hexdigest()!=sha:raise RuntimeError('Archive copy differs; original preserved')
   rows.append({'package':package,'source':str(src.relative_to(root)),'destination':str(dst.relative_to(root)),
    'bytes':len(data),'sha256':sha,'reason':'User removed the old Witch and Foundation selectable variants; no retained package referencers',
    'replacement':'/Game/Monsters/WitchRebuilt and /Script/FPSGAME.WitchRebuiltMonster'})
 loaded=[u.load_asset(p) for p in retired]
 if any(a is None for a in loaded):raise RuntimeError('Could not load retired packages; archive copies retained')
 deleted=not loaded or u.EditorAssetLibrary.delete_loaded_assets(loaded)
 receipt=root/'Docs/AssetArchives/witch-variants-assets-20260922.json';receipt.parent.mkdir(exist_ok=True)
 previous=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else []
 saved={r['source']:r for r in previous}
 saved.update({r['source']:r for r in rows if not (root/r['source']).exists()})
 receipt.write_text(json.dumps(list(saved.values()),indent=2),encoding='utf-8')
 if not deleted or any((root/r['source']).exists() for r in rows):raise RuntimeError('Some packages were retained; consult archive receipt')
 result={'retired_packages':retired,'retained_dependencies':plan['keep'],'archive':str(archive),'runtime_tested':False}
 (out/'asset_retirement_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result))
