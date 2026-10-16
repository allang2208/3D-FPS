import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;D=json.loads((O/'capture.json').read_text());V=O/'Preview';V.mkdir(exist_ok=True);W=O/'Working';W.mkdir(exist_ok=True)
key=sys.argv[sys.argv.index('--')+1]
with (O/'Input'/(key+'_host.bin')).open('rb') as f:
 h=json.loads(f.readline());p=np.fromfile(f,'<f4',h['vertices']*3).reshape(-1,3)*np.array([.01,-.01,.01]);t=np.fromfile(f,'<i4',h['triangles']*3).reshape(-1,3);m=np.fromfile(f,'<i4',h['triangles']);ns=np.fromfile(f,'<f4',h['triangles']*9).reshape(-1,3,3)*np.array([1,-1,1])
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
bpy.ops.import_scene.fbx(filepath=D['assets'][key]['fbx']);grip=next(o for o in bpy.context.scene.objects if o.type=='MESH');mat=grip.matrix_world.copy();nm=mat.to_3x3().inverted().transposed();norm=[tuple((nm@n.vector).normalized()) for n in grip.data.corner_normals];grip.data.transform(mat);grip.parent=None;grip.matrix_world=Matrix.Identity(4);grip.data.normals_split_custom_set(norm);grip.name='Current_Phantom'
def mesh(name,ids):
 me=bpy.data.meshes.new(name);me.from_pydata(p,[],t[ids]);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
 for face in me.polygons:face.use_smooth=True
 me.normals_split_custom_set(ns[ids].reshape(-1,3).tolist());return ob
factory=np.isin(m,h['factory_slots']);fac=mesh('Native_Factory_Grip',factory);host=mesh('Current_Receiver',~factory);fac.hide_render=True;fac.hide_set(True)
# Remove unused points before geometric bounds; native factory sections are reference only.
fp=p[np.unique(t[factory])];gp=np.array([tuple(v.co) for v in grip.data.vertices]);gtri=np.array([list(f.vertices) for f in grip.data.polygons]);gm=np.array([f.material_index for f in grip.data.polygons])
np.savez_compressed(W/(key+'.npz'),host_positions=p,host_triangles=t,host_mids=m,factory_slots=np.array(h['factory_slots']),grip_positions=gp,grip_triangles=gtri,grip_mids=gm)
summary={'factory_bounds':[fp.min(0).tolist(),fp.max(0).tolist()],'grip_bounds':[gp.min(0).tolist(),gp.max(0).tolist()],'slots':[m.name for m in grip.data.materials]};(W/(key+'_summary.json')).write_text(json.dumps(summary,indent=2))
def material(name,colour,rough):
 mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(*colour,1);bs.inputs['Metallic'].default_value=.35;bs.inputs['Roughness'].default_value=rough;return mat
grey=material('Receiver diagnostic',(.12,.14,.16),.42);silver=material('Grip diagnostic',(.3,.31,.33),.4);host.data.materials.append(grey)
for i in range(len(grip.data.materials)):grip.data.materials[i]=silver
top=fp[:,2].max();near=fp[fp[:,2]>top-.02];center=Vector(((near[:,0].min()+near[:,0].max())*.5,(near[:,1].min()+near[:,1].max())*.5,top-.022));scale=.155
if key=='Super90':scale=.17
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=1100;scene.render.resolution_y=950;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('Inspection');world.use_nodes=True;scene.world=world;bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.15,.18,.22,1);bg.inputs[1].default_value=.5
def aim(ob):ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
for offset,power,size in [((.24,-.17,.3),20,.3),((.1,.3,.1),12,.3),((-.2,.1,.25),22,.2)]:
 light=bpy.data.objects.new('Studio light',bpy.data.lights.new('Studio light','AREA'));scene.collection.objects.link(light);light.location=center+Vector(offset);light.data.energy=power;light.data.size=size;aim(light)
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);cam.location=center+Vector((.4,.055,.025));cam.data.type='ORTHO';cam.data.ortho_scale=scale;cam.data.clip_start=.001;scene.camera=cam;aim(cam)
scene.render.filepath=str(V/(key+'_before.png'));bpy.ops.render.render(write_still=True);bpy.ops.wm.save_as_mainfile(filepath=str(W/(key+'_assembly.blend')));print('ASSEMBLY_INSPECTED',key,summary,flush=True)
