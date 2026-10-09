"""Install the audited joint solver and exact-pair fallback bank; no generation."""
import copy
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
TARGET = '/Game/GameMaps/L_Dungeon_Randomized'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def contract(catalog):
    result = copy.deepcopy(catalog)
    for key in ('layout_bank', 'probe_pair_order', 'joint_layout_version'):
        result['facility_flow'].pop(key, None)
    return result


if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Preserve unsaved maps')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('Preserve active PIE')
bank = read(ROOT/'Config/layout-bank-v1.json')
if len(bank['entries']) != 120:
    raise RuntimeError('All 120 pairings must be covered before activation')
for label, minimum in [('joint-bank-all120-audit-20261008',120), ('joint-final-64seeds-audit-20261008',64)]:
    proof = read(ROOT/f'Receipts/{label}.json')
    if minimum == 120 and proof.get('ordered_pairing_coverage') != 120:
        raise RuntimeError('Exhaustive ordered-pair coverage missing')
    if proof['unique_seeds'] < minimum or proof['failed_unique'] or any(not x['passed'] for x in proof['results']):
        raise RuntimeError(f'Incomplete layout acceptance: {label}')
world = u.EditorLoadingAndSavingUtils.load_map(TARGET)
generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
if len(generators) != 1:
    raise RuntimeError('Expected one production generator')
generator = generators[0]
before = generator.get_editor_property('module_catalog_json')
catalog = json.loads(before)
expected = read(ROOT/'Receipts/joint-bank-contract-20261008-catalog.json')
if contract(catalog) != contract(expected):
    raise RuntimeError('Production catalog changed after layout tests; preserve current map')
package = PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap'
digest = hashlib.sha256(package.read_bytes()).hexdigest()
snapshot = ROOT/'Snapshots/JointLayout20261008'
snapshot.mkdir(parents=True,exist_ok=True)
backup = snapshot/f'L_Dungeon_Randomized-{digest[:12]}.umap'
if not backup.exists():
    shutil.copy2(package,backup)
(snapshot/f'catalog-{digest[:12]}.json').write_text(before,encoding='utf-8')
bank['native_replay_pending'] = False
catalog['facility_flow']['joint_layout_version'] = 1
catalog['facility_flow']['layout_bank'] = bank
generator.modify()
generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):
    raise RuntimeError('Production map save failed')
(ROOT/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
(ROOT/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
report = {'stage':'map_saved','map':TARGET,'backup_map':str(backup),'pairings':len(bank['entries']),
          'contract_sha1':bank['contract_sha1'],'generated':False,'game_run':False,'visual_tested':False,
          'map_sha256':hashlib.sha256(package.read_bytes()).hexdigest()}
(ROOT/'Receipts/joint-layout-save-20261008.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('FACILITY_JOINT_LAYOUT_SAVED '+TARGET)
