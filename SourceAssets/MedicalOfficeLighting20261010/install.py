"""Save office-only downlights and exposure in production and the two retained scenes."""
import copy,json,runpy,shutil,traceback
from datetime import datetime
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
OFFICE=PROJECT/'SourceAssets/MedicalOfficeWing20261010';FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007'
LINE=PROJECT/'SourceAssets/DungeonHospitalLine20261003';TARGET='/Game/GameMaps/L_Dungeon_Randomized'
SUBJECTS=[('/Game/GameMaps/Design/L_MedicalDoctorOffice_Subject','MedicalOffice'),('/Game/GameMaps/Design/L_Hospital_Theme_Subject','HospitalLine_Office')]
read=lambda p:json.loads(p.read_text('utf-8-sig'))
R=runpy.run_path(str(ROOT/'recipe.py'))
W=runpy.run_path(str(PROJECT/'SourceAssets/DungeonFixtureLighting20261009/world_lights.py'))
save=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionCoverage20261009/install.py'))['save']
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem) or u.new_object(u.UnrealEditorSubsystem)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
playing=editor.get_game_world();dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if playing or dirty:raise RuntimeError('Preserve editor state: '+json.dumps(dict(playing=bool(playing),world=str(playing),dirty_maps=dirty)))
prior=editor.get_editor_world().get_path_name().split('.')[0] if editor.get_editor_world() else None
backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True)
report=dict(stage='preparing',revision=R['REVISION'],backup=str(backup),maps=[],tests_run=False,game_run=False,rendered=False)
def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def preserve(path):
 if path.exists():
  dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
def write(path,value):
 preserve(path);path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf8')
try:
 for target in [TARGET]+[p for p,_ in SUBJECTS]:
  rel=target.removeprefix('/Game/');preserve(PROJECT/'Content'/(rel+'.umap'))
  for category in ('__ExternalActors__','__ExternalObjects__'):
   folder=PROJECT/'Content'/category/rel
   if folder.exists():
    for path in folder.rglob('*'):
     if path.is_file():preserve(path)
 world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
 gen=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
 raw=gen.get_editor_property('module_catalog_json');(backup/'production-before.json').write_text(raw,encoding='utf8')
 catalog=json.loads(raw);office=next(m for m in catalog['modules'] if m['id']=='MedicalDoctorOffice')
 R['apply'](office);catalog['facility_flow']['medical_lighting_revision']=R['REVISION']
 bank=catalog['facility_flow']['layout_bank'];bank['contract_sha1']=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash'](catalog)
 gen.modify();gen.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
 save(world,TARGET);report['maps'].append(dict(path=TARGET,saved=True,lights=len(office['lights'])));record()
 write(FLOW/'Config/catalog.json',catalog);write(FLOW/'Config/layout-bank-v1.json',bank)
 write(OFFICE/'Config/module.json',office);write(OFFICE/'Config/layout-bank.json',bank)
 pending=copy.deepcopy(catalog);pending['facility_flow'].pop('layout_bank',None);write(OFFICE/'Config/catalog-pending.json',pending)
 sources=read(LINE/'Config/source-modules.json');sources['modules']=[office if m['id']==office['id'] else m for m in sources['modules']];write(LINE/'Config/source-modules.json',sources)
 for target,prefix in SUBJECTS:
  world=u.EditorLoadingAndSavingUtils.load_map(target)
  actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
  for i,spec in enumerate(office['lights']):
   actor=W['apply'](world,actors[prefix+'_Light'+str(i)],dict(fields=spec))
   R['set_light'](actor.get_component_by_class(u.RectLightComponent),spec)
  exposure=actors[prefix+'_Exposure'];exposure.modify();component=exposure.get_component_by_class(u.PostProcessComponent);component.modify()
  R['set_exposure'](component,next(s for s in office['runtime_actors'] if s['type']=='post_process'))
  save(world,target);report['maps'].append(dict(path=target,saved=True,lights=len(office['lights']),local_exposure_saved=True));record()
 report.update(stage='maps_saved',light_type='rect',direct_scale_after_conversion=R['DIRECT_SCALE'],
  corridor_lumens=99.,room_lumens=126.5,exposure_ev=1.2,exposure_bias=-.35,layout_entries_preserved=len(bank['entries']))
 record();print('MEDICAL_OFFICE_LIGHTING_SAVED',len(report['maps']),'maps',flush=True)
except Exception:
 report.update(stage='incomplete',error=traceback.format_exc());record();raise
finally:
 if prior and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(prior)
