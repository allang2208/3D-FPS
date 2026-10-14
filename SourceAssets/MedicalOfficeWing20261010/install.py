"""Save office/transition changes against the latest production catalog and map."""
import json,runpy,shutil,traceback,copy
from pathlib import Path
from datetime import datetime
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007';LINE=PROJECT/'SourceAssets/DungeonHospitalLine20261003'
TARGET='/Game/GameMaps/L_Dungeon_Randomized';HOSPITAL='/Game/GameMaps/Design/L_Hospital_Theme_Subject'
SUBJECT='/Game/GameMaps/Design/L_MedicalDoctorOffice_Subject'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
R=runpy.run_path(str(ROOT/'recipe.py'));assemble=runpy.run_path(str(ROOT/'scene_assembly.py'))['populate']
save=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionCoverage20261009/install.py'))['save']
def paths(v):
 if isinstance(v,str) and v.startswith('/Game/'):yield v.split('.')[0]
 elif isinstance(v,dict):
  for x in v.values():yield from paths(x)
 elif isinstance(v,list):
  for x in v:yield from paths(x)
def main():
 editor=(u.get_editor_subsystem(u.UnrealEditorSubsystem) or u.new_object(u.UnrealEditorSubsystem))
 if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve active play/unsaved maps')
 prior=editor.get_editor_world().get_path_name().split('.')[0] if editor.get_editor_world() else None
 report=dict(stage='saving',maps=[],game_run=False,tested=False,rendered=False)
 def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True)
 def preserve(p):
  if p.exists():
   dest=backup/p.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 def write(p,v,compact=False):
  preserve(p);p.write_text(json.dumps(v,ensure_ascii=False,**({'separators':(',',':')} if compact else {'indent':2})),encoding='utf8')
 try:
  for target in (TARGET,HOSPITAL,SUBJECT):
   rel=target.removeprefix('/Game/');preserve(PROJECT/'Content'/(rel+'.umap'))
   for category in ('__ExternalActors__','__ExternalObjects__'):
    folder=PROJECT/'Content'/category/rel
    if folder.exists():
     for p in folder.rglob('*'):
      if p.is_file():preserve(p)
  module=read(ROOT/'Config/module.json');bank=read(ROOT/'Config/layout-bank.json')
  if len(bank['entries'])!=120:raise RuntimeError('Replacement production bank still incomplete')
  world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
  gen=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
  raw=gen.get_editor_property('module_catalog_json');(backup/'production-before.json').write_text(raw,encoding='utf8')
  latest=json.loads(raw);catalog=R['apply'](latest)
  pending=read(ROOT/'Config/catalog-pending.json')
  # Reject unrelated structural edits made during the bake, preserving the current map.
  def geometry(c):
   return {m['id']:{k:m.get(k) for k in ('cells','ports','port_pairs','min','max','walk_polyline','side_ports')} for m in c['modules']}
  layout_fields=('themed_routes','mission_rules','room_ids','start_position','start_normal','start_connection','reserved_min','reserved_max')
  if geometry(catalog)!=geometry(pending) or any(catalog.get(k)!=pending.get(k) for k in layout_fields):
   raise RuntimeError('Production geometry changed during office authoring; retain latest map and rebuild bank from it')
  catalog=R['apply'](latest,bank);bank=catalog['facility_flow']['layout_bank']
  assets={a.get_path_name():a for a in gen.get_editor_property('module_assets') if a}
  for path in sorted(set(paths(module))):
   a=u.load_asset(path)
   if not a:raise RuntimeError('Office asset unavailable '+path)
   assets[a.get_path_name()]=a
  gen.modify();gen.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));gen.set_editor_property('module_assets',list(assets.values()))
  save(world,TARGET);report['maps'].append(TARGET);record()
  write(FLOW/'Config/catalog.json',catalog);write(FLOW/'Config/layout-bank-v1.json',bank,True);write(ROOT/'Config/layout-bank.json',bank,True)
  pending=copy.deepcopy(catalog);pending['facility_flow'].pop('layout_bank',None)
  write(ROOT/'Config/catalog-pending.json',pending,True)

  # Update only the first room and rigidly move the retained downstream hospital line.
  world=u.EditorLoadingAndSavingUtils.load_map(HOSPITAL);actors=(u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem))
  line=read(LINE/'Config/line.json');oldfirst=line['sequence'][0]
  if oldfirst not in ('Drainage','MedicalDoctorOffice'):raise RuntimeError('Preserve independently changed medical subject')
  oldpose=line['placements'][0];firstid='MedicalDoctorOffice';newexit=module['ports'][1]['position']
  firstlink=next(p for p in line['placements'] if p.get('name') in ('DrainageWardLink','OfficeWardLink'))
  delta=u.Vector(newexit[0]-firstlink['position'][0],newexit[1]-firstlink['position'][1],newexit[2]-firstlink['position'][2])
  for a in list(actors.get_all_level_actors()):
   tags={str(t) for t in a.tags};label=a.get_actor_label()
   if 'HospitalLine.Subject' not in tags:continue
   if oldfirst in tags or 'MedicalOfficeWing20261010' in tags:actors.destroy_actor(a);continue
   if tags.intersection({'AbandonedIsolationWard','AbandonedAnatomyTheatre','DrainageWardLink','OfficeWardLink','WardTheatreLink'}) or label=='HospitalLine_EndCap':
    a.modify();a.set_actor_location(a.get_actor_location()+delta,False,True)
   elif label=='HospitalLine_PlayerStart':
    a.modify();a.set_actor_location(u.Vector(0,-160,105),False,True)
   elif label=='HospitalLine_StartCap':
    a.modify();a.set_actor_location(u.Vector(0,0,140),False,True)
  assemble(module,dict(id=firstid,position=[0,0,0],yaw=0),prefix='HospitalLine_Office')
  line['sequence'][0]=firstid;line['placements'][0]=dict(id=firstid,position=[0,0,0],yaw=0)
  for p in line['placements'][1:]:
   p['position']=[p['position'][0]+delta.x,p['position'][1]+delta.y,p['position'][2]+delta.z]
   if p.get('name')=='DrainageWardLink':p['name']='OfficeWardLink'
  line['player_start']=[0,-160,105];line['office_revision']=R['REVISION'];save(world,HOSPITAL);write(LINE/'Config/line.json',line)
  write(LINE/'Config/source-modules.json',dict(modules=[next(m for m in catalog['modules'] if m['id']==i) for i in line['sequence']]+[next(m for m in catalog['modules'] if m['id']=='Transit')]))
  report['maps'].append(HOSPITAL);record()

  world=u.EditorLoadingAndSavingUtils.load_map(SUBJECT) if u.EditorAssetLibrary.does_asset_exist(SUBJECT) else u.EditorLoadingAndSavingUtils.new_blank_map(False)
  for a in list(actors.get_all_level_actors()):
   if 'MedicalOfficeWing20261010' in {str(t) for t in a.tags} or 'MedicalDoctorOffice' in {str(t) for t in a.tags}:actors.destroy_actor(a)
  world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Script/FPSGAME.FPSGAMEGameMode'))
  assemble(module,dict(id=firstid,position=[0,0,0],yaw=0))
  helpers=runpy.run_path(str(PROJECT/'SourceAssets/HospitalContainers20261003/Scripts/unreal_helpers.py'))
  container_rules=runpy.run_path(str(PROJECT/'SourceAssets/HospitalContainers20261003/Scripts/catalog_rules.py'))
  outline=helpers['ensure_outline'](actors,container_rules['rules']()['outline'],'MedicalOffice_ContainerOutline',u.load_asset,True)
  outline.set_editor_property('tags',list(outline.tags)+[u.Name('MedicalOfficeWing20261010')])
  start=actors.spawn_actor_from_class(u.PlayerStart,u.Vector(0,-160,105),u.Rotator(pitch=0,yaw=-90,roll=0))
  start.set_editor_property('tags',[u.Name('MedicalOfficeWing20261010')])
  for p,scale in [([0,0,140],[3,.12,2.8]),([2000,-1100,140],[.12,3,2.8])]:
   a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*p));a.set_editor_property('tags',[u.Name('MedicalOfficeWing20261010')])
   a.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));a.static_mesh_component.set_material(0,u.load_asset('/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete'))
   a.static_mesh_component.set_collision_profile_name('BlockAll');a.set_actor_scale3d(u.Vector(*scale))
  save(world,SUBJECT);report['maps'].append(SUBJECT)
  report.update(stage='maps_saved',revision=R['REVISION'],bank_entries=len(bank['entries']),backup=str(backup),
     medical_sequence=line['sequence'],transition_families=catalog['themed_routes']['transition_families'],parts=len(module['parts']))
  record();print('MEDICAL_OFFICE_MAPS_SAVED',json.dumps(report,ensure_ascii=False),flush=True)
 except Exception:
  report.update(stage='save_incomplete',error=traceback.format_exc());record();raise
 finally:
  if prior and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(prior)
if __name__=='__main__':main()
