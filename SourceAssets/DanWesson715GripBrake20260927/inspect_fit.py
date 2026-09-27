"""Measure and render the saved UE geometry in the runtime mounting frame."""
import bpy, json, math, sys
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent/'FitInspection'
read=lambda name:json.loads((O/(name+'.json')).read_text(encoding='utf-8'))
host=read('host');poses=read('poses');manifest=read('manifest')
arms=read('bare_arms') if manifest['bare_arms'] else None
keys=['dw715_rubber_grip','dw715_target_wood_grip','dw715_muzzle_brake']
parts={k:read(k) for k in keys}
if '--candidate' in sys.argv:
    # Pre-import fitting uses the exported author's geometry, explicitly labelled.
    with bpy.data.libraries.load(str(O.parent/'DW715_GripBrake_Editable.blend'),link=False) as (src,dst):dst.objects=keys[:2]
    for k,ob in zip(keys[:2],dst.objects):
        parts[k]['positions']=[[v.co.x*100,-v.co.y*100,v.co.z*100] for v in ob.data.vertices]
        parts[k]['triangles']=[list(reversed(list(p.vertices))) for p in ob.data.polygons]
        parts[k]['materials']=[p.material_index for p in ob.data.polygons]
        parts[k]['uv']=[[list(ob.data.uv_layers.active.data[i].uv) for i in reversed(list(p.loop_indices))] for p in ob.data.polygons]
refs={k:np.array(v) for k,v in host['reference'].items()}
R=refs['WPN_root'];up=R[:3,2]/np.linalg.norm(R[:3,2])
fwd=refs['WPN_FrontSight'][:3,3]-refs['WPN_RearSight'][:3,3]
fwd-=up*np.dot(fwd,up);fwd/=np.linalg.norm(fwd)
frame=np.eye(4);frame[:3,0]=fwd;frame[:3,1]=np.cross(up,fwd);frame[:3,2]=up;frame[:3,3]=R[:3,3]
mounts={k:frame.copy() for k in keys};mounts[keys[2]][:3,3]=refs['WPN_SOCKET_Muzzle'][:3,3]

def transform(p,m):return np.array(p)@m[:3,:3].T+m[:3,3]
factory_slot=host['slots'].index('M_DW715_Hero_Grip')
factory_faces=[f for f,m in zip(host['triangles'],host['materials']) if m==factory_slot]
canonical=transform(host['positions'],np.linalg.inv(frame))
factory=BVHTree.FromPolygons(canonical.tolist(),factory_faces,all_triangles=True)
report={'assets':manifest,'factory_grip_slot':factory_slot,'protected_grip_region':{},'muzzle':{}}
report['parts_origin']='editable candidate' if '--candidate' in sys.argv else 'saved UE assets'
for k in keys[:2]:
    points=transform(parts[k]['positions'],np.linalg.inv(frame)@mounts[k])
    ds=[factory.find_nearest(Vector(p))[3]*10 for p in points if p[2]>=-7.1]
    report['protected_grip_region'][k]={'samples':len(ds),'maximum_surface_error_mm':max(ds),'mean_error_mm':sum(ds)/len(ds)}

# Read the actual forward-most bore shell at the muzzle; do not infer fit from a whole-gun box.
muzzle_frame=mounts[keys[2]]
gun_at_muzzle=transform(host['positions'],np.linalg.inv(muzzle_frame))
tipverts=[p for p in gun_at_muzzle if -.035<p[0]<.035 and np.linalg.norm(p[1:])<.7]
tip=np.array(tipverts)
if len(tip):
    center=(tip[:,1:].max(axis=0)+tip[:,1:].min(axis=0))/2
    report['muzzle']={'host_tip_sample_count':len(tip),'socket_to_bore_center_offset_mm':(center*10).tolist(),
       'host_tip_axial_range_mm':(np.array([tip[:,0].min(),tip[:,0].max()])*10).tolist(),
       'brake_local_bounds_cm':[np.min(parts[keys[2]]['positions'],axis=0).tolist(),np.max(parts[keys[2]]['positions'],axis=0).tolist()]}

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
with bpy.data.libraries.load(str(O.parent/'DW715_GripBrake_Editable.blend'),link=False) as (src,dst):
    dst.materials=[n for n in src.materials if n.startswith('DW715_')]
partmats={m.name:m for m in dst.materials}
def mat(name,color,metal=0,rough=.5):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m
steel=mat('InspectionSteel',(.50,.52,.55),.9,.22);black=mat('InspectionBlack',(.028,.03,.032),0,.65)
skin=mat('InspectionSkin',(.42,.25,.17),0,.65);brass=mat('InspectionBrass',(.35,.25,.10),.8,.26)

def make(name,data,positions,filter_fn=None):
    keep=[i for i,f in enumerate(data['triangles']) if filter_fn is None or filter_fn(data['slots'][data['materials'][i]])]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata((positions*.01).tolist(),[],[data['triangles'][i] for i in keep]);mesh.update()
    ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob)
    for s in data['slots']:
        material=partmats.get(s)
        if material is None:
            material=brass if 'Ammo' in s else black if any(x in s.lower() for x in ['grip','sight','loader','glove','sleeve']) else skin if any(x in s.lower() for x in ['hand','skin','arm','manny']) else steel
        mesh.materials.append(material)
    uv=mesh.uv_layers.new(name='UV0')
    for p,idx in zip(mesh.polygons,keep):
        p.material_index=data['materials'][idx];p.use_smooth=True
        for li,tex in zip(p.loop_indices,data['uv'][idx]):uv.data[li].uv=tex
    return ob

