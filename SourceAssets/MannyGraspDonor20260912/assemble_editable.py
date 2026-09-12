import bpy,json
from pathlib import Path
O=Path(__file__).parent/'Final';build=json.loads((O/'build.json').read_text())
for weapon in ['m4','akm']:
 D=O/weapon/'vertical';prefix=f'A_{weapon.upper()}_{"Vertical" if weapon=="m4" else "vertical"}_'
 bpy.ops.wm.open_mainfile(filepath=str(D/(prefix+'idle.blend')))
 r=bpy.data.objects['SK_M4_Infima'];idle=r.animation_data.action;idle.name=prefix+'idle_VRE';idle.use_fake_user=True
 for key,meta in build.items():
  if not key.startswith(weapon+':') or key.endswith(':idle'):continue
  clip=key.split(':')[1]
  # Copies retain Blender's suffix because the previous action remains in the
  # file. Identify the active donor copy, not the original reference action.
  with bpy.data.libraries.load(str(D/(prefix+clip+'.blend')),link=False) as (src,dst):
   assert meta['action'] in src.actions;dst.actions=[meta['action']]
  assert dst.actions[0];dst.actions[0].name=prefix+clip+'_VRE';dst.actions[0].use_fake_user=True
 r.animation_data.action=idle;r.animation_data.action_slot=idle.slots[0];bpy.context.scene.frame_set(0)
 r['grasp_donor']='mordentral/VRExpPluginExample: GrabAnimation';r['grasp_mirror']='rest-frame anatomical reflection'
 bpy.ops.wm.save_as_mainfile(filepath=str(D/(weapon.upper()+'_Vertical_VRE_Editable.blend')))
 print('EDITABLE_READY',weapon,flush=True)
