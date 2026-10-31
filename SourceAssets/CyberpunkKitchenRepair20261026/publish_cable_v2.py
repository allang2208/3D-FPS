"""Scoped cable publication only. Uses the existing background mutex runner."""
from pathlib import Path
from datetime import datetime
import unreal as u,runpy,json,shutil,hashlib
R=Path(__file__).resolve().parent;P=R.parents[1];MAP='/Game/GameMaps/L_CyberpunkApartment'
H=runpy.run_path(str(R/'install_level.py'))
# Capture the currently saved contact geometry before replacing the local copy.
contact=runpy.run_path(str(R/'read_cable_contact.py'))
H['assets']()
w=contact['w']
if not w or w.get_path_name()!=MAP+'.L_CyberpunkApartment':raise RuntimeError('Unexpected world')
backup=R/'Backups'/datetime.now().strftime('cables-%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
path=P/'Content/GameMaps/L_CyberpunkApartment.umap';shutil.copy2(path,backup/path.name)
actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
result=runpy.run_path(str(R/'cable_route.py'))['apply'](w,actors,H)
if not u.EditorLoadingAndSavingUtils.save_map(w,MAP):raise RuntimeError('Cable map save failed')
result.update(stage='map_saved',map=MAP,backup=str(backup/path.name),saved_at=datetime.now().astimezone().isoformat(),map_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(R/'cable_v2_installed.json').write_text(json.dumps(result,indent=2),encoding='utf8')
prior=json.loads((R/'installed.json').read_text(encoding='utf8'));prior['cable_refinement']=result
prior['cables']=result['cables'];prior['updated']=list(dict.fromkeys(prior['updated']+['KP_Counter','KR_CoffeeEdgeBend','KR_Cable_CoffeeCounter']))
prior.update(map_sha256=result['map_sha256'],saved_at=result['saved_at'])
(R/'installed.json').write_text(json.dumps(prior,indent=2),encoding='utf8')
print('KITCHEN_CABLE_V2_SAVED',len(result['cables']))
