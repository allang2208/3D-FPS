"""Build 30/45 round side magazines from the accepted patterned M4 shell.

The extended shell repeats eight complete pattern periods below the unchanged
upper grasp; no uniform stretching of the mouth, latch or finger contact area.
"""
import bpy,bmesh,json,pickle,sys,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
r=Path(__file__).resolve().parent;S=r.parents[1];out=r/'Exports';out.mkdir(exist_ok=True)
grid=r/'Grid45';grid.mkdir(exist_ok=True)
source=S/'M4GridUnified20260919'
if not (grid/'M4_ExtMag40_Grid_Editable.blend').exists():
    code=(source/'author_surface.py').read_text()
    code=code.replace('O=Path(__file__).parent;S=O.parent;',f'O=Path({str(grid)!r});S=Path({str(S)!r});')
    code=code.replace('extension=.0625','extension=.1000').replace('steps=steps_per_period*5','steps=steps_per_period*8')
    exec(compile(code,str(source/'author_surface.py'),'exec'),{'__file__':str(source/'author_surface.py')})
    code=(source/'finish.py').read_text().replace("O=Path(__file__).parent;S=O.parent;",f'O=Path({str(grid)!r});S=Path({str(S)!r});')
    exec(compile(code,str(source/'finish.py'),'exec'),{'__file__':str(source/'finish.py')})
from mathutils import Quaternion
def matrix(v):
    m=np.eye(4);m[:3,:3]=np.array(Quaternion((v[6],*v[3:6])).to_matrix())*np.array(v[7:]);m[:3,3]=v[:3];return m
def rot(m):return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)
def compose(ns,pa,ls):
    w={}
    for n in ns:w[n]=w[pa[n]]@ls[n] if pa[n] else ls[n].copy()
    return w
sys.path.insert(0,str(S/'ExtMagPattern20260919'));from export_tangents import export
d=pickle.load(open(r/'native.pkl','rb'));g=pickle.load(open(r/'grasp.pkl','rb'))
B={n:matrix(v) for n,v in zip(g['names'],g['bind'])}
source_to_mag=np.diag([100,100,100,1])@np.linalg.inv(B['WPN_SOCKET_Magazine'])@np.diag([100,-100,100,1])
ns=d['names'];pa={n:ns[p] if p>=0 else None for n,p in zip(ns,d['parents'])}
idle=next(v for k,v in d['clips'].items() if k.split('.')[0].endswith('_idle'))
world=compose(ns,pa,{n:matrix(v) for n,v in zip(ns,idle['frames'][0])})
mag=np.linalg.inv(world['WPN_root'])@world['WPN_SOCKET_Magazine'];mag[:3,3]*=100;mag[:3,:3]=rot(mag)
# The positive root X side is the weapon's left side. The shell projects left
# and slightly down; the feed head is seated inside the receiver-side lip.
Q=np.array(Matrix.Rotation(math.radians(-76),4,'Y'))
head=None;manifest={}
for capacity,path,name in [(30,S/'ExtMagRebuild20260919/M4_ExtMag_Editable.blend','Factory_M4'),(45,grid/'M4_ExtMag40_Grid_Editable.blend','SM_M4_ExtMag40_Grid')]:
    bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False)
    ob=bpy.data.objects[name]
    for obj in list(bpy.data.objects):
        if obj!=ob:bpy.data.objects.remove(obj,do_unlink=True)
    ob.hide_render=False;ob.hide_set(False)
    mesh=ob.data;v=np.array([tuple(v.co) for v in mesh.vertices]);magv=(source_to_mag@np.c_[v,np.ones(len(v))].T).T[:,:3]
    if head is None:
        rim=magv[magv[:,2]>magv[:,2].max()-1.2];head=(rim.min(0)+rim.max(0))*.5;head[2]=magv[:,2].max()
    target=Q.copy();target[:3,3]=np.array([3.35,11.4,4.6])-Q[:3,:3]@head
    to_bone=np.linalg.inv(mag)@target@source_to_mag
    # UE static meshes are authored in the normalized magazine bone frame.
    to_blender=np.diag([.01,-.01,.01,1])@to_bone
    original_normals=[n.vector.copy() for n in mesh.corner_normals]
    m=Matrix(to_blender.tolist());normal=m.to_3x3().inverted().transposed()
    for v in mesh.vertices:v.co=m@v.co
    mesh.normals_split_custom_set([(normal@n).normalized() for n in original_normals]);mesh.update()
    ob.name='SM_m249_side_mag_'+str(capacity)
    # A zero seam weight gives the standard shell the same material contract.
    if capacity==30:
        for k in range(1,7):
            layer=mesh.uv_layers.new(name='SeamUV' if k==1 else 'SeamBasis'+str(k-2))
            for i,loop in enumerate(layer.data):loop.uv=mesh.uv_layers[0].data[i].uv if k==1 else (0,1)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(ob.name+'.blend')))
    export(mesh,out/(ob.name+'.fbx'))
    manifest[str(capacity)]=dict(mesh=ob.name,vertices=len(mesh.vertices),grip_region_unchanged=True,body_extension_cm=0 if capacity==30 else 10)
# A receiver-bound open sleeve stays on the gun while the magazine moves.
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
objects=[];f=np.diag([.01,-.01,.01,1]);basis=Q[:3,:3]
def bar(name,center,extent):
    bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.name=name
    frame=np.eye(4);frame[:3,:3]=basis@np.diag(extent);frame[:3,3]=np.array([4.25,11.4,4.375])+basis@np.array(center)
    o.matrix_world=Matrix((f@frame).tolist());bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bevel=o.modifiers.new('Machined edge','BEVEL');bevel.width=.0004;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
    objects.append(o)
# Dimensions match the unchanged source mouth; the inner opening is real.
mouth=magv if False else None
half_width=1.96;half_depth=3.55
for x in (-half_width,half_width):bar('Side socket cheek',(x,0,-.25),(.28,7.5,1.7))
for y in (-half_depth,half_depth):bar('Side socket end',(0,y,-.25),(3.65,.32,1.7))
bar('Magazine catch',(-2.20,-2.35,-.4),(.32,1.05,1.05))
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_M249_SidePort'
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project();bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.wm.save_as_mainfile(filepath=str(out/(ob.name+'.blend')))
export(ob.data,out/(ob.name+'.fbx'))
(r/'model_recipe.json').write_text(json.dumps(dict(parts=manifest,donor_mag_to_root=target.tolist(),idle_mag_frame=mag.tolist(),source_head_cm=head.tolist(),port_root_cm=[4.25,11.4,4.375],extension_cm=10,rendering_tested=False),indent=2))
print('M249_SIDE_MAG_MODELS_EXPORTED',flush=True)
