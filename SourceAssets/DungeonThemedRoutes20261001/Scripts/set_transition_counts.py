"""Save the requested 1-2 facility rooms on each side of every themed core."""
import hashlib,json,shutil
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:raise RuntimeError('Production map unavailable')
generators=[a for a in u.ObjectIterator(u.AuthoredDungeonGenerator) if a.get_path_name().startswith(TARGET+'.')]
if len(generators)!=1:raise RuntimeError('Production generator unavailable')
g=generators[0];before=g.get_editor_property('module_catalog_json');catalog=json.loads(before)
old=catalog['themed_routes']['before_after_transition_count'][:]
catalog['themed_routes']['before_after_transition_count']=[1,2]
source=PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap'
digest=hashlib.sha256(source.read_bytes()).hexdigest()
backup=ROOT/'Backup'/('L_Dungeon_Randomized-before-transition-counts-'+digest[:12]+'.umap')
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(source,backup)
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Transition counts not saved')
receipt=ROOT/'Receipts/install.json';data=json.loads(receipt.read_text('utf-8'))
data['routes']['before_after_transition_count']=[1,2]
receipt.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Receipts/transition-counts.json').write_text(json.dumps(dict(stage='map_saved',map=TARGET,
    before=old,after=[1,2],prior_map_sha256=digest,backup=str(backup),
    tests_run=False,generation_executed=False,editor_started=False),indent=2),encoding='utf-8')
print('THEMED_TRANSITION_COUNTS_SAVED [1, 2]',flush=True)
