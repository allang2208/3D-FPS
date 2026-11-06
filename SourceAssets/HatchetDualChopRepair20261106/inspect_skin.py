"""Scoped elbow inspection using the previously exported V9 weighted mesh."""
import json,math,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
# Blender has NumPy but no SciPy; consume already-authored world-space samples.
d=np.load(P/'inspection-poses.npz');names=list(d['names']);idx={n:i for i,n in enumerate(names)}
g=json.loads((P.parent/'OneHandAxe20261101/FalconEdge20261103/SwiftFalconLegendary/HeavyPull/R2/geometry.json').read_text())['skins']['Arms']
def mat(q):
    x,y,z,w=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
v=np.array(g['vertices']);tri=np.array(g['triangles']);groups={};prep=[]
for i,weights in enumerate(g['weights']):
    for name,weight in weights.items():
        if name in idx:groups.setdefault(name,[]).append((i,weight))
for name,weights in groups.items():
    vi=np.array([x[0] for x in weights]);wt=np.array([x[1] for x in weights]);ref=np.array(g['bones'][name])
    prep.append((idx[name],vi,wt,(v[vi]-ref[:3])@mat(ref[3:7])/ref[7:]))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;C=np.diag([1,-1,1]);mesh=bpy.data.meshes.new('V9 skin')
mesh.from_pydata((v@C*.01).tolist(),[],tri[:,::-1].tolist());mesh.update()
obj=bpy.data.objects.new('Exact weighted V9 surface',mesh);scene.collection.objects.link(obj)
for poly in mesh.polygons:poly.use_smooth=True
material=bpy.data.materials.new('Diagnostic skin');material.diffuse_color=(.57,.37,.27,1);material.use_nodes=True
material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.57,.37,.27,1)
material.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.72
mesh.materials.append(material)
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.32,.38,.45,1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.8
sun=bpy.data.objects.new('Key',bpy.data.lights.new('Key','SUN'));sun.data.energy=3;sun.rotation_euler=(.8,-.35,.5);scene.collection.objects.link(sun)
cam=bpy.data.objects.new('View',bpy.data.cameras.new('View'));scene.collection.objects.link(cam);scene.camera=cam
cam.data.sensor_fit='VERTICAL';cam.data.angle_y=math.radians(75);cam.data.clip_start=.02
cam.matrix_world=Matrix(((1,0,0),(0,0,-1),(0,1,0))).to_4x4()
(P/'Inspection').mkdir(exist_ok=True)
for pose,label in zip(d['poses'],d['labels']):
    vertices=np.zeros_like(v)
    for bone,vi,weight,local in prep:
        b=pose[bone];vertices[vi]+=(local*b[7:]@mat(b[3:7]).T+b[:3])*weight[:,None]
    mesh.vertices.foreach_set('co',(vertices@C*.01).astype('float32').ravel());mesh.update()
    scene.render.filepath=str(P/'Inspection'/f'{label}.png');bpy.ops.render.render(write_still=True)
