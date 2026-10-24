"""Patch the saved apartment in place, preserving placement, storage and animation."""
from pathlib import Path
from datetime import datetime
import sys,json,shutil,re,traceback
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
from surface_specs import *
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
MAP='/Game/GameMaps/L_CyberpunkApartment'
STOCK={
 'MI_Fabric_Charcoal_OPBR':'Fabric','MI_Fabric_Textile_Gray':'Linen','MI_Carpet_Gray_OPBR':'Carpet',
 'MI_BareSteel':'Steel','MI_BrushedSteel_Horizontal_OPBR':'Steel','MI_Paint_Black_SmallGrain_OPBR':'Teal',
 'MI_Rubber_Weatherstrip_OPBR':'Rubber','M_Reception_Stone':'Stone','M_Reception_Floor':'Floor',
 'M_Room_Rubber':'Rubber','M_RH2_Blue':'Plastic','M_RH2_Office_Steel':'Steel','M_RH2_Office_Rubber':'Rubber','M_RH2_Seam':'Fabric',
 'M_Staff_Ceramic':'Ceramic','M_Staff_PoolBlue_V4':'Plastic','M_Staff_PoolIvory_V4':'Ceramic',
 'M_Staff_MachineCoat_V7':'Teal','M_Staff_Stainless_V6':'Steel','M_Staff_KettleRubber_V6':'Rubber','M_Staff_CupGlaze_V7':'Ceramic',
 'M_Staff_FreshPlastic_V5':'Plastic','M_Staff_Terry_V3':'Linen','M_Staff_Hem_V3':'Linen'}
def load(path):
 o=u.load_asset(path)
 if not o:raise RuntimeError('Missing apartment upgrade dependency '+path)
 return o
def role_for(slot,material):
 name=material.get_name() if material else ''
 if slot.startswith('AP_'):
  role=ALIASES.get(slot[3:],slot[3:])
  if role in SPECS:return role
 if name.startswith(('M_AP_','MI_AP4_','M_AP4_')):
  role=name.split('_',2)[-1];role=ALIASES.get(role,role)
  if role in SPECS:return role
 return STOCK.get(name)
def apply_upgrade(world):
 mesh_report=json.loads((ROOT/'meshes_saved.json').read_text())
 if mesh_report['stage']!='meshes_saved':raise RuntimeError('Incomplete cabinet mesh import')
 replacements={k:load(v['path']) for k,v in mesh_report['meshes'].items()}
 surface_report=json.loads((ROOT/'surfaces_saved.json').read_text())
 if surface_report['stage']!='surfaces_saved':raise RuntimeError('Incomplete PBR import')
 base_mats={k:load(v['path']) for k,v in surface_report['materials'].items()}
 calibrated={};report={'components':[],'mesh_swaps':[],'material_slots_changed':0,'normal_bound_slots':0,'preserved':[]}
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  label=actor.get_actor_label()
  for c in actor.get_components_by_class(u.StaticMeshComponent):
   mesh=c.static_mesh
   if not mesh:continue
   if label.startswith(('BAY_','Bay_','CITY_')) or not c.is_visible() or c.get_editor_property('hidden_in_game'):
    report['preserved'].append({'actor':label,'component':c.get_name(),'reason':'exterior/hidden collision'});continue
   key=mesh.get_name().removeprefix('SM_AP_')
   if key in replacements:
    c.set_static_mesh(replacements[key]);mesh=replacements[key]
    # Old per-slot overrides may refer to different slots after replacing a door.
    c.set_editor_property('override_materials',[])
    report['mesh_swaps'].append({'actor':label,'component':c.get_name(),'key':key})
   slots=mesh.get_editor_property('static_materials');scale=c.get_world_scale()
   row={'actor':label,'component':c.get_name(),'mesh':mesh.get_path_name(),'slots':[]}
   for i,s in enumerate(slots):
    old=c.get_material(i);slot=re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name));role=role_for(slot,old)
    if not role:
     row['slots'].append({'slot':slot,'action':'preserved','material':old.get_path_name() if old else None,
       'reason':'screen/emitter/transparent glass/liquid/foliage or existing specialty surface'});continue
    spec=SPECS[role];tiling=spec['uv_m']/spec['period_m'];basis='authored metre UV; 1.20 scene scale'
    if not slot.startswith('AP_'):
     info=s.get_editor_property('uv_channel_data');density=list(info.get_editor_property('local_uv_densities'))
     if density and density[0]>0:
      tiling=max(.05,min(32.,density[0]*max(abs(scale.x),abs(scale.y),abs(scale.z))/(spec['period_m']*100.)))
      basis='mesh UV0 world-units density'
     else:
      # Library UVs retain their existing normal family; use authored source fallback.
      basis='library source UV; density unavailable, family scale'
    tiling=round(tiling,3);cache=(role,tiling)
    if cache not in calibrated:
     if abs(tiling-spec['uv_m']/spec['period_m'])<.001:mi=base_mats[role]
     else:
      name='MI_AP4_'+role+'_UV'+str(tiling).replace('.','p');path=BASE+'/Calibrated/'+name
      mi=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Calibrated',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
      L.set_material_instance_parent(mi,base_mats[role]);L.set_material_instance_scalar_parameter_value(mi,'UVScale',tiling)
      L.update_material_instance(mi)
      if not E.save_loaded_asset(mi,False):raise RuntimeError('UV instance save '+name)
     calibrated[cache]=mi
    c.set_material(i,calibrated[cache]);report['material_slots_changed']+=1;report['normal_bound_slots']+=1
    row['slots'].append({'slot':slot,'action':'PBR upgrade','role':role,'material':calibrated[cache].get_path_name(),
      'normal':spec['normal'],'uv_scale':tiling,'uv_basis':basis,'repeat_m':spec['period_m']})
   report['components'].append(row)
 report['calibrated_instances']=len(calibrated)
 next_revision=ROOT.parent/'RefinementV5'
 if (next_revision/'installed.json').exists():
  import runpy
  report['v5']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
 return report
def main():
 report={'stage':'preparing','map':MAP,'game_run':False,'rendered':False,'component_checks_requested':True}
 def record():(ROOT/'map_saved.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 try:
  ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
  if ed and ed.get_game_world():raise RuntimeError('Preserve running game')
  if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
  backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
  source=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap';shutil.copy2(source,backup/source.name)
  report['backup']=str(backup/source.name);record()
  world=u.EditorLoadingAndSavingUtils.load_map(MAP);report.update(apply_upgrade(world))
  if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Apartment map save failed')
  report['stage']='map_saved';record();(ROOT/'installed.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
  print('APARTMENT_V4_MAP_SAVED',report['material_slots_changed'],len(report['mesh_swaps']))
 except Exception:
  report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