def deform(data,pose):
    points=np.array(data['positions']);out=np.zeros_like(points)
    matrices={int(i):np.array(pose[n])@np.linalg.inv(np.array(data['reference'][n])) for i,n in data['bones'].items() if n in pose}
    for vi,weights in enumerate(data['weights']):
        for bi,w in weights:out[vi]+=transform(points[vi],matrices[bi])*w
    return out

def penetration(tree,p):
    closest,normal,idx,distance=tree.find_nearest(Vector(p))
    direction=Vector((.217,.941,.261)).normalized();origin=Vector(p);hits=0
    for _ in range(20):
        hit,_,_,_=tree.ray_cast(origin,direction,50)
        if hit is None:break
        hits+=1;origin=hit+direction*.0001
    return distance*10 if hits%2 else 0.

if arms:
    report['hand_clearance']={}
    trees={k:BVHTree.FromPolygons(parts[k]['positions'],parts[k]['triangles'],all_triangles=True) for k in keys[:2]}
    for pose_key,pose_info in poses.items():
        pose=pose_info['bones'];to_gun=np.linalg.inv(np.array(pose['WPN_root'])@np.linalg.inv(R)@frame)
        points=transform(deform(arms,pose),to_gun)
        # Only hand vertices near the grip; compare with the accepted factory grip at the same pose.
        sample=[p for p in points if -9.5<p[0]<2 and abs(p[1])<2.3 and -11.5<p[2]<3]
        baseline=[penetration(factory,p) for p in sample]
        entry={'sample_vertices':len(sample),'factory_max_penetration_mm':max(baseline,default=0)}
        for k,tree in trees.items():
            depth=[penetration(tree,p) for p in sample]
            extra=[d-b for b,d in zip(baseline,depth)]
            worst=sorted(range(len(extra)),key=lambda i:extra[i],reverse=True)[:8]
            entry[k]={'maximum_penetration_mm':max(depth,default=0),
                'new_vertices_over_0_5mm':sum(b<=.5 and d>.5 for b,d in zip(baseline,depth)),
                'maximum_additional_penetration_mm':max(extra,default=0),
                'worst_samples_cm':[list(sample[i])+[extra[i]] for i in worst]}
        report['hand_clearance'][pose_key]=entry

(O/'fit_measurements.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if '--measure' in sys.argv:
    print('DW715_FIT_MEASUREMENTS '+json.dumps({k:v for k,v in report.items() if k!='assets'}),flush=True)
    raise SystemExit(0)

def assemble(grip,pose_key='idle',hands=False):
    for ob in list(scene.objects):
        if ob.type=='MESH':bpy.data.objects.remove(ob,do_unlink=True)
    # Everything is displayed in the gun's current frame; the transforms below reproduce Configure().
    pose=poses[pose_key]['bones'];root_pose=np.array(pose['WPN_root'])
    gun_to_pose=root_pose@np.linalg.inv(R)
    view=np.linalg.inv(gun_to_pose@frame)
    def show(s):
        if s=='M_DW715_Hero_Grip':return False
        if not hands or arms:return s.startswith('M_DW715_') and 'Loader' not in s
        return 'Loader' not in s
    make('Host',host,transform(deform(host,pose),view),show)
    if hands and arms:make('BareArmsV7',arms,transform(deform(arms,pose),view))
    for k in [grip,keys[2]]:
        make(k,parts[k],transform(parts[k]['positions'],view@gun_to_pose@mounts[k]))

scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.render.resolution_x=1500;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.world=bpy.data.worlds.new('FitInspectionWorld');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.055,.064,.078,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
scene.view_settings.view_transform='AgX'
camera_data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',camera_data);scene.collection.objects.link(camera);scene.camera=camera;camera_data.type='ORTHO'
for name,loc,energy,size in [('Key',(.10,.4,.6),45,.6),('Rim',(.2,-.3,.25),30,.4),('Fill',(-.2,.3,.10),15,.4)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size
    ob=bpy.data.objects.new(name,d);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((.06,0,0))-ob.location).to_track_quat('-Z','Y').to_euler()
def capture(name,grip,center,direction,width,pose='idle',hands=False):
    assemble(grip,pose,hands);center=Vector(center)
    camera.location=center+Vector(direction);camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.ortho_scale=width
    scene.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)

capture('rubber_side',keys[0],(.072,0,-.012),(.015,.65,.06),.42)
capture('wood_side',keys[1],(.072,0,-.012),(.015,.65,.06),.42)
capture('grip_joint',keys[1],(-.025,0,-.027),(-.19,.5,.14),.145)
capture('muzzle_joint',keys[1],(.226,0,.043),(.16,.48,.17),.105)
capture('wood_hand_idle',keys[1],(-.005,0,-.04),(-.16,.48,.15),.23,hands=True)
capture('wood_hand_reload',keys[1],(-.015,0,-.025),(.08,.55,.12),.25,pose='reload_insert',hands=True)
(O/'fit_measurements.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DW715_FIT_MEASUREMENTS '+json.dumps({k:v for k,v in report.items() if k!='assets'}),flush=True)
