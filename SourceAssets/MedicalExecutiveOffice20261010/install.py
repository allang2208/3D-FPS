"""Import and replace only medical office workstations in retained and production maps."""
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
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve active PIE or unsaved maps')
prior=editor.get_editor_world().get_path_name().split('.')[0] if editor.get_editor_world() else None
backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True)
report=dict(stage='preparing',revision=R['REVISION'],backup=str(backup),maps=[],tests_run=False,game_run=False,rendered=False)
def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def preserve(path):
 if path.exists():
  dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
def write(path,value):
 preserve(path);path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf8')
def asset(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing saved workstation dependency '+path)
 return a
try:
 for target in [TARGET]+[p for p,_ in SUBJECTS]:
  rel=target.removeprefix('/Game/');preserve(PROJECT/'Content'/(rel+'.umap'))
  for category in ('__ExternalActors__','__ExternalObjects__'):
   folder=PROJECT/'Content'/category/rel
   if folder.exists():
    for path in folder.rglob('*'):
     if path.is_file():preserve(path)
 runpy.run_path(str(ROOT/'import_assets.py'))
 report['stage']='assets_saved';record()
 world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
 gen=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
 raw=gen.get_editor_property('module_catalog_json');(backup/'production-before.json').write_text(raw,encoding='utf8')
 catalog=json.loads(raw);office=next(m for m in catalog['modules'] if m['id']=='MedicalDoctorOffice')
 before=copy.deepcopy(office);changes=R['apply'](office)
 catalog['facility_flow']['medical_workstation_revision']=R['REVISION']
 bank=catalog['facility_flow']['layout_bank'];bank['contract_sha1']=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash'](catalog)
 assets={a.get_path_name():a for a in gen.get_editor_property('module_assets') if a}
 for path in sorted(set(R['paths'](changes['new_parts']))):
  a=asset(path);assets[a.get_path_name()]=a
 gen.modify();gen.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));gen.set_editor_property('module_assets',list(assets.values()))
 save(world,TARGET);report['maps'].append(dict(path=TARGET,saved=True,workstations=changes['workstations']));record()
 write(FLOW/'Config/catalog.json',catalog);write(FLOW/'Config/layout-bank-v1.json',bank)
 write(OFFICE/'Config/module.json',office);write(OFFICE/'Config/layout-bank.json',bank)
 pending=copy.deepcopy(catalog);pending['facility_flow'].pop('layout_bank',None);write(OFFICE/'Config/catalog-pending.json',pending)
 sources=read(LINE/'Config/source-modules.json');sources['modules']=[office if m['id']==office['id'] else m for m in sources['modules']];write(LINE/'Config/source-modules.json',sources)
 write(ROOT/'Config/installed-module.json',office)
 for target,prefix in SUBJECTS:
  world=u.EditorLoadingAndSavingUtils.load_map(target)
  actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor)}
  # Resolve every existing workstation before changing this saved subject map.
  for key,*_ in R['STATIONS']:
   label=prefix+'_MedicalOffice.'+key+'.Desk'
   if label not in actors:raise RuntimeError('Target workstation unavailable '+target+' '+label)
  old_ids=set(changes['old_part_ids']);new_ids={p['id'] for p in changes['new_parts']};removed=0;created=0;replaced=0
  for key in old_ids-new_ids:
   a=actors.get(prefix+'_'+key)
   if a:AA.destroy_actor(a);removed+=1
  for part in changes['new_parts']:
   label=prefix+'_'+part['id'];a=actors.get(label)
   if a:a.modify();replaced+=1
   else:
    a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*part['position']),u.Rotator(pitch=0,yaw=part['yaw'],roll=0));created+=1
    a.set_actor_label(label);a.set_folder_path('HospitalLine/MedicalDoctorOffice')
    a.set_editor_property('tags',[u.Name('HospitalLine.Subject'),u.Name('MedicalDoctorOffice'),u.Name('MedicalOfficeWing20261010'),u.Name('MedicalExecutiveOffice20261010')])
   a.set_actor_location(u.Vector(*part['position']),False,True);a.set_actor_rotation(u.Rotator(pitch=0,yaw=part['yaw'],roll=0),True);a.set_actor_scale3d(u.Vector(1,1,1))
   c=a.static_mesh_component;c.modify();c.set_mobility(u.ComponentMobility.STATIC);c.set_editor_property('override_materials',[]);c.set_static_mesh(asset(part['mesh']))
   c.set_collision_profile_name('BlockAll' if part['collision'] else 'NoCollision');c.set_cast_shadow(True)
  save(world,target);report['maps'].append(dict(path=target,saved=True,workstations=len(R['STATIONS']),replaced=replaced,created=created,removed=removed));record()
 report.update(stage='maps_saved',workstations=len(R['STATIONS']),mesh_assets=6,materials=4,textures=2,layout_entries_preserved=len(bank['entries']))
 record();print('MEDICAL_EXECUTIVE_OFFICE_SAVED',len(report['maps']),'maps',flush=True)
except Exception:
 report.update(stage='incomplete',error=traceback.format_exc());record();raise
finally:
 if prior and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(prior)
