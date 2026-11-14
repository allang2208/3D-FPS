"""Triangulate the sampled finish with refined rows at the cast joints. All dimensions are in cm."""
from pathlib import Path
import bpy,numpy as np
r=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
depth=np.load(r/'wall-depth.npy');y0,y1=-548.,-116.;z0,z1=86.8,319.55
def axis(lo,hi,pitch,joints,details):
    grid=list(np.arange(lo,hi,pitch))+[lo,hi]
    for j in joints:grid.extend([j-.95,j-.39,j,j+.39,j+.95])
    for a,b in details:grid.extend(np.arange(a,b,1.85))
    return np.array(sorted({round(v,3) for v in grid if lo<=v<=hi}))
ys=axis(y0,y1,4.3,[-402,-429,-265,-278],[(-412,-378),(-269,-252)])
zs=axis(z0,z1,4.3,[200],[(173,207),(124,144)])
y,z=np.meshgrid(ys,zs)
u=(y-y0)/(y1-y0);v=(z-z0)/(z1-z0)
ix=np.clip(np.rint(u*(depth.shape[1]-1)).astype(int),0,depth.shape[1]-1)
iz=np.clip(np.rint((1-v)*(depth.shape[0]-1)).astype(int),0,depth.shape[0]-1)
front=depth[iz,ix].copy()
for bottom,lines in [(True,[-402,-265]),(False,[-429,-278])]:
    mask=z<200 if bottom else z>=200
    for line in lines:front[mask]-=.54*np.exp(-((y[mask]-line)/.50)**2)
front-=.48*np.exp(-((z-200)/.55)**2)
verts=[(x/100,-(yy+332)/100,zz/100) for x,yy,zz in zip(front.flat,y.flat,z.flat)]
uvs=list(zip(u.flat,v.flat));rows,cols=y.shape;faces=[]
for j in range(rows-1):
    for i in range(cols-1):
        k=j*cols+i
        faces.extend([(k,k+cols,k+cols+1),(k,k+cols+1,k+1)])
# Return thin edge to the original wall at the two ends of the bay.
for i in [0,cols-1]:
    idx=list(range(i,rows*cols,cols));back=[]
    for k in idx:
        x,yy,zz=verts[k];back.append(len(verts));verts.append((-.001,yy,zz));uvs.append(uvs[k])
    for j in range(rows-1):
        s=(idx[j],back[j],back[j+1],idx[j+1]);faces.append(s if i==0 else s[::-1])
mesh=bpy.data.meshes.new('SM_CastBayFace');mesh.from_pydata(verts,[],faces);mesh.update()
obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj)
maplayer=mesh.uv_layers.new(name='RegisteredBay')
for f in mesh.polygons:
    f.use_smooth=len(f.vertices)==3
    for k in f.loop_indices:maplayer.data[k].uv=uvs[mesh.loops[k].vertex_index]
mesh.materials.append(bpy.data.materials.new('CastMineral'))
obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(r/'SM_CastBayFace.fbx'),use_selection=True,axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
