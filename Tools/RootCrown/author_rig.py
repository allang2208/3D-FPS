"""Preserve the Meshy body; add a continuous radial deformation rig to its crown."""
import bpy, json, math, hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector, Quaternion, Matrix
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/RootCrown_Source.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH')
verts=np.array([v.co[:] for v in mesh.data.vertices],dtype=np.float64)
original=[{mesh.vertex_groups[e.group].name:float(e.weight) for e in v.groups} for v in mesh.data.vertices]
original_names=[b.name for b in rig.data.bones]
hub=np.array([.18,.015,.67]);angles=np.radians(np.linspace(-25,200,10))
spokes=[]
crown=verts[verts[:,2]>.57]
polar=np.arctan2(crown[:,2]-hub[2],crown[:,0]-hub[0])
polar=np.where(polar<math.radians(-30),polar+math.tau,polar)
radius=np.linalg.norm(crown[:,[0,2]]-hub[[0,2]],axis=1)
for a in angles:
    sel=np.abs(polar-a)<math.radians(13)
    r=float(np.percentile(radius[sel],97)) if np.any(sel) else .22
    r=max(r,.20)
    points=[hub.copy()]
    for f in (.34,.68,1.02):
        x,z=hub[[0,2]]+np.array([math.cos(a),math.sin(a)])*r*f
        distance=(crown[:,0]-x)**2+(crown[:,2]-z)**2
        near=crown[np.argpartition(distance,min(350,len(distance)-1))[:350],1]
        y=float((np.percentile(near,15)+np.percentile(near,85))*.5)
        points.append(np.array([x,y,z]))
    spokes.append(dict(angle=float(a),radius=r,points=points))
bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
def bone(name,head,tail,parent):
    b=rig.data.edit_bones.new(name);b.head=Vector(head);b.tail=Vector(tail)
    b.parent=rig.data.edit_bones.get(parent) if parent else None;b.use_connect=False;b.use_deform=True
    b.align_roll(Vector((0,-1,0)))
    return b
bone('Root',(0,0,0),(0,0,.12),None)
rig.data.edit_bones['Bone_000'].parent=rig.data.edit_bones['Root']
# Keep the existing chain and joint head; the unused extrapolated tail was 49 cm above the surface.
rig.data.edit_bones['Bone_013'].tail=(-.23,.015,1.63)
bone('Stem_Lower',(.01,.14,.29),(-.10,.075,.45),'Bone_001')
bone('Stem_Upper',(-.10,.075,.45),hub,'Stem_Lower')
bone('Crown_Base',hub,hub+np.array([0,0,.15]),'Stem_Upper')
for i,s in enumerate(spokes):
    parent='Crown_Base';s['bones']=[]
    for j,suffix in enumerate(('Base','Flex','Rim')):
        name=f'Crown_{i+1:02d}_{suffix}';bone(name,s['points'][j],s['points'][j+1],parent)
        s['bones'].append(name);parent=name
bpy.ops.object.mode_set(mode='OBJECT')
def smooth(v):
    v=min(1.,max(0.,float(v)));return v*v*(3.-2.*v)
def blend_axis(value,centres):
    if value<=centres[0]:return [(0,1.)]
    if value>=centres[-1]:return [(len(centres)-1,1.)]
    k=int(np.searchsorted(centres,value)-1);t=smooth((value-centres[k])/(centres[k+1]-centres[k]))
    return [(k,1.-t),(k+1,t)]
def crown_weights(p):
    dx,dz=p[0]-hub[0],p[2]-hub[2];r=math.hypot(dx,dz);a=math.atan2(dz,dx)
    if a<math.radians(-30):a+=math.tau
    radial=smooth((r-.08)/.15)
    weights={'Crown_Base':1.-radial}
    for k,aw in blend_axis(a,angles):
        s=spokes[k]
        for j,rw in blend_axis(r/s['radius'],(.17,.51,.85)):
            weights[s['bones'][j]]=weights.get(s['bones'][j],0.)+radial*aw*rw
    return weights
