"""Skinned native body review for the reported third-person clipping issue."""
import json,sys
from pathlib import Path
import numpy as np,bpy
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;R=O.parents[1]
data=json.loads((O/'authored_body.json').read_text());skin=json.loads((O/'body_geometry.json').read_text());rig=json.loads((O/'body_rig.json').read_text())
names=data['names'];parents=data['parents'];ix={n:i for i,n in enumerate(names)}
if names!=rig['names'] or not np.allclose(data['reference'],rig['reference'],atol=1e-4):raise RuntimeError('Native body binding differs from authoring source')
def mat(t):
    m=Quaternion((t[6],t[3],t[4],t[5])).to_matrix().to_4x4();m.translation=Vector(t[:3]);return m
def world(f):
    result=[]
    for i,t in enumerate(f):result.append(result[parents[i]]@mat(t) if parents[i]>=0 else mat(t))
    return result
rest=world(data['reference']);inv=[m.inverted() for m in rest];p=np.column_stack((skin['positions'],np.ones(len(skin['positions']))));weights={n:np.array([w.get(n,0) for w in skin['weights']]) for n in names};weights={n:w for n,w in weights.items() if np.any(w)}
geo=json.loads((R/'SourceAssets/LargeLamb20261014/large-lamb-geometry.json').read_text());report={}
def under(n,root):
    i=ix[n]
    while i>=0:
        if names[i]==root:return True
        i=parents[i]
    return False
armids={s:np.where(sum((w for n,w in weights.items() if under(n,'upperarm_'+s)),np.zeros(len(p)))>.8)[0] for s in ['l','r']}
bodyweight=sum((w for n,w in weights.items() if n.startswith(('spine_','pelvis','neck_','head'))),np.zeros(len(p)))
bodyfaces=[f for f in skin['triangles'] if all(bodyweight[j]>.8 for j in f)]
def material(name,color):m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
def mesh(name,verts,faces,color):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(material(name,color))
    for f in me.polygons:f.use_smooth=True
    return ob
for seconds in [.55,1.65,2.75,4.65,5.3]:
    f=data['frames'][round(seconds*60)];pose=world(f);out=np.zeros((len(p),3))
    for n,w in weights.items():out+=(p@np.array(pose[ix[n]]@inv[ix[n]]).T)[:,:3]*w[:,None]
    bvh=BVHTree.FromPolygons([Vector(v) for v in out],bodyfaces)
    row={}
    for side in ['l','r']:
        # The native torso has open sockets and UE triangle winding. Measure
        # unsigned separation and exact edge/surface crossings, not a normal-
        # signed distance that mistakes outside vertices for deep penetration.
        hand=pose[ix['hand_'+side]].translation;elbow=pose[ix['lowerarm_'+side]].translation
        ids=[i for i in armids[side] if sum(skin['weights'][i].get(n,0) for n in ['lowerarm_'+side,'hand_'+side])>.5]
        distances=[]
        for i in ids:
            near,normal,_,dist=bvh.find_nearest(Vector(out[i]));distances.append(dist)
        selected=set(ids);edges=set()
        for face in skin['triangles']:
            if all(i in selected for i in face):
                edges.update(tuple(sorted((face[j],face[(j+1)%3]))) for j in range(3))
        crosses=0
        for a,b in edges:
            origin=Vector(out[a]);delta=Vector(out[b])-origin;length=delta.length
            if length<.001:continue
            hit,_,_,distance=bvh.ray_cast(origin+delta.normalized()*.0001,delta.normalized(),length-.0002)
            if hit is not None:crosses+=1
        row[side]=dict(forearm_hand_to_torso_min_cm=float(min(distances)),forearm_hand_edge_torso_crossings=crosses,wrist=list(hand),elbow=list(elbow))
    report[str(seconds)]=row
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    mesh('Actual Jason body',out.tolist(),skin['triangles'],(.48,.34,.26))
    # The runtime prop is attached to the achieved left hand, matching Sample.Props.
    ob=pose[ix['hand_l']]@Matrix(data['hand_in_food']['l']).inverted()
    meat=mesh('Actual large lamb',[list(ob@Vector(v)) for v in geo['vertices']],geo['faces'],(.27,.12,.04))
    scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('Review world');scene.world.color=(.055,.055,.055);scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.view_settings.view_transform='Standard'
    camera=bpy.data.objects.new('Body review camera',bpy.data.cameras.new('Body review camera'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=112
    center=Vector((0,10,126))
    for label,offset in [('front',(0,180,5)),('side',(160,30,6))]:
        camera.location=center+Vector(offset);camera.rotation_euler=(-Vector(offset)).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/f'body_{seconds:.2f}_{label}.png');bpy.ops.render.render(write_still=True)
    if seconds==2.75:bpy.ops.wm.save_as_mainfile(filepath=str(O/'LargeLamb_BodyReview.blend'))
(O/'body_surface_review.json').write_text(json.dumps(report,indent=2));print('LAMB_BODY_REVIEW_RECORDED')
