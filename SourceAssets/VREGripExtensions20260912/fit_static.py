"""Reuse the authored closed grasp; align the entire fist to each mount."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
sys.path.insert(0,str(Path(__file__).parent));from case import *
sys.path.insert(0,str(O/'ReferenceWorkflow'));from front_pose import solve_arm,apply
import inspect_pose
base=read(DONOR/'Opening/0.8/aligned_fit.json')
handlocal=Matrix(base['grip_in_root']).inverted()@Matrix(base['hand_in_root'])
out=read(O/'fits.json') if (O/'fits.json').exists() else {}
requested=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
for w,v in FAMILIES:
 if requested and v not in requested:continue
 D=O/'Static'/w/v;D.mkdir(parents=True,exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(source_dir(w,v)/(prefix(w,v)+'idle.blend')));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0)
 fit=grip_fit(w,v);G=r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root']);inspect_pose.O=D
 if not (D/'before_palm.png').exists():inspect_pose.render(r,fit,'before')
 p={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};baseline={b.name:b.matrix_basis.copy() for b in r.pose.bones}
 # VRE's authored fist is unchanged for the 45-degree shaft; only its whole
 # frame follows the actual tilted grip body. The small handstop sits inside
 # a slightly more closed fist without per-finger surface optimization.
 body=Matrix(grip_fit('m4','canted')['body_in_grip']) if v=='canted' else Matrix.Identity(4)
 axial=.008 if v=='canted' else .004
 H=G@body@Matrix.Translation((0,0,axial))@handlocal
 if v=='canted':
  # Keep the source's natural forearm approach. A strict shaft alignment
  # forced >140 degrees of forearm twist, despite a nearly straight wrist.
  # Rotate the entire authored fist about its grasp center, never individual
  # finger joints; retain a quarter of the shaft-aligned orientation.
  pivot=G@body@Vector((0,0,-.060+axial));q=H.to_quaternion().slerp(p['hand_l'].to_quaternion(),.75);dq=q@H.to_quaternion().inverted()
  H=Matrix.LocRotScale(pivot+dq@(H.translation-pivot),q,H.to_scale())
 arm=solve_arm(p,rest,H,G)
 closure=.8 if v=='canted' else .9
 full=read(DONOR/'donor_fit.json')['basis'];bases={}
 for b in r.pose.bones:
  if b.name in full:
   loc,q,scale=Matrix(full[b.name]).decompose();q=Quaternion().slerp(q,closure)
   loc,unused,scale=baseline[b.name].decompose();m=Matrix.LocRotScale(loc,q,scale);bases[b.name]=[list(x) for x in m]
   p[b.name]=p[b.parent.name]@(rest[b.parent.name].inverted()@rest[b.name])@m
 r.animation_data.action=None;apply(r,p,rest)
 fitout={'weapon':w,'variant':v,'grip_in_root':fit['grip_in_root'],'hand_in_root':[list(x) for x in r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_l'].matrix],'basis':bases,'closure':closure,'axial_slide_m':axial,'source_approach_blend':.75 if v=='canted' else 0,'arm':arm}
 out[w+':'+v]=fitout
 bpy.ops.wm.save_as_mainfile(filepath=str(D/'Grasp_Editable.blend'));inspect_pose.render(r,fitout,'after')
 (O/'fits.json').write_text(json.dumps(out,indent=2));print('GRASP_STATIC_READY',w,v,arm,flush=True)
