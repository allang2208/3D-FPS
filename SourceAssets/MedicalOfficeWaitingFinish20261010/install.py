"""Save the local rail/tile repair and reuse the ward waiting benches. No game run."""
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
 for kind in ('Trim','Tiles'):preserve(PROJECT/('Content/Dungeons/MedicalOfficeWing20261010/Meshes/SM_MedicalOffice_'+kind+'.uasset'))
 bench=u.load_asset(R['BENCH'])
 if not bench:raise RuntimeError('Ward bench asset unavailable '+R['BENCH'])
 runpy.run_path(str(OFFICE/'import_assets.py'),init_globals={'GEOMETRY_ONLY':True,'IMPORT_KINDS':{'Trim','Tiles'}})
 report['stage']='assets_saved';record()
 world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
 gen=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
 raw=gen.get_editor_property('module_catalog_json');(backup/'production-before.json').write_text(raw,encoding='utf8')
 catalog=json.loads(raw);office=next(m for m in catalog['modules'] if m['id']=='MedicalDoctorOffice')
 changes=R['apply'](office);catalog['facility_flow']['medical_waiting_revision']=R['REVISION']
 bank=catalog['facility_flow']['layout_bank'];bank['contract_sha1']=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash'](catalog)
 assets={a.get_path_name():a for a in gen.get_editor_property('module_assets') if a};assets[bench.get_path_name()]=bench
 gen.modify();gen.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));gen.set_editor_property('module_assets',list(assets.values()))
 save(world,TARGET);report['maps'].append(dict(path=TARGET,saved=True,benches=len(changes)));record()
 write(FLOW/'Config/catalog.json',catalog);write(FLOW/'Config/layout-bank-v1.json',bank)
 write(OFFICE/'Config/module.json',office);write(OFFICE/'Config/layout-bank.json',bank)
 pending=copy.deepcopy(catalog);pending['facility_flow'].pop('layout_bank',None);write(OFFICE/'Config/catalog-pending.json',pending)
 sources=read(LINE/'Config/source-modules.json');sources['modules']=[office if m['id']==office['id'] else m for m in sources['modules']];write(LINE/'Config/source-modules.json',sources)
 for target,prefix in SUBJECTS:
  world=u.EditorLoadingAndSavingUtils.load_map(target)
  actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor)}
  for part in changes:
   a=actors[prefix+'_'+part['id']];a.modify();c=a.static_mesh_component;c.modify()
   a.set_actor_location(u.Vector(*part['position']),False,True);a.set_actor_rotation(u.Rotator(pitch=0,yaw=part['yaw'],roll=0),True);a.set_actor_scale3d(u.Vector(1,1,1))
   c.set_editor_property('override_materials',[]);c.set_static_mesh(bench);c.set_collision_profile_name('BlockAll');c.set_cast_shadow(True)
  save(world,target);report['maps'].append(dict(path=target,saved=True,benches=len(changes)));record()
 report.update(stage='maps_saved',reimported_meshes=['SM_MedicalOffice_Trim','SM_MedicalOffice_Tiles'],
  reused_bench=R['BENCH'],retained_previous_bench=R['RETAINED'],layout_entries_preserved=len(bank['entries']),
  rail_profile=read(OFFICE/'Config/geometry.json')['mid_rail'])
 record();print('MEDICAL_WAITING_FINISH_SAVED',len(report['maps']),'maps; old bench asset retained',flush=True)
except Exception:
 report.update(stage='incomplete',error=traceback.format_exc());record();raise
finally:
 if prior and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(prior)
