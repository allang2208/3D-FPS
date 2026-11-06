"""Render the exact current third-person weighted surfaces; no asset edits."""
import json,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent
def mat(q):
    x,y,z,w=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
        [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
        [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=720;scene.render.resolution_y=608;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=.7
scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.show_object_outline=False;scene.display.shading.background_type='WORLD'
scene.world.color=(.045,.05,.06)
cam=bpy.data.objects.new('Inspection camera',bpy.data.cameras.new('Inspection camera'));scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=1.05;cam.data.clip_start=.01
material=bpy.data.materials.new('Neutral surface');material.diffuse_color=(.6,.43,.30,1)
C=np.diag([1,-1,1])
for label in ('Jason','Kaitlin'):
    g=json.loads((P.parents[1]/'ElbowReview'/(label+'-geometry.json')).read_text());d=np.load(P/(label+'-render.npz'))
    names=list(d['names']);idx={n:i for i,n in enumerate(names)}
    v=np.array(g['vertices']);tri=np.array(g['triangles']);groups={};prep=[]
    for i,weights in enumerate(g['weights']):
        for name,weight in weights.items():groups.setdefault(name,[]).append((i,weight))
    for name,weights in groups.items():
        vi=np.array([x[0] for x in weights]);wt=np.array([x[1] for x in weights]);ref=np.array(g['bones'][name])
        prep.append((idx[name],vi,wt,(v[vi]-ref[:3])@mat(ref[3:7])/ref[7:]))
    # Restrict the diagnostic mesh to torso and arms; exposed full-body surfaces are irrelevant.
    tri=tri[(v[tri,2].min(axis=1)>95)]
    mesh=bpy.data.meshes.new(label);mesh.from_pydata((v@C*.01).tolist(),[],tri[:,::-1].tolist());mesh.update()
    obj=bpy.data.objects.new(label,mesh);scene.collection.objects.link(obj);mesh.materials.append(material)
    for poly in mesh.polygons:poly.use_smooth=True
    out=P/'Renders';out.mkdir(exist_ok=True)
    for pose,name in zip(d['poses'],d['labels']):
        vertices=np.zeros_like(v)
        for bone,vi,wt,local in prep:
            b=pose[bone];vertices[vi]+=(local*b[7:]@mat(b[3:7]).T+b[:3])*wt[:,None]
        mesh.vertices.foreach_set('co',(vertices@C*.01).astype('float32').ravel());mesh.update()
        joint_ids=[idx[k+'_'+s] for s in ('r','l') for k in ('upperarm','lowerarm','hand')]
        center=(pose[joint_ids,:3].min(0)+pose[joint_ids,:3].max(0))/2@C*.01
        for view,offset in [('front',(3.,-4.,1.0)),('back',(-3.,4.,.7))]:
            target=Vector(center);cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
            scene.render.filepath=str(out/(label+'_'+str(name)+'_'+view+'.png'))
            bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj,do_unlink=True)
