"""Save scoped doorway mesh and leaf corrections; retain all route geometry/placements."""
import copy,json,runpy,shutil,traceback
from datetime import datetime
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007'
LINE=PROJECT/'SourceAssets/DungeonHospitalLine20261003'
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
SUBJECTS=['/Game/GameMaps/Design/L_MedicalDoctorOffice_Subject','/Game/GameMaps/Design/L_Hospital_Theme_Subject']
REVISION='medical_doorway_reveals_and_swing_20261010'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
save=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionCoverage20261009/install.py'))['save']
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem) or u.new_object(u.UnrealEditorSubsystem)
if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve play/unsaved maps')
prior=editor.get_editor_world().get_path_name().split('.')[0] if editor.get_editor_world() else None
backup=ROOT/'Backups'/('DoorwayInstall-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
def preserve(path):
 if path.exists():
  dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
def write(path,value):
 preserve(path);path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf8')
report=dict(stage='importing',revision=REVISION,backup=str(backup),maps=[],leaf_updates={},gameplay_tested=False,rendered=False)
def record():(ROOT/'Receipts/doorways-install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
try:
 for target in [TARGET]+SUBJECTS:
  rel=target.removeprefix('/Game/');preserve(PROJECT/'Content'/(rel+'.umap'))
  for category in ('__ExternalActors__','__ExternalObjects__'):
   folder=PROJECT/'Content'/category/rel
   if folder.exists():
    for path in folder.rglob('*'):
     if path.is_file():preserve(path)
 runpy.run_path(str(ROOT/'import_assets.py'),init_globals={'GEOMETRY_ONLY':True,'IMPORT_KINDS':{'Walls','WallFinish','Trim','Frames','Tiles'}})
 runpy.run_path(str(PROJECT/'SourceAssets/DungeonIsolationWard20260929/Scripts/import_assets.py'),
                init_globals={'WARD_IMPORT_NAMES':{'SM_Ward_Walls','SM_Ward_GlassDoorFrame'}})
 report['stage']='assets_saved';record()
 world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
 gen=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
 catalog=json.loads(gen.get_editor_property('module_catalog_json'))
 (backup/'production-before.json').write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf8')
 office=next(m for m in catalog['modules'] if m['id']=='MedicalDoctorOffice')
 specs={a['id']:a for a in read(ROOT/'Config/module.json')['runtime_actors'] if a['type']=='glass_door'}
 corrected=0
 for a in office['runtime_actors']:
  if a.get('id') not in specs:continue
  target=specs[a['id']]
  if a['position'][:2]!=target['position'][:2] or a['yaw']!=target['yaw']:raise RuntimeError('Preserve independently moved door '+a['id'])
  a['position'][2]=target['position'][2];a.pop('frame_id',None);corrected+=1
 if corrected!=14:raise RuntimeError('Unexpected office door count '+str(corrected))
 catalog['facility_flow']['medical_doorway_revision']=REVISION
 bank=catalog['facility_flow']['layout_bank']
 bank['contract_sha1']=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash'](catalog)
 gen.modify();gen.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
 save(world,TARGET);report['maps'].append(TARGET);record()
 write(FLOW/'Config/catalog.json',catalog);write(FLOW/'Config/layout-bank-v1.json',bank)
 write(ROOT/'Config/layout-bank.json',bank);write(ROOT/'Config/module.json',office)
 pending=copy.deepcopy(catalog);pending['facility_flow'].pop('layout_bank',None);write(ROOT/'Config/catalog-pending.json',pending)
 source_modules=read(LINE/'Config/source-modules.json')
 source_modules['modules']=[office if m['id']==office['id'] else m for m in source_modules['modules']]
 write(LINE/'Config/source-modules.json',source_modules)
 for target in SUBJECTS:
  world=u.EditorLoadingAndSavingUtils.load_map(target);changed=[]
  for actor in u.GameplayStatics.get_all_actors_of_class(world,u.WardGlassDoor):
   if 'MedicalOfficeWing20261010' not in {str(t) for t in actor.tags}:continue
   pos=actor.get_actor_location();actor.modify();pos.z=1.6;actor.set_actor_location(pos,False,True)
   changed.append(actor.get_actor_label())
  if len(changed)!=14:raise RuntimeError('Unexpected subject door count '+target)
  save(world,target);report['maps'].append(target);report['leaf_updates'][target]=changed;record()
 report.update(stage='maps_saved',office_leaves=corrected,saved_meshes=7,route_geometry_changed=False,
               layout_entries_preserved=len(bank['entries']),interior_clear_width_cm=326,office_door_floor_gap_cm=1)
 record();print('MEDICAL_DOORWAY_REPAIR_SAVED',flush=True)
except Exception:
 report.update(stage='incomplete',error=traceback.format_exc());record();raise
finally:
 if prior and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(prior)
