"""Local joint contours, axillary sculpt and shoulder skin-weight correction.
Keep the V07 UVs, identity, original rig rests and all action timing.
"""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'foreman-downstroke-v07-20260906/foreman-downstroke-v07.blend'))
a=bpy.data.objects['ForemanRig']; body=bpy.data.objects['ForemanBody']; s=bpy.context.scene
actions=[act for act in bpy.data.actions if act.name in ['Idle','Walk','Attack','Death','Howl']]
a.animation_data.action=None
for tr in a.animation_data.nla_tracks:tr.mute=True
for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
def ss(lo,hi,x):
 u=max(0.,min(1.,(x-lo)/(hi-lo)));return u*u*(3-2*u)
def mesh_stats():
 bm=bmesh.new();bm.from_mesh(body.data)
 d={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)}
 bm.free();return d
report={'before':mesh_stats(),'method':'Local joint contour cuts + 24mm axillary crease + shoulder weight relaxation; original UVs and elbow/hand influences retained','cuts':[]}
shoulder=a.data.bones['upper_arm.R'].head_local.copy(); elbow=a.data.bones['forearm.R'].head_local.copy()
axis=(elbow-shoulder).normalized(); elbow_axis=(a.data.bones['hand.R'].head_local-shoulder).normalized()
def in_patch(co):return co.x<-.34 and 1.34<co.z<2.23
bm=bmesh.new();bm.from_mesh(body.data)
# Cuts interpolate existing corner UVs and deform data. Preserve both cloth
# surfaces and the shared boundary, which automatic patch remeshing lost.
for center,normal,offsets in [(shoulder,axis,[-.07,-.025,.02,.065,.115,.175]),(elbow,elbow_axis,[-.09,-.045,0,.045,.09])]:
 for offset in offsets:
  fs=[f for f in bm.faces if all(in_patch(v.co) for v in f.verts)]
  es=set(e for f in fs for e in f.edges);vs=set(v for f in fs for v in f.verts)
  cut=bmesh.ops.bisect_plane(bm,geom=list(vs)+list(es)+fs,dist=1e-6,plane_co=center+normal*offset,plane_no=normal,clear_inner=False,clear_outer=False)
  report['cuts'].append({'center':list(center+normal*offset),'new_contour_edges':sum(isinstance(g,bmesh.types.BMEdge) for g in cut['geom_cut'])})
bm.normal_update();bm.to_mesh(body.data);bm.free();body.data.update()
report['after_cuts']=mesh_stats()
assert report['after_cuts']['boundary_edges']==0,report
assert report['after_cuts']['nonmanifold_edges']==0,report
# Recess only the inner sleeve to form an axillary crease; pin the front
# apron, shoulder silhouette and cuff. Units are meters.
sculpt_max=0.;sculpt_count=0
for v in body.data.vertices:
 x,y,z=v.co; mask=ss(.36,.43,-x)*(1-ss(.54,.61,-x))*math.exp(-((z-1.79)/.115)**2)*(1-ss(.17,.25,abs(y)))
 delta=.024*mask
 if delta>1e-6:v.co.x-=delta;sculpt_count+=1;sculpt_max=max(sculpt_max,delta)
report['sculpt']={'vertices':sculpt_count,'max_displacement_m':sculpt_max}
# BMesh has interpolated the skin onto the new contour vertices. Enforce
# glTF's four-weight contract and reject any missing deformation data.
rebound=0
for v in body.data.vertices:
 w={g.group:g.weight for g in v.groups if g.weight>1e-8}
 assert sum(w.values())>1e-8,(v.index,list(v.co))
 values=sorted(w.items(),key=lambda it:-it[1])[:4];total=sum(weight for _,weight in values)
 assert total>0,(v.index,list(v.co))
 for group in body.vertex_groups:group.remove([v.index])
 for gi,weight in values:body.vertex_groups[gi].add([v.index],weight/total,'REPLACE')
report['cut_surface_rebound_vertices']=rebound
# Smooth the shoulder's torso/upper-arm transition along connected edges.
# Forearm/hand weights remain fixed so the elbow bend and grip are retained.
coords=np.array([v.co[:] for v in body.data.vertices]);edges=np.array([e.vertices[:] for e in body.data.edges])
src=np.concatenate([edges[:,0],edges[:,1]]);dst=np.concatenate([edges[:,1],edges[:,0]])
conductance=1/np.maximum(np.linalg.norm(coords[src]-coords[dst],axis=1),.02)
denom=np.bincount(src,weights=conductance,minlength=len(coords))
w=np.zeros((len(coords),len(body.vertex_groups)))
for v in body.data.vertices:
 for g in v.groups:w[v.index,g.group]=g.weight
fixed=[g.index for g in body.vertex_groups if any(term in g.name for term in ['forearm','hand','finger','thumb'])]
mobile=[k for k in range(w.shape[1]) if k not in fixed];target_sum=w[:,mobile].sum(axis=1)
mask=np.array([ss(.34,.48,-x)*(1-ss(.78,.90,-x))*ss(1.34,1.47,z)*(1-ss(2.08,2.23,z)) if x<0 and not (abs(x)<.56 and 1.28<z<1.85 and y<-.20) else 0 for x,y,z in coords])
for iteration in range(90):
 avg=np.stack([np.bincount(src,weights=conductance*w[dst,k],minlength=len(coords))/np.maximum(denom,1e-12) for k in mobile],axis=1)
 v=w[:,mobile]+.6*mask[:,None]*(avg-w[:,mobile]);v*=target_sum[:,None]/np.maximum(v.sum(axis=1)[:,None],1e-12);w[:,mobile]=v
for i in np.where(mask>0)[0]:
 pinned=[(k,w[i,k]) for k in fixed if w[i,k]>1e-8]
 moving=sorted([(k,w[i,k]) for k in mobile if w[i,k]>1e-8],key=lambda it:-it[1])[:4-len(pinned)]
 total=sum(v for _,v in moving);remaining=1-sum(v for _,v in pinned)
 values=pinned+[(k,v*remaining/max(total,1e-12)) for k,v in moving]
 for g in body.vertex_groups:g.remove([int(i)])
 for gi,value in values:body.vertex_groups[gi].add([int(i)],float(value),'REPLACE')
report['shoulder_weight_relaxation_iterations']=90
report['clips']={act.name:(act.frame_range[1]-act.frame_range[0])/s.render.fps for act in actions}
report['after']=mesh_stats(); report['bone_count']=len(a.data.bones)
report['max_weight_error']=max(abs(sum(g.weight for g in v.groups)-1) for v in body.data.vertices)
report['max_influences']=max(sum(g.weight>1e-7 for g in v.groups) for v in body.data.vertices)
assert report['max_weight_error']<1e-5 and report['max_influences']<=4,report
assert all(math.isfinite(x) for l in body.data.uv_layers.active.data for x in l.uv)
a.animation_data.action=bpy.data.actions['Idle'];s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'foreman-retopo-v08.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in [a,body,bpy.data.objects['Whip'],bpy.data.objects['WhipHandle']]:o.select_set(True)
bpy.context.view_layer.objects.active=a
bpy.ops.export_scene.gltf(filepath=str(R/'foreman-retopo-v08.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_frame_step=1,export_def_bones=True)
(R/'retopo-report.json').write_text(json.dumps(report,indent=2));print('RETOPO',json.dumps(report))
