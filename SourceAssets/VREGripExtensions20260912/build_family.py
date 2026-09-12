"""Patch only left-arm rotations and clavicle reach in existing timed clips."""
import bpy,sys,json
from pathlib import Path
from mathutils import Matrix,Quaternion
sys.path.insert(0,str(Path(__file__).parent));from case import *
sys.path.insert(0,str(O/'ReferenceWorkflow'));from front_pose import solve_arm
fits=read(O/'fits.json');OUT.mkdir(exist_ok=True)
requested=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
report=read(OUT/'build.json') if (OUT/'build.json').exists() else {}
for w,v in FAMILIES:
 if any(x in ['canted','prism'] for x in requested) and v not in requested:continue
 fit=fits[w+':'+v];donor={n:Matrix(m).to_quaternion() for n,m in fit['basis'].items()};newroot=Matrix(fit['hand_in_root']);griproot=Matrix(fit['grip_in_root'])
 D=OUT/w/v;D.mkdir(parents=True,exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(source_dir(w,v)/(prefix(w,v)+'idle.blend')));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0)
 heldroot=r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_l'].matrix
 deltas={n:donor[n]@r.pose.bones[n].matrix_basis.to_quaternion().inverted() for n in donor}
 for clip,meta in metadata(w,v).items():
  clip_filter=[x for x in requested if x not in ['canted','prism']]
  if clip_filter and clip not in clip_filter:continue
  name=prefix(w,v)+clip;source=source_dir(w,v)/(name+'.blend')
  bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
  a=r.animation_data.action.copy();r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
  curves={fc.data_path+'#'+str(fc.array_index):fc for la in a.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves}
  frames=[p.co.x for p in curves['pose.bones["hand_l"].rotation_quaternion#0'].keyframe_points]
  names=['clavicle_l','upperarm_l','lowerarm_l','hand_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_twist_01_l','lowerarm_twist_02_l']+list(donor)
  rest={b.name:b.matrix_local.copy() for b in r.data.bones};localrest={n:rest[r.pose.bones[n].parent.name].inverted()@rest[n] for n in names}
  samples=[];previous={};maxbend=0;preserved=0
  for f in frames:
   s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();armw,fingerw=weights(w,clip,f,meta['frames'])
   baseline={n:r.pose.bones[n].matrix_basis.copy() for n in names};row={n:m.copy() for n,m in baseline.items()}
   if armw>0:
    p={b.name:b.matrix.copy() for b in r.pose.bones};root=p['WPN_root'];H=p['hand_l'].copy();oldtarget=root@heldroot;newtarget=root@newroot
    deltaq=newtarget.to_quaternion()@oldtarget.to_quaternion().inverted()
    H=Matrix.LocRotScale(H.translation+(newtarget.translation-oldtarget.translation)*armw,Quaternion().slerp(deltaq,armw)@H.to_quaternion(),H.to_scale())
    metric=solve_arm(p,rest,H,root@griproot,armw)
    if armw>.999:maxbend=max(maxbend,metric['wrist_axis_bend_deg'])
    for n in names:
     loc,q,scale=baseline[n].decompose()
     if n in donor:q=Quaternion().slerp(deltas[n],fingerw)@q
     else:
      local=localrest[n].inverted()@(p[r.pose.bones[n].parent.name].inverted()@p[n]);q=local.to_quaternion()
      if n=='clavicle_l':loc=local.translation
     row[n]=Matrix.LocRotScale(loc,q,scale)
   else:preserved+=1
   for n in names:
    loc,q,scale=row[n].decompose()
    if n in previous and previous[n].dot(q)<0:q.negate()
    previous[n]=q.copy();row[n]=(loc,q,scale)
   samples.append(row)
  for n in names:
   for prop,index,count in [('rotation_quaternion',1,4)]+([('location',0,3)] if n=='clavicle_l' else []):
    for axis in range(count):
     fc=curves[f'pose.bones["{n}"].{prop}#{axis}'];assert len(fc.keyframe_points)==len(frames)
     for k,key in enumerate(fc.keyframe_points):key.co.y=samples[k][n][index][axis]
     fc.update()
  s.frame_set(0);bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(D/(name+'.blend')))
  bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
  bpy.ops.export_scene.fbx(filepath=str(D/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=s.render.fps/meta['sample_rate'],bake_anim_simplify_factor=0)
  report[w+':'+v+':'+clip]={**meta,'action':a.name,'previous_editable':str(source),'output':str(D/(name+'.fbx')),'closure':fit['closure'],'max_wrist_axis_bend_deg':maxbend,'preserved_samples':preserved,'asset':asset_dir(w,v)+'/'+name,'baseline_asset':asset_dir(w,v,True)+'/'+name}
  (OUT/'build.json').write_text(json.dumps(report,indent=2));print('EXTENSION_CLIP_READY',w,v,clip,flush=True)
print('EXTENSION_BUILD_READY',len(report),flush=True)
