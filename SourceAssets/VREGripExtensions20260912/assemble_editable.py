import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));from case import *
build=read(OUT/'build.json')
for w,v in FAMILIES:
 D=OUT/w/v;name=prefix(w,v)
 bpy.ops.wm.open_mainfile(filepath=str(D/(name+'idle.blend')));r=bpy.data.objects['SK_M4_Infima'];idle=r.animation_data.action;idle.name=name+'idle_VRE';idle.use_fake_user=True
 for key,meta in build.items():
  if not key.startswith(w+':'+v+':') or key.endswith(':idle'):continue
  clip=key.split(':')[2]
  with bpy.data.libraries.load(str(Path(meta['output']).with_suffix('.blend')),link=False) as (src,dst):
   assert meta['action'] in src.actions;dst.actions=[meta['action']]
  assert dst.actions[0];dst.actions[0].name=name+clip+'_VRE';dst.actions[0].use_fake_user=True
 r.animation_data.action=idle;r.animation_data.action_slot=idle.slots[0];bpy.context.scene.frame_set(0)
 r['grasp_source']='VRE GrabAnimation';r['grasp_family']=v
 bpy.ops.wm.save_as_mainfile(filepath=str(D/(w.upper()+'_'+v+'_VRE_Editable.blend')));print('EDITABLE_READY',w,v,flush=True)
