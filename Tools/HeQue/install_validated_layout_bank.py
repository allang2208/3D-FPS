"""Refresh only the proven bank signature in the current saved dungeon."""
import copy
import hashlib
import json
import runpy
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

project=Path('D:/FPS3D/FPSGAME')
root=project/'SourceAssets/HeQueBoss20261014/DungeonE2E/Records'
target='/Game/GameMaps/L_Dungeon_Randomized'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
proof=read(root/'layout-bank-independent.json')
native=read(project/'Saved/DungeonRoutingFix20260927/heque-current-bank-120-20261015.json')
if proof['total']!=120 or proof['passed']!=120 or proof['pairings']!=120 or len(native)!=120 or not all(r['success'] for r in native):
    raise RuntimeError('Current-catalog bank verification is incomplete')
expected=read(root/'catalog-before.json')
bank=read(root/'layout-bank-candidate.json')
if bank['entries']!=expected['facility_flow']['layout_bank']['entries']:
    raise RuntimeError('Candidate placements changed; preserve map')
digest=runpy.run_path(str(project/'SourceAssets/DungeonFacilityFlow20261007/restore_entry_recipe.py'))['contract_hash']
if digest(expected)!=bank['contract_sha1'] or any(r['catalog_contract_sha1']!=bank['contract_sha1'] for r in native):
    raise RuntimeError('Proof belongs to another catalog')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
world=u.EditorLoadingAndSavingUtils.load_map(target)
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Expected one current generator')
generator=generators[0]
actual=json.loads(generator.get_editor_property('module_catalog_json'))
if actual!=expected:raise RuntimeError('Production map changed since verification; preserve it')
backup=root/('LayoutBankBackup-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir()
map_file=project/'Content/GameMaps/L_Dungeon_Randomized.umap'
shutil.copy2(map_file,backup/map_file.name)
external=project/'Content/__ExternalActors__/GameMaps/L_Dungeon_Randomized'
if external.exists():shutil.copytree(external,backup/'ExternalActors')
bank['native_replay_pending']=False
bank['revalidated_catalog_contract']=bank['contract_sha1']
actual['facility_flow']['layout_bank']=bank
generator.modify()
generator.set_editor_property('module_catalog_json',json.dumps(actual,ensure_ascii=False,separators=(',',':')))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Map save failed')
# External actors are part of this map; save only its modified packages.
packages=[p for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
          if p.get_path_name().startswith('/Game/__ExternalActors__/GameMaps/L_Dungeon_Randomized/')]
if packages and not u.EditorLoadingAndSavingUtils.save_packages(packages,True):raise RuntimeError('External generator package save failed')
(root/'catalog-installed.json').write_text(json.dumps(actual,ensure_ascii=False,separators=(',',':')),encoding='utf8')
receipt=dict(stage='map_saved',map=target,backup=str(backup),contract=bank['contract_sha1'],entries=120,
             changed='layout_bank signature only; authored placements and current catalog preserved',external_packages=[p.get_path_name() for p in packages])
(root/'layout-bank-install.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print('HEQUE_LAYOUT_BANK_SAVED '+json.dumps(receipt,ensure_ascii=False),flush=True)
