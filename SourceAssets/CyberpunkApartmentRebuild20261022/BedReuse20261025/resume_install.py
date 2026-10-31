"""Finish this batch after the throw attachment API argument was corrected."""
from pathlib import Path
from datetime import datetime
import hashlib,json,runpy
import unreal as u
R=Path(__file__).resolve().parent
d=runpy.run_path(str(R/'install_level.py'))
MAP=d['MAP'];PROJECT=d['PROJECT']
s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if s.get_game_world():raise RuntimeError('Preserve current PIE')
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if set(dirty)!={MAP}:raise RuntimeError('Unexpected dirty package scope: '+str(dirty))
world=u.load_asset(MAP)
actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
for label in ('AP_Bed3_Bed','AP_Bed3_FootThrow'):
    if label not in actors or not actors[label].actor_has_tag(d['TAG']):
        raise RuntimeError('The unfinished batch is not present: '+label)
report=d['apply_upgrade'](world)
if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Apartment save failed')
source=json.loads((R/'source.json').read_text('utf8'))
before=next(r for r in source['beds'] if r['actor']=='AP_Bed3_Bed')
report['beds'][0]['previous_mesh']=before['mesh']
report['beds'][0]['foot_throw_created']=True
path=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap'
backup=sorted((R/'Backups').glob('*/L_CyberpunkApartment.umap'))[-1]
report.update(stage='formal_apartment_beds_saved',saved_at=datetime.now().astimezone().isoformat(),
              backup=str(backup),map_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
              new_editor_started=False,resumed_attachment_after_api_correction=True)
(R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('APARTMENT_BEDS_REUSED_AND_SAVED',len(report['beds']),report['saved_at'])