new_weights=[];changed=0
for i,p in enumerate(verts):
    original_weight=original[i]
    # Protect every lower support vertex. Replace upper-body cross-talk only
    # through a smooth stalk band, before the actual crown attachment.
    change=smooth((p[2]-.33)/.25)
    if change==0:
        new_weights.append(original_weight);continue
    changed+=1
    crown_mix=smooth((p[2]-.54)/.15)
    stem_mix=smooth((p[2]-.36)/.10)
    target={'Stem_Lower':(1.-crown_mix)*(1.-stem_mix),'Stem_Upper':(1.-crown_mix)*stem_mix}
    for n,w in crown_weights(p).items():target[n]=target.get(n,0.)+w*crown_mix
    final={n:w*(1.-change) for n,w in original_weight.items()}
    for n,w in target.items():final[n]=final.get(n,0.)+w*change
    final=dict(sorted(((n,w) for n,w in final.items() if w>1e-6),key=lambda x:x[1],reverse=True)[:8])
    total=sum(final.values());new_weights.append({n:w/total for n,w in final.items()})
# Equal-position UV duplicates receive identical upper weights, preventing UV-seam tearing.
seam_weights={}
for i,p in enumerate(verts):
    if p[2]<=.33:continue
    key=tuple(np.round(p,6))
    if key in seam_weights:new_weights[i]=seam_weights[key]
    else:seam_weights[key]=new_weights[i]
mesh.vertex_groups.clear()
groups={b.name:mesh.vertex_groups.new(name=b.name) for b in rig.data.bones}
for i,row in enumerate(new_weights):
    for n,w in row.items():groups[n].add([i],w,'REPLACE')
for modifier in mesh.modifiers:
    if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=False
rig.name='RootCrownRig';mesh.name='RootCrownBody'
scene=bpy.context.scene;scene.render.fps=30;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
for b in rig.pose.bones:b.rotation_mode='QUATERNION'
def clear_pose():
    for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
def rotate(name,axis,degrees):
    local=rig.data.bones[name].matrix_local.to_3x3().inverted()@Vector(axis)
    rig.pose.bones[name].rotation_quaternion=Quaternion(local.normalized(),math.radians(degrees))
def pose(cup=0.,sway=0.,ripple=0.):
    clear_pose();rotate('Crown_Base',(0,1,0),sway)
    for i,s in enumerate(spokes):
        axis=(-math.sin(s['angle']),0,math.cos(s['angle']))
        for j,name in enumerate(s['bones']):
            rotate(name,axis,-cup*(4.,7.,10.)[j]+ripple*math.sin(i*.75)*(0.,.7,1.5)[j])
    bpy.context.view_layer.update()
def evaluated():
    o=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());m=o.to_mesh()
    p=np.array([v.co[:] for v in m.vertices]);o.to_mesh_clear();return p
edges=np.array([e.vertices[:] for e in mesh.data.edges]);length=np.linalg.norm(verts[edges[:,0]]-verts[edges[:,1]],axis=1)
use=length>1e-5;ground=verts[:,2]<.20
report={'original_bones':len(original_names),'total_bones':len(rig.data.bones),'added_bones':[b.name for b in rig.data.bones if b.name not in original_names],
 'triangles':sum(len(p.vertices)-2 for p in mesh.data.polygons),'vertices':len(verts),'upper_vertices_reweighted':changed,
 'max_influences':max(len(r) for r in new_weights),'weight_sum_error':max(abs(sum(r.values())-1.) for r in new_weights),
 'unweighted_vertices':sum(not r for r in new_weights),'lower_weights_preserved':all(original[i]==new_weights[i] for i,p in enumerate(verts) if p[2]<=.33),
 'spokes':[dict(angle_degrees=math.degrees(s['angle']),radius=s['radius'],bones=s['bones'],points=[p.tolist() for p in s['points']]) for s in spokes],
 'poses':{},'preview_only':True,'game_height_cm':350,'mesh_height_cm':170}
