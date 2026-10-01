"""Import baked textures and bind ASH-only WS1 materials to the actual runtime meshes.
No skeletal FBX reimport, C++/game changes, PIE, captures, or gameplay tests.
"""
import json,shutil,hashlib
from pathlib import Path
import unreal as u
HERE=Path(__file__).parent
DEST='/Game/Weapons/ASH12/SurfaceStandard20260930'
L,E,A=u.MaterialEditingLibrary,u.EditorAssetLibrary,u.AssetToolsHelpers.get_asset_tools()
PLAN=json.loads((HERE/'slot_plan.json').read_text())
CARD=json.loads((HERE.parent/'surface_card.json').read_text())
RP=HERE/'install_receipt.json'
receipt=json.loads(RP.read_text()) if RP.exists() else {'backups':{},'textures':{},'materials':{},'bindings':{},'complete':False,'tested':False}
CONTENT=Path(u.Paths.project_dir()).resolve()/'Content'
WEATHER='/Game/Weapons/ASH12/Surface20260919/DA_ASH12_WetMaterials'

def record():RP.write_text(json.dumps(receipt,indent=1,ensure_ascii=False),encoding='utf-8')
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def backup(path):
 package=path.split('.')[0]
 if package in receipt['backups']:return
 if not package.startswith('/Game/Weapons/ASH12/'):raise RuntimeError('Outside ASH12')
 rel=package.removeprefix('/Game/')+'.uasset'
 dest=HERE/'Before'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(CONTENT/rel,dest)
 receipt['backups'][package]=str(dest);record()

# Only bind slots still matching the captured source or this installation.
for key,entry in PLAN.items():
 if not any(s['action']=='preset' for s in entry['slots'].values()):continue
 mesh=load(entry['path']);prop='materials' if key=='ASH12' else 'static_materials'
 for slot in mesh.get_editor_property(prop):
  spec=entry['slots'].get(str(slot.material_slot_name))
  if not spec or spec['action']!='preset':continue
  path=slot.material_interface.get_path_name() if slot.material_interface else ''
  if path!=spec['before'] and not path.startswith(DEST+'/Materials/'):
   raise RuntimeError('Target slot changed since source capture: '+entry['path']+' '+str(slot.material_slot_name))

def texture(name):
 if name in texture_cache:return texture_cache[name]
 source=HERE/'Bake'/(name+'.png');path=DEST+'/Textures/'+name
 digest=hashlib.sha256(source.read_bytes()).hexdigest()
 if not E.does_asset_exist(path) or receipt['textures'].get(name,{}).get('sha256')!=digest:
  task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST+'/Textures';task.destination_name=name
  task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
 tex=load(path);tex.set_editor_property('srgb',False);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
 tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON)
 E.set_metadata_tag(tex,'WeaponSurfaceVersion','WS1-ASH12-20260930');save(tex)
 receipt['textures'][name]={'path':tex.get_path_name(),'source':str(source),'sha256':digest};record()
 texture_cache[name]=tex;return tex

texture_cache={};instances={}
for key,entry in PLAN.items():
 for name,spec in entry['slots'].items():
  if spec['action']!='preset':continue
  suffix=name.removeprefix('M_ASH12_').removeprefix('ASH_')
  mi_name='MI_ASH12_WS_'+key+'_'+suffix
  path=DEST+'/Materials/'+mi_name
  mi=load(path) if E.does_asset_exist(path) else A.create_asset(mi_name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
  L.clear_all_material_instance_parameters(mi)
  if spec.get('regional'):parent=DEST+'/Presets/MI_ASH12_WS_Regions_'+spec['preset']
  else:parent=DEST+'/Master/M_ASH12_WS_'+('ExtMag' if spec.get('seam_normal') else 'Static')
  mi.set_editor_property('parent',load(parent))
  scalars={};vectors={}
  if not spec.get('regional'):
   scalars.update(CARD['presets'][spec['preset']].get('scalars',{}));vectors.update(CARD['presets'][spec['preset']].get('vectors',{}))
  density=spec['uv']['uv_per_cm']
  scalars.update(MaskUVChannel=float(spec.get('mask_uv',0)),BeadScale=round(2.42/max(density,1e-4),3))
  if spec.get('normal_tiling'):scalars['NormalUVScale']=spec['normal_tiling']
  scalars.update(spec['scalars']);vectors.update(spec['vectors'])
  for k,v in scalars.items():L.set_material_instance_scalar_parameter_value(mi,k,float(v))
  for k,v in vectors.items():L.set_material_instance_vector_parameter_value(mi,k,u.LinearColor(*v,1))
  tex={'SurfaceMask':texture(spec['mask_name']) if spec['mask']=='bake' else load('/Game/Weapons/WeaponSurface/Textures/T_WS_MaskNeutral')}
  if spec.get('normal'):tex['SurfaceNormal']=load(spec['normal'])
  for k,v in tex.items():L.set_material_instance_texture_parameter_value(mi,k,v)
  L.update_material_instance(mi);E.set_metadata_tag(mi,'WeaponSurfacePreset',spec['preset']);save(mi)
  instances[(key,name)]=mi
  receipt['materials'][mi_name]={'path':mi.get_path_name(),'parent':parent,'preset':spec['preset'],
    'scalars':scalars,'vectors':vectors,'textures':{k:v.get_path_name() for k,v in tex.items()},'original':spec['before']}
  record()

# The WS1 ASH-specific graph has its own water stage. The existing ASH table makes
# each saved instance its own wet replacement, requiring no shared C++ change.
backup(WEATHER);weather=load(WEATHER);mapping=dict(weather.get_editor_property('wet_materials'))
for mi in instances.values():mapping[mi.get_path_name()]=mi
weather.set_editor_property('wet_materials',mapping);save(weather)
receipt['wet_mapping']={'asset':WEATHER,'added':{mi.get_path_name():mi.get_path_name() for mi in instances.values()}};record()

for key,entry in PLAN.items():
 selected={name:mi for (owner,name),mi in instances.items() if owner==key}
 if not selected:continue
 backup(entry['path']);mesh=load(entry['path']);prop='materials' if key=='ASH12' else 'static_materials'
 slots=mesh.get_editor_property(prop);changed=[]
 for i,s in enumerate(slots):
  name=str(s.material_slot_name)
  if name not in selected:continue
  before=s.material_interface.get_path_name() if s.material_interface else None
  s.material_interface=selected[name];slots[i]=s
  changed.append({'slot':name,'before':before,'after':selected[name].get_path_name()})
 mesh.set_editor_property(prop,slots)
 # Record the applied property; UE struct arrays must be written back explicitly.
 actual={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in mesh.get_editor_property(prop)}
 if any(actual[c['slot']]!=c['after'] for c in changed):raise RuntimeError('Slot write failed '+key)
 E.set_metadata_tag(mesh,'WeaponSurfaceVersion','WS1-ASH12-20260930');save(mesh)
 receipt['bindings'][entry['path']]=changed;record()
 print('ASH12_WS_BOUND',key,len(changed),flush=True)
receipt['kept']={key:{name:s['reason'] for name,s in e['slots'].items() if s['action']=='keep'} for key,e in PLAN.items()}
receipt['complete']=True;record()
print('ASH12_WS_INSTALL_COMPLETE',len(receipt['materials']),len(receipt['bindings']),len(receipt['textures']),flush=True)
