"""Requested final geometry/detail check on UE-exported current assets."""
import bpy,bmesh,numpy as np,json,hashlib,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;PROJECT=O.parents[2];report={'scope':'actual saved front assembly, hard edges, panel masks, cover and unchanged legs','game_tested':False};bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O/'Exports/After_Body.fbx'),use_anim=False)
rig=next(ob for ob in bpy.data.objects if ob.type=='ARMATURE');inv=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted();arrays={};hard_ns=[];mask_values={}
for ob in list(bpy.data.objects):
 if ob.type!='MESH':continue
 xf=inv@ob.matrix_world;ns=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals];ob.data.transform(xf);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.data.normals_split_custom_set(ns)
 me=ob.data;me.calc_loop_triangles();v=np.array([q.co[:] for q in me.vertices]);color=me.color_attributes.active_color
 for label,prefix in [('front_hard','M_LMG201_H39_Cover'),('front_inner','M_LMG201_H39_Interior'),('receiver','M_LMG201_H39_Receiver'),('handguard','M_LMG201_H39_Handguard'),('cover','M_LMG201_R38_')]:
  selected=[p for p in me.loop_triangles if me.materials[p.material_index].name.startswith(prefix)]
  if not selected:continue
  f=np.array([p.vertices[:] for p in selected]);arrays.setdefault(label,[]).append(v[f])
  if label=='front_hard':
   for t in selected:
    for li in t.loops:hard_ns.append((v[me.loops[li].vertex_index],np.array(me.corner_normals[li].vector)))
  if label in ['receiver','handguard'] and color:
   values=[color.data[li if color.domain=='CORNER' else me.loops[li].vertex_index].color[0] for t in selected for li in t.loops];mask_values.setdefault(label,[]).extend(values)

def metric(tri):
 raw=tri.reshape(-1,3);v,idx=np.unique(np.round(raw,6),axis=0,return_inverse=True);f=idx.reshape(-1,3);valid=(f[:,0]!=f[:,1])&(f[:,1]!=f[:,2])&(f[:,2]!=f[:,0]);f=f[valid]
 e=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);edges,counts=np.unique(e,axis=0,return_counts=True);area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)
 return {'bounds':np.stack([v.min(0),v.max(0)]).tolist(),'triangles':len(f),'open_edges':int((counts==1).sum()),'near_zero_area_faces':int((area<1e-12).sum()),'max_edge_m':float(np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1).max()),'lateral_outliers_over_90mm':int((abs(v[:,0])>.09).sum())}
for label,items in arrays.items():report[label]=metric(np.concatenate(items))
report['front_all_materials']=metric(np.concatenate(arrays['front_hard']+arrays.get('front_inner',[])))
report['panel_masks']={k:{'min':float(min(v)),'max':float(max(v)),'fraction_active':float(np.mean(np.array(v)>.1))} for k,v in mask_values.items()}
fans={}
for p,n in hard_ns:fans.setdefault(tuple(np.round(p,6)),[]).append(n)
angles=[]
for normals in fans.values():
 if len(normals)<2:continue
 n=np.unique(np.round(normals,5),axis=0)
 if len(n)>1:angles.append(float(np.degrees(np.arccos(np.clip((n@n.T).min(),-1,1)))))
report['hard_edge_vertices_over_25deg']=int(np.sum(np.array(angles)>25));report['max_corner_normal_angle_deg']=max(angles,default=0)
for ob in list(bpy.data.objects):
 if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True)
def render_meshes_only(old):
 visible=[]
 for ob in list(bpy.data.objects):
  if ob in old or ob.type!='MESH':continue
  if ob.name.startswith(('UCX_','UBX_','USP_','UCP_')):bpy.data.objects.remove(ob,do_unlink=True)
  else:visible.append(ob)
 if len(visible)!=1:raise RuntimeError('Unexpected render object count '+str([ob.name for ob in visible]))
 return visible[0]
for key in ['BipodBase','BipodLegA','BipodLegB']:
 filename='After_BipodBase.fbx' if key=='BipodBase' else 'Before_'+key+'.fbx';old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Exports'/filename),use_anim=False);ob=render_meshes_only(old);ob.name=key
 if key!='BipodBase':ob.location+=Vector((.01356,-.46498,-.01398) if key=='BipodLegA' else (-.01196,-.46498,-.01398))
 else:
  me=ob.data;me.calc_loop_triangles();v=np.array([(ob.matrix_world@q.co)[:] for q in me.vertices]);report['bipod_base']=metric(v[np.array([p.vertices[:] for p in me.loop_triangles])])
cap=json.loads((O/'capture.json').read_text());report['unchanged_legs']={key:hashlib.sha256((PROJECT/'Content'/(cap[key]['asset'].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()==cap[key]['sha256'] for key in ['BipodLegA','BipodLegB']}
for key,pivot in [('FrontSight',(.0008,-.54212,.0648)),('RearSight',(.0008,.04252,.0855))]:
 path=O/'Exports'/('Current_'+key+'.fbx')
 if path.exists():
  old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False);ob=render_meshes_only(old);ob.location+=Vector(pivot)
(O/'saved_check.json').write_text(json.dumps(report,indent=2));print('H39_SAVED_CHECK',json.dumps(report),flush=True)
if any(report[k]['lateral_outliers_over_90mm'] for k in ['front_all_materials','cover','receiver','handguard']):raise RuntimeError('Lateral spike found')
if report['cover']['open_edges'] or report['front_all_materials']['open_edges'] or report['bipod_base']['open_edges']:raise RuntimeError('Open rebuilt shell found')
if not all(report['unchanged_legs'].values()):raise RuntimeError('Leg asset changed')
if len(report['panel_masks'])!=2 or any(not(0<v['fraction_active']<.85) for v in report['panel_masks'].values()):raise RuntimeError('Panel color mask lost')
if not report['hard_edge_vertices_over_25deg']:raise RuntimeError('Hard edges lost')
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1400;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.world=scene.world or bpy.data.worlds.new('Diag');s=scene.display.shading;s.light='STUDIO';s.color_type='SINGLE';s.single_color=(.35,.36,.39);s.show_shadows=True;s.show_cavity=True;s.cavity_type='BOTH';s.background_type='WORLD';scene.world.color=(.1,.11,.13)
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.clip_start=.005;cam.data.clip_end=5
for name,pos,target,scale in [('saved_front',(1,-.90,.16),(0,-.535,-.027),.54),('saved_front_under',(1,-.50,-.27),(0,-.50,.012),.35),('saved_receiver',(1,-.06,.23),(0,-.10,.04),.32)]:
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;scene.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
