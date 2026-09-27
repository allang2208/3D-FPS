"""Author thin, source-fitted game grip treatments and physical-scale textures."""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;T=O/'Textures';E=O/'Exports'
T.mkdir(exist_ok=True);E.mkdir(exist_ok=True)
SOURCE=O.parent/'M1911RearRain20260913/M1911_RearFinish_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_M1911_Manny'];rig.data.pose_position='REST'
bpy.context.view_layer.update();root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
def activate(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
def source_bvh(name):
    ob=bpy.data.objects[name];xf=root.inverted()@ob.matrix_world
    return BVHTree.FromPolygons([xf@v.co for v in ob.data.vertices],[list(p.vertices) for p in ob.data.polygons])
verts=[];faces=[];uvs=[];fits=[]
def patch(name,bvh,side):
    # Rounded islands stop between the original screws; front strap stops below guard.
    is_side=side!=0;segments=64;rings=10
    center_z=-.044 if is_side else -.063
    half_z=.030 if is_side else .022
    half_u=.0108 if is_side else .006
    first=len(verts);locations=[];normals=[]
    for ring in range(rings+1):
        count=1 if ring==0 else segments;r=ring/rings
        for k in range(count):
            a=k*math.tau/segments
            sx=math.copysign(abs(math.cos(a))**.5,math.cos(a))
            sy=math.copysign(abs(math.sin(a))**.5,math.sin(a))
            z=center_z+half_z*r*sy
            u=half_u*r*sx
            y=.0174-.354*z+u
            start=Vector((side*.04,y,z)) if is_side else Vector((u,-.15,z))
            direction=Vector((-side,0,0)) if is_side else Vector((0,1,0))
            hit,normal,_,_=bvh.ray_cast(start,direction)
            if hit is None:raise RuntimeError('Surface fitting ray missed '+name+' '+str(list(start)))
            if normal.dot(direction)>0:normal=-normal
            # Hair-thin adhesive edge, raised rubber center. Never move the gun.
            offset=.00009+.00023*min(1.,(1.-r)*5.)
            locations.append(hit);normals.append(normal)
            verts.append(tuple(hit+normal*offset))
            uvs.append(((y+.354*z)/.1,z/.1) if is_side else (u/.1,z/.1))
    def idx(r,k):return first if r==0 else first+1+(r-1)*segments+k%segments
    for k in range(segments):faces.append((idx(0,0),idx(1,k),idx(1,k+1)))
    for r in range(1,rings):
        for k in range(segments):faces.append((idx(r,k),idx(r+1,k),idx(r+1,k+1),idx(r,k+1)))
    # Border and recessed back close the wafer without lifting its visible edge.
    underside=[]
    for k in range(segments):
        outer=idx(rings,k);local=outer-first
        underside.append(len(verts));verts.append(tuple(locations[local]+normals[local]*.000025));uvs.append(uvs[outer])
    for k in range(segments):faces.append((idx(rings,k),underside[k],underside[(k+1)%segments],idx(rings,k+1)))
    faces.append(tuple(reversed(underside)))
    fits.append({'surface':name,'vertices':len(verts)-first,'edge_offset_m':.00009,'center_offset_m':.00032})
patch('right wood panel',source_bvh('M1911_RightWoodPanel'),1)
patch('left wood panel',source_bvh('M1911_LeftWoodPanel'),-1)
patch('frame front strap',source_bvh('M1911_Frame'),0)
mesh=bpy.data.meshes.new('M1911_GripSurface_SourceFit');mesh.from_pydata(verts,[],faces);mesh.update()
uv=mesh.uv_layers.new(name='Physical10cm')
for poly in mesh.polygons:
    for li in poly.loop_indices:uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
for p in mesh.polygons:p.use_smooth=True
surface=bpy.data.objects.new('SM_M1911_GripSurface',mesh);scene.collection.objects.link(surface)

# Original factory grip retained only as a separate icon authoring object.
factory=[]
for name in ['M1911_LeftWoodPanel','M1911_RightWoodPanel']:
    src=bpy.data.objects[name];ob=src.copy();ob.data=src.data.copy();scene.collection.objects.link(ob)
    xf=root.inverted()@src.matrix_world;ob.parent=None;ob.modifiers.clear();ob.matrix_world=Matrix.Identity(4);ob.data.transform(xf)
    factory.append(ob)
activate(factory);bpy.ops.object.join();factory=factory[0];factory.name='SM_M1911_FactoryGripIcon'

# 10 cm seamless tiles, shallow physical relief; no per-grain geometry.
N=1024;yy,xx=np.mgrid[0:N,0:N].astype(np.float32);x=xx/N*.1;y=yy/N*.1
rng=np.random.default_rng(19110927)
noise=rng.random((N,N),dtype=np.float32)
def periodic_grains(cells):
    gx=xx/N*cells;gy=yy/N*cells;ix=np.floor(gx).astype(int);iy=np.floor(gy).astype(int)
    jitter=rng.random((cells,cells,2),dtype=np.float32)
    dist=np.full((N,N),100.,dtype=np.float32)
    for dy in [-1,0,1]:
        for dx in [-1,0,1]:
            ox=jitter[(iy+dy)%cells,(ix+dx)%cells,0];oy=jitter[(iy+dy)%cells,(ix+dx)%cells,1]
            dist=np.minimum(dist,(gx-(ix+dx+ox))**2+(gy-(iy+dy+oy))**2)
    return np.exp(-dist*8.)
grain=periodic_grains(120)
diamond=np.maximum(0,np.minimum(np.abs(np.sin(math.pi*(x+y)/.0025)),np.abs(np.sin(math.pi*(x-y)/.0025)))-.13)/.87
dot_r=np.sqrt(((x/.00125+.5)%1-.5)**2+((y/.00125+.5)%1-.5)**2)
dots=np.clip((.32-dot_r)/.15,0,1)
surfaces={
 'pistol_grip_granular':(grain*.000115+noise*.000008,.024,.79),
 'pistol_grip_diamond':(diamond*.00018+noise*.000004,.019,.72),
 'pistol_grip_quickdot':(dots*.00007+noise*.000003,.028,.66)}
textures={};materials={}
for key,(height,base,rough) in surfaces.items():
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(.2/N)
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(.2/N)
    normal=np.stack([-dx,-dy,np.ones_like(dx)],axis=-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
    tone=base*(.83+.30*noise+.20*height/max(float(height.max()),1e-6))
    color=np.stack([tone*.94,tone*.98,tone],axis=-1)
    # Blender image pixels are linear; saving the sRGB image applies encoding.
    orm=np.stack([.93+.07*height/max(float(height.max()),1e-6),np.clip(rough+(noise-.5)*.08,0,1),np.zeros_like(noise)],axis=-1)
    textures[key]={};images={}
    for kind,arr in [('BaseColor',color),('ORM',orm),('Normal',normal*.5+.5)]:
        im=bpy.data.images.new('T_'+key+'_'+kind,N,N,alpha=False,float_buffer=False)
        im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
        rgba=np.concatenate([arr,np.ones((N,N,1),dtype=np.float32)],axis=-1).astype(np.float32)
        im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(T/(im.name+'.png'));im.file_format='PNG';im.save()
        images[kind]=im;textures[key][kind]=im.filepath_raw
    mat=bpy.data.materials.new('M_'+key);mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links
    bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    for kind,im in images.items():
        tx=nodes.new('ShaderNodeTexImage');tx.image=im
        if kind=='BaseColor':links.new(tx.outputs[0],bs.inputs['Base Color'])
        elif kind=='Normal':
            nm=nodes.new('ShaderNodeNormalMap');nm.uv_map='Physical10cm';links.new(tx.outputs[0],nm.inputs['Color']);links.new(nm.outputs[0],bs.inputs['Normal'])
        else:
            sep=nodes.new('ShaderNodeSeparateColor');links.new(tx.outputs[0],sep.inputs[0]);links.new(sep.outputs[1],bs.inputs['Roughness']);links.new(sep.outputs[2],bs.inputs['Metallic'])
    mat.use_fake_user=True;materials[key]=mat
surface.data.materials.append(materials['pistol_grip_granular'])
for ob in list(scene.objects):
    if ob not in [surface,factory]:bpy.data.objects.remove(ob,do_unlink=True)
for ob in [surface,factory]:ob.data.transform(root)
factory.hide_render=True;factory.hide_set(True)
activate([surface]);tri=surface.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_GripSurface_Editable.blend'))
record={'source':str(SOURCE),'root_matrix':[list(row) for row in root],'fits':fits,'textures':textures,
 'mesh':'/Game/Weapons/PistolGripSurface20260927/M1911/SM_M1911_GripSurface','bone':'WPN_root',
 'texture_tile_m':.1,'provenance':'Original procedural rubber textures and thin derivative fit to the accepted local M1911 game mesh; no external artwork',
 'game_tested':False}
for ob in list(scene.objects):
    if ob!=surface:bpy.data.objects.remove(ob,do_unlink=True)
group=bpy.data.objects.new('SM_M1911_GripSurface',None);scene.collection.objects.link(group);group['fbx_type']='LodGroup'
surface.name='SM_M1911_GripSurface_LOD0';surface.parent=group;levels=[surface]
for i,ratio in [(1,.5),(2,.25)]:
    part=surface.copy();part.data=surface.data.copy();part.name='SM_M1911_GripSurface_LOD'+str(i);scene.collection.objects.link(part)
    activate([part]);mod=part.modifiers.new('Distant surface reduction','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name);levels.append(part)
activate([group]+levels)
bpy.ops.export_scene.fbx(filepath=str(E/'SM_M1911_GripSurface.fbx'),use_selection=True,object_types={'MESH','EMPTY'},
 axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,use_custom_props=True)
record['lods']=[len(x.data.polygons) for x in levels]
(O/'authoring.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_GripSurface_LODs.blend'))
print('PISTOL_GRIP_SURFACE_AUTHORED',flush=True)
