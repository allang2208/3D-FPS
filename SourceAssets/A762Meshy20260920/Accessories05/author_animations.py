"""Preserve accepted AKM whole-arm grip/contact actions on the shared rig.
Only replace A762 sight/muzzle/ejection marker tracks; action clocks are retained.
"""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;D=O/'Animations';D.mkdir(exist_ok=True)
src=json.loads((O/'sources.json').read_text())
markers=json.loads((O.parent/'Integration/authoring.json').read_text())['markers_blender_root']
report=json.loads((O/'animations.json').read_text()) if (O/'animations.json').exists() else {}
bpy.context.preferences.filepaths.save_version=0
for family in ['vertical','canted','prism','angled']:
 directory=O.parents[1]/'RifleTacticalSprint20260915'/'AKM'/family.title()
 for kind in ['Enter','Loop','Exit']:
  src['animations'][family+'/sprint_'+kind.lower()]={'source':[str(directory/('AKM_TacticalSprint_'+family.title()+'_Editable.blend'))],
   'action':'AKM_TacticalSprint_'+family.title()+'_'+kind,'asset':'/Game/Weapons/RifleTacticalSprint20260915/AKM/'+family.title()+'/A_AKM_TacticalSprint_'+family.title()+'_'+kind}
for key,info in src['animations'].items():
 if key in report:continue
 family,clip=key.split('/');blend=Path(info['source'][0]).with_suffix('.blend')
 bpy.ops.wm.open_mainfile(filepath=str(blend));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 old=bpy.data.actions[info['action']] if 'action' in info else r.animation_data.action
 action=old.copy();action.name='A_A762_'+family+'_'+clip;action.use_fake_user=True
 r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in list(bag.fcurves):
     if any('"'+n+'"' in curve.data_path for n in markers):bag.fcurves.remove(curve)
 start,end=map(int,old.frame_range);fps=s.render.fps/s.render.fps_base
 for f in range(start,end+1):
  s.frame_set(f);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix.copy()
  for name,p in markers.items():
   b=r.pose.bones[name];m=b.matrix.copy();m.translation=root@Vector(p);b.matrix=m
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f)
 s.frame_start=start;s.frame_end=end;s.frame_set(start)
 bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 dest=D/family;dest.mkdir(exist_ok=True)
 bpy.ops.export_scene.fbx(filepath=str(dest/(action.name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
 bpy.data.libraries.write(str(dest/(action.name+'.blend')),{r,action},fake_user=True)
 report[key]={'name':action.name,'fps':fps,'frames':end-start,'source':str(blend),'source_asset':info['asset']}
 (O/'animations.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('A762_GRIP_ANIMATION_AUTHORED',key,flush=True)
