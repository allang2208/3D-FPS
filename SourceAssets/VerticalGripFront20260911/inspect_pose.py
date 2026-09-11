import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
O=Path(__file__).parent;S=O.parent;O.mkdir(exist_ok=True)

def render(r,fit,label):
 s=bpy.context.scene
 for ob in s.objects:
  if ob.type=='LIGHT':ob.hide_render=True
 G=r.matrix_world@r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root']);H=r.matrix_world@r.pose.bones['hand_l'].matrix
 cam=bpy.data.cameras.new('ReviewCamera');c=bpy.data.objects.new('ReviewCamera',cam);s.collection.objects.link(c);s.camera=c;cam.type='ORTHO';cam.clip_start=.001
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=900;s.render.resolution_y=800;s.render.resolution_percentage=100
 for off in [(-.6,-.5,.8),(.6,.2,.7)]:
  ld=bpy.data.lights.new('ReviewLight','AREA');ld.energy=70;ld.size=1;l=bpy.data.objects.new('ReviewLight',ld);s.collection.objects.link(l);l.location=G.translation+Vector(off);l.rotation_euler=(G.translation-l.location).to_track_quat('-Z','Y').to_euler()
 R=G.to_quaternion().to_matrix()
 for view,focus,off,scale in [('player',(-.065,.075,-.065),(-.40,.38,.30),.27),('palm',(0,0,-.04),(0,-.4,.02),.26),('thumb',(0,0,-.035),(0,.4,.01),.24),('front',(0,0,-.04),(.4,0,.03),.28),('arm',(-.15,.1,-.10),(-.35,.45,.3),.67)]:
  target=G.translation+R@Vector(focus);c.location=target+R@Vector(off);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();cam.ortho_scale=scale;s.render.filepath=str(O/(label+'_'+view+'.png'));bpy.ops.render.render(write_still=True)

if __name__=='__main__':
 result={}
 for key,path,action in [('vertical',S/'VerticalGripErgonomic20260911/vertical/A_M4_Vertical_idle.blend',None),('prism',S/'VerticalGripErgonomic20260911/prism/A_M4_Prism_idle.blend',None),('original',S/'M4ContactImpact20260910/M4_Hand_MAT_Editable.blend','M4_idle')]:
  bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
  if action:a=bpy.data.actions[action];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
  s.frame_set(0);bpy.context.view_layer.update();H=r.pose.bones['hand_l'].matrix;data={}
  for b in r.pose.bones:
   if b.name.endswith('_l'):
    data[b.name]={'basis_euler_deg':[math.degrees(v) for v in b.matrix_basis.to_euler('XYZ')],'basis':[list(x) for x in b.matrix_basis],'pose':[list(x) for x in b.matrix],'rest':[list(x) for x in b.bone.matrix_local],'in_hand':list(H.inverted()@b.head),'parent':b.parent.name if b.parent else None}
  result[key]=data
  if key!='original':render(r,json.loads((path.parent/'fit_final.json').read_text()),'before_'+key)
 (O/'before_bones.json').write_text(json.dumps(result,indent=2));print('FRONT_REFERENCE_READY',flush=True)
