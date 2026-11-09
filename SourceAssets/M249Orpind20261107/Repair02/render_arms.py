"""Inspect complete skinned arms before and after the native hierarchy repair."""
import pickle
from pathlib import Path
import bpy
import numpy as np
from mathutils import Quaternion,Vector

root=Path(__file__).resolve().parent
project=root.parents[2]
def load(path):
    with path.open("rb") as f:return pickle.load(f)
def mat(t):
    m=np.eye(4);m[:3,:3]=np.asarray(Quaternion((t[6],*t[3:6])).to_matrix())*t[7:];m[:3,3]=t[:3];return m
d=load(project/"Saved/M249ReloadReview/geometry.pkl")
rig=load(root/"before_rig.pkl")
bind=np.asarray([mat(t) for t in d["bind"]])
lookup=dict(zip(d["used"],range(len(d["names"]))))
indices={}
vertices=np.asarray(d["vertices"])
for i,row in enumerate(d["weights"]):
    for b,w in row:indices.setdefault(lookup[b],[]).append((i,w))
skin_groups=[]
for b,pairs in indices.items():
    ids,weight=np.asarray(pairs).T;ids=ids.astype(int)
    skin_groups.append((b,ids,np.c_[vertices[ids],np.ones(len(ids))]*weight[:,None]))
faces=np.asarray(d["faces"])
sections=np.asarray(d["sections"])
materials=d["slots"]
bpy.ops.wm.read_factory_settings(use_empty=True)
mesh=bpy.data.meshes.new("M249")
mesh.from_pydata(vertices.tolist(),[],faces.tolist())
obj=bpy.data.objects.new("M249",mesh);bpy.context.collection.objects.link(obj)
for name in materials:
    m=bpy.data.materials.new(name);m.use_nodes=True
    color=(.5,.29,.18,1) if name.startswith("Skin") else (.09,.26,.3,1) if "Belt" in name else (.045,.05,.055,1)
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=color;bsdf.inputs["Roughness"].default_value=.63
    mesh.materials.append(m)
mesh.polygons.foreach_set("material_index",sections)
mesh.polygons.foreach_set("use_smooth",np.ones(len(faces),dtype=bool))
scene=bpy.context.scene;scene.render.engine="CYCLES";scene.cycles.samples=12
scene.render.resolution_x=800;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new("World");scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.25,.25,.25,1)
for pos,power in (((70,50,100),200000),((-80,-20,50),140000)):
    data=bpy.data.lights.new("Softbox","AREA");data.energy=power;data.size=120
    light=bpy.data.objects.new("Softbox",data);bpy.context.collection.objects.link(light);light.location=pos
    light.rotation_euler=(Vector((0,-20,-10))-light.location).to_track_quat("-Z","Y").to_euler()
camdata=bpy.data.cameras.new("Camera");cam=bpy.data.objects.new("Camera",camdata);bpy.context.collection.objects.link(cam)
scene.camera=cam;camdata.type="ORTHO";camdata.ortho_scale=85;camdata.clip_end=1000
cam.location=(65,45,38);cam.rotation_euler=(Vector((0,-16,-14))-cam.location).to_track_quat("-Z","Y").to_euler()
current=load(root/"before_reload.pkl")
after=np.load(root/"reload_world.npz")
for time in (1.6,4.7,5.6):
    i=round(time*(len(current["frames"])-1)/current["duration"])
    for state in ("before","after"):
        if state=="before":
            row={n:mat(t) for n,t in zip(rig["names"],current["frames"][i])}
            b=mat(rig["bind"][rig["names"].index("WPN_root")])
            g=b@np.linalg.inv(row["WPN_root"])
            worlds=np.asarray([g@row[n] for n in d["names"]])
        else:worlds=np.asarray([after[n][i] for n in d["names"]])
        transforms=worlds@np.linalg.inv(bind)
        points=np.zeros_like(vertices)
        for bone,ids,coords in skin_groups:points[ids]+=coords@transforms[bone,:3,:].T
        hidden="New" if time<3.2 else "Old"
        hideverts=np.unique(faces[np.array(["__"+hidden in materials[m] for m in sections])])
        points[hideverts]=[0,0,-1000]
        mesh.vertices.foreach_set("co",points.astype(np.float32).ravel());mesh.update()
        scene.render.filepath=str(root/(f"arm_{state}_{time:.1f}.png"))
        bpy.ops.render.render(write_still=True)
