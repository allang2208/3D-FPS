"""Remove the ten published C6 packages for two Thor-only common seat adaptations."""
from pathlib import Path
import json,hashlib,shutil,datetime
import unreal as u
P=Path(__file__).resolve().parent;R=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
retired=('ancient_breaking_seal_seat','storm_drive_seat')
pub=json.loads((P/'publication_receipt.json').read_text(encoding='utf-8'))
if not pub['complete']:raise RuntimeError('Publish exclusions first')
module=json.loads((R/'Content/ColdSteelData/thunder-god-hammer-modules.json').read_text(encoding='utf-8-sig'))
if any(id in module['slots']['head_mount'] for id in retired):raise RuntimeError('Retired model still active')
root='/Game/Weapons/ThunderGodHammer20261028/SeatInlaidC6'
paths=[]
for id in retired:
 paths += [root+'/Meshes/SM_ThunderGodHammer_head_mount_'+id,root+'/M_ThorSeatC6_'+id]
 paths += [root+'/Textures/T_ThorSeatC6_'+id+'_'+kind for kind in ('BaseColor','ORM','Normal')]
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths):raise RuntimeError('Preserving unsaved retired packages: '+str(dirty.intersection(paths)))
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([root],True)
for path in paths:
 refs=set(u.EditorAssetLibrary.find_package_referencers_for_asset(path,False))-set(paths)
 if refs:raise RuntimeError('Preserving externally referenced package '+path+': '+str(refs))
archive=R/'trash/thunder-seat-retired-20261031'/('Assets-'+datetime.datetime.now().strftime('%H%M%S'));archive.mkdir(parents=True)
content=(R/'Content').resolve();owned=(R/'Content/Weapons/ThunderGodHammer20261028/SeatInlaidC6').resolve()
receipt=dict(complete=False,scope='Thor-only SeatInlaidC6 adaptations',retired=list(retired),packages=paths,files=[],deleted=[],bytes=0,retained=['all CommonHammerSeats packages for other weapons','three normal Thor seat adaptations','historical versions outside SeatInlaidC6','shared icons'],runtime_tested=False)
def record():(P/'retirement_assets_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
for path in paths:
 base=content/path.removeprefix('/Game/')
 for suffix in ('.uasset','.uexp','.ubulk'):
  src=base.with_suffix(suffix).resolve()
  if not src.is_relative_to(owned):raise RuntimeError('Outside retirement boundary '+str(src))
  if not src.exists():continue
  dst=archive/src.relative_to(content);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
  digest=hashlib.sha256(src.read_bytes()).hexdigest()
  if hashlib.sha256(dst.read_bytes()).hexdigest()!=digest:raise RuntimeError('Archive copy incomplete '+str(src))
  receipt['files'].append(dict(source=str(src),archive=str(dst),bytes=src.stat().st_size,sha256=digest));receipt['bytes']+=src.stat().st_size
record()
for path in paths:
 if u.EditorAssetLibrary.does_asset_exist(path):
  if not u.EditorAssetLibrary.delete_asset(path):raise RuntimeError('Asset deletion failed '+path)
 receipt['deleted'].append(path);record()
receipt['complete']=True;record();print('THUNDER_TWO_COMMON_ADAPTATIONS_RETIRED '+str(receipt['bytes']))
