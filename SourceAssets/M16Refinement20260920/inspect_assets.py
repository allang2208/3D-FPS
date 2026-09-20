import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
paths=['/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_holographic','/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_Holographic']
out={}
for path in paths:
 m=u.load_asset(path);rows=[]
 for s in m.static_materials:
  a=s.material_interface;b=a.get_base_material();v={'slot':str(s.material_slot_name),'material':a.get_path_name(),'blend':str(b.get_editor_property('blend_mode')),'two_sided':b.get_editor_property('two_sided'),'expressions':[]}
  for n in u.MaterialEditingLibrary.get_material_expressions(b):
   row={'class':n.get_class().get_name()}
   for prop in ('parameter_name','default_value','texture','const_coordinate','coordinate_index','code'):
    try:row[prop]=str(n.get_editor_property(prop))
    except Exception:pass
   v['expressions'].append(row)
  rows.append(v)
 out[path]=rows
out['animation_compression']={}
for path in ['/Game/Weapons/M16A2/Gameplay20260919/Animations/A_M16_reload','/Game/Weapons/M16A2/UniversalAttachments20260920/Animations/vertical/A_M16_vertical_reload']:
 a=u.load_asset(path);out['animation_compression'][path]={'bone_compression':str(a.get_editor_property('bone_compression_settings')),'skeleton':str(a.get_editor_property('skeleton')),'length':a.get_play_length()}
(O/'engine_inspection.json').write_text(json.dumps(out,indent=2))
print('M16_INSPECTION_SAVED')