snapshots={}
for name,args in [('Rest',{}),('Cup',{'cup':1.}),('Spread',{'cup':-.6}),('Left',{'sway':8.}),('Right',{'sway':-8.}),('Rim',{'ripple':1.})]:
    pose(**args);p=evaluated();snapshots[name]=p
    ratio=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1)[use]/length[use]
    report['poses'][name]={'finite':bool(np.isfinite(p).all()),'edge_stretch_p99':float(np.percentile(ratio,99)),
        'edge_stretch_max':float(ratio.max()),'edge_compression_p01':float(np.percentile(ratio,1)),
        'foot_drift_m':float(np.max(np.linalg.norm(p[ground]-verts[ground],axis=1))),
        'max_displacement_m':float(np.max(np.linalg.norm(p-verts,axis=1)))}
    np.save(ROOT/'Reports'/('pose_'+name+'.npy'),p)
pose();report['rest_error_m']=float(np.max(np.linalg.norm(evaluated()-verts,axis=1)))
(ROOT/'Reports/rig-checks.json').write_text(json.dumps(report,indent=2),encoding='utf8')
assert report['unweighted_vertices']==0 and report['weight_sum_error']<1e-5
assert report['lower_weights_preserved'] and report['rest_error_m']<1e-5
assert all(p['finite'] and p['foot_drift_m']<1e-5 and p['edge_stretch_p99']<1.6 for p in report['poses'].values())
rig.animation_data_create();bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);rig.select_set(True)
bpy.context.view_layer.objects.active=rig
fbx=dict(use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,mesh_smooth_type='FACE',
    use_tspace=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Exports/SK_RootCrown.fbx'),bake_anim=False,**fbx)
clips=[]
for role,duration in [('Idle',4.),('CrownRigDemo',12.)]:
    action=bpy.data.actions.new('A_RootCrown_'+role);action.use_fake_user=True;rig.animation_data.action=action
    scene.frame_start=1;scene.frame_end=int(duration*30)+1
    for frame in range(scene.frame_start,scene.frame_end+1):
        t=(frame-1)/30.
        if role=='Idle':
            pulse=.5-.5*math.cos(t/duration*math.tau);pose(cup=.045*pulse,ripple=.16*math.sin(t/duration*math.tau))
        else:
            phase=t/duration
            if phase<.5:pose(cup=math.sin(phase*math.tau)**2)
            else:pose(cup=-.6*math.sin((phase-.5)*math.tau)**2,sway=6*math.sin((phase-.5)*math.tau))
        for b in rig.pose.bones:b.keyframe_insert('rotation_quaternion',frame=frame,group=b.name)
    scene.frame_set(1)
    path=ROOT/'Exports'/('A_RootCrown_'+role+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),bake_anim=True,**fbx)
    clips.append({'role':role,'fbx':str(path),'duration':duration})
rig.animation_data.action=None;pose();scene.frame_set(1)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'Exports/RootCrown_Rigged.glb'),export_format='GLB',use_selection=True,export_animations=False,export_all_influences=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/RootCrown_CrownRig.blend'))
report['clips']=clips
(ROOT/'Reports/rig.json').write_text(json.dumps(report,indent=2),encoding='utf8')
# Requested deformation checks: read the actual deformed skin under neutral lighting.
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1050;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('PreviewStudio');scene.world.use_nodes=True
background=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
background.inputs[0].default_value=(.6,.6,.6,1)
background.inputs[1].default_value=.6
for loc,power,size in [((-3,-4,5),500,4),((4,-1,3),320,3),((0,3,4),450,3)]:
    d=bpy.data.lights.new('Softbox','AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new('Softbox',d);scene.collection.objects.link(o);o.location=loc
    o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Camera');cd.type='ORTHO';cd.ortho_scale=2.2
cam=bpy.data.objects.new('Camera',cd);scene.collection.objects.link(cam);scene.camera=cam
for name,args in [('rest',{}),('cup',{'cup':1.}),('spread',{'cup':-.6})]:
    pose(**args)
    for view,loc in [('front',(0,-5,.9)),('side',(5,0,.9))]:
        cam.location=loc;cam.rotation_euler=(Vector((0,0,.85))-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(ROOT/'Previews'/(name+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
print('ROOT_CROWN_RIG_COMPLETE '+json.dumps({k:report[k] for k in ('total_bones','max_influences','rest_error_m','lower_weights_preserved','poses')}),flush=True)
