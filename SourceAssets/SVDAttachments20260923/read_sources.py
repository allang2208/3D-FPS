"""Read current production donor import paths and material bindings for authoring."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;L=u.MaterialEditingLibrary
prior=json.loads((O.parent/'A762Meshy20260920/Accessories05/sources.json').read_text())
keys=['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring','suppressor','tactical_suppressor','brake','titanium_brake','vertical','tactical_vertical','canted','prism','angled','laser','flashlight']
result={'meshes':{},'materials':{},'textures':{},'animations':prior['animations']}
def sources(a):
 d=a.get_editor_property('asset_import_data');return list(d.extract_filenames()) if d else []
def texture(t):
 if t and t.get_path_name() not in result['textures']:
  result['textures'][t.get_path_name()]={'source':sources(t),'srgb':t.srgb,'flip_green':t.flip_green_channel}
def material(m):
 if not m or m.get_path_name() in result['materials']:return
 base=m.get_base_material();data={'base':base.get_path_name(),'class':m.get_class().get_name(),'params':{},'samples':[]}
 instance=isinstance(m,u.MaterialInstanceConstant)
 for kind in ['scalar','vector','texture','static_switch']:
  data['params'][kind]={}
  for n in getattr(L,'get_'+kind+'_parameter_names')(base):
   func=getattr(L,('get_material_instance_' if instance else 'get_material_default_')+kind+'_parameter_value',None)
   if not func:continue
   v=func(m,n)
   if kind=='texture':texture(v);v=v.get_path_name() if v else None
   elif kind=='vector':v=[v.r,v.g,v.b,v.a]
   data['params'][kind][str(n)]=v
 for n in L.get_material_expressions(base):
  if isinstance(n,u.MaterialExpressionTextureSample):
   t=n.get_editor_property('texture');texture(t)
   if t:data['samples'].append(t.get_path_name())
 result['materials'][m.get_path_name()]=data
for key in keys:
 path=prior['meshes'][key]['asset'];a=u.load_asset(path)
 if not a:raise RuntimeError(path)
 slots=[]
 for slot in a.static_materials:
  m=slot.material_interface
  if key=='laser' and len(slots)==0:m=u.load_asset('/Game/Weapons/TacticalDevices20260913/AKM/laser/M_AKM_laser_Body_OpticalV2') or m
  if key=='flashlight' and len(slots)==0:m=u.load_asset('/Game/Weapons/TacticalDevices20260913/HunyuanV3/AKM/flashlight/M_AKM_flashlight_Body_MetalTail') or m
  material(m);slots.append({'slot':str(slot.material_slot_name),'path':m.get_path_name()})
 result['meshes'][key]={'asset':path,'source':sources(a),'materials':slots,'sockets':{}}
 for name in ['Emitter','AimGuide','AimCenter']:
  q=a.find_socket(name)
  if q:result['meshes'][key]['sockets'][name]=list(q.relative_location.to_tuple())
a=u.load_asset('/Game/Weapons/SVDDragunov20260922/Complete20260923/SK_SVD_Manny')
result['svd']={'asset':a.get_path_name(),'source':sources(a),'skeleton':a.skeleton.get_path_name(),'materials':{str(x.material_slot_name):x.material_interface.get_path_name() for x in a.materials}}
for clip in ['idle','aim','fire','aim_fire','reload','reload_empty','equip','inspect','quick_melee','sprint_enter','sprint_loop','sprint_exit']:
 a=u.load_asset('/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_'+clip)
 result.setdefault('svd_clips',{})[clip]={'source':sources(a),'seconds':a.get_play_length()}
(O/'sources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
u.log('SVD_ATTACH_SOURCES_SAVED')
