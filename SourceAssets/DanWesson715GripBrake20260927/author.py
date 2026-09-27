"""Original game attachments fitted to the accepted DW715 source; no gameplay previews.

Only the transparent grayscale attachment icons are rendered for the shipped UI.
"""
import bpy, bmesh, json, math, shutil
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

O=Path(__file__).parent
ICONS=O.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'
T=O/'Textures';T.mkdir(exist_ok=True)
try:
    bpy.ops.wm.open_mainfile(filepath=str(O.parent/'DanWesson715MetalFinish20260914/DanWesson715_MetalFinish_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
rig=bpy.data.objects['SK_DW715_Manny']
inv=rig.data.bones['WPN_root'].matrix_local.inverted()
source=bpy.data.objects['DW715_RubberGrip'].data.copy()
source.transform(inv)
# Same forward/up frame as the accepted 715 optic fitting pipeline.
to_aim=Matrix(((0,-1,0,0),(1,0,0,0),(0,0,1,0),(0,0,0,1)))
source.transform(to_aim)
source_vertices=[tuple(v.co) for v in source.vertices]
source_faces=[tuple(p.vertices) for p in source.polygons]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
report={'source':'DanWesson715MetalFinish20260914/DanWesson715_MetalFinish_Editable.blend',
        'frame':'Blender +X forward, +Z up; exported UE +X forward; grip pivot WPN_root, brake pivot WPN_SOCKET_Muzzle',
        'factory_grip_slot':'M_DW715_Hero_Grip','parts':{},'textures':{}}

def texture(name,arr,color=False):
    image=bpy.data.images.new(name,width=arr.shape[1],height=arr.shape[0],alpha=True)
    image.colorspace_settings.name='sRGB' if color else 'Non-Color'
    rgba=np.ones((*arr.shape[:2],4),dtype=np.float32);rgba[:,:,:3]=np.clip(arr,0,1)
    image.pixels.foreach_set(rgba.ravel());image.filepath_raw=str(T/(name+'.png'));image.file_format='PNG';image.save()
    return image

N=2048
v,u=np.mgrid[0:N,0:N].astype(np.float32)/N
# Seamless 10 cm physical tiles. Geometry carries the silhouette; these carry fine surface finish.
wave=np.sin(2*np.pi*(u*37+.26*np.sin(v*2*np.pi*3)))
micro=np.sin(u*2*np.pi*347)*np.sin(v*2*np.pi*331)
grain=np.sin(2*np.pi*(u*74+1.4*np.sin(v*2*np.pi)+.31*np.sin(v*2*np.pi*3)))
grain2=np.sin(2*np.pi*(u*171+.7*np.sin(v*2*np.pi*2)))
diamond=(1-np.abs(np.sin((u+v)*2*np.pi*38)))*(1-np.abs(np.sin((u-v)*2*np.pi*38)))
pebble=(np.sin(u*2*np.pi*153+.65*np.sin(v*2*np.pi*71))*np.sin(v*2*np.pi*149+.5*np.sin(u*2*np.pi*43))*.5+.5)**2
specs={
 'Rubber':(np.stack([.031+pebble*.009]*3,-1),.76-pebble*.08,pebble*.00009+micro*.000006,0),
 'RubberCheckered':(np.stack([.037+diamond*.012]*3,-1),.83-diamond*.09,diamond*.00020+pebble*.00004,0),
 'Walnut':(np.stack([.19+grain*.052+grain2*.013,.067+grain*.020+grain2*.005,.027+grain*.009],-1),.37+grain*.035,grain2*.000007,0),
 'WalnutCheckered':(np.stack([.14+grain*.037+diamond*.015,.048+grain*.015,.019+grain*.006],-1),.48+diamond*.07,diamond*.00020+grain2*.000006,0),
 'Steel':(np.stack([.58+micro*.004]*3,-1),.20+wave*.012,micro*.0000007,1),
 'DarkSteel':(np.stack([.053+micro*.002]*3,-1),.30+wave*.012,micro*.0000007,1),
}
materials={}
for key,(color,rough,height,metal) in specs.items():
    dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(.2/N)
    dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(.2/N)
    normal=np.stack([-dx,-dy,np.ones_like(dx)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    bc=texture('T_DW715_'+key+'_BaseColor',color,True)
    nm=texture('T_DW715_'+key+'_NormalGL',normal*.5+.5)
    orm=texture('T_DW715_'+key+'_ORM',np.stack([np.ones_like(rough),rough,np.full_like(rough,metal)],-1))
    report['textures'][key]={k:str(T/(im.name+'.png')) for k,im in [('BaseColor',bc),('Normal',nm),('ORM',orm)]}
    mat=bpy.data.materials.new('DW715_'+key);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF')
    bs.inputs['Metallic'].default_value=metal
    for im,target in [(bc,'Base Color'),(nm,'Normal'),(orm,'Roughness')]:
        tex=nodes.new('ShaderNodeTexImage');tex.image=im
        if target=='Normal':
            norm=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],norm.inputs['Color']);links.new(norm.outputs['Normal'],bs.inputs[target])
        elif target=='Roughness':
            separate=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],separate.inputs['Color']);links.new(separate.outputs['Green'],bs.inputs[target])
        else:links.new(tex.outputs['Color'],bs.inputs[target])
    materials[key]=mat

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob

def planar_uv(ob):
    uv=ob.data.uv_layers.new(name='Physical10cm')
    for p in ob.data.polygons:
        axis=max(range(3),key=lambda a:abs(p.normal[a]))
        # Side faces: grain runs along Z. Front/back: also preserve vertical grain.
        axes=(0,2) if axis==1 else (1,2) if axis==0 else (0,1)
        for li in p.loop_indices:
            co=ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv=(co[axes[0]]/.1,co[axes[1]]/.1)

def grip(key,wood=False):
    mesh=bpy.data.meshes.new(key);mesh.from_pydata(source_vertices,[],source_faces);mesh.update()
    ob=bpy.data.objects.new(key,mesh);bpy.context.collection.objects.link(ob)
    mesh.materials.append(materials['Walnut' if wood else 'Rubber'])
    mesh.materials.append(materials['WalnutCheckered' if wood else 'RubberCheckered'])
    if wood:
        # Explicit loops stop deformation of a long lower-side face from reaching
        # the support palm above the heel, even when its corner remains unchanged.
        bm=bmesh.new();bm.from_mesh(mesh)
        for height in [-.091,-.094]:
            bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                dist=.000001,plane_co=(0,0,height),plane_no=(0,0,1),clear_inner=False,clear_outer=False)
        for rear in [-.079,-.081]:
            bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                dist=.000001,plane_co=(rear,0,0),plane_no=(1,0,0),clear_inner=False,clear_outer=False)
        bm.to_mesh(mesh);bm.free()
    for vert in mesh.vertices:
        # Retain the complete source installation neck and hand-contact band.
        # Continuous lower flare is part of the grip shell, with no added seam.
        if wood:
            # The support palm sits under the front/middle of the grip. Enlarge
            # only the exposed rear heel; keep the factory floor and contact band.
            t=max(0,min(1,(-vert.co.z-.091)/.005734));t=t*t*(3-2*t)
            heel=max(0,min(1,(-vert.co.x-.079)/.005592));heel=heel*heel*(3-2*heel)
            t*=heel
            vert.co.y*=1+t*.35
            vert.co.x-=t*.009
    mesh.update()
    for p in mesh.polygons:
        p.use_smooth=True
        # Recess-like checkering bounded by smooth edges and an untextured mounting neck.
        c=p.center
        p.material_index=int(abs(p.normal.y)>.72 and -.084<c.z<-.018 and -.068<c.x<-.012)
    planar_uv(ob)
    return ob

def lathe(name,profile,mat,segments=96):
    # Profiles close around a visible bore; model dimensions only, not fabrication geometry.
    vertices=[];faces=[]
    for x,r in profile:
        for i in range(segments):
            a=2*math.pi*i/segments;vertices.append((x,math.cos(a)*r,math.sin(a)*r))
    for row in range(len(profile)):
        nxt=(row+1)%len(profile)
        for i in range(segments):
            j=(i+1)%segments;faces.append((row*segments+i,row*segments+j,nxt*segments+j,nxt*segments+i))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(mat)
    # Consistent outward normals after profile construction and booleans.
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    for p in mesh.polygons:p.use_smooth=True
    return ob

rubber=grip('dw715_rubber_grip')
wood=grip('dw715_target_wood_grip',True)
factory=grip('factory_grip')
for vert,co in zip(factory.data.vertices,source_vertices):vert.co=co
factory.data.update()
# The rear shoulder overlays the existing game's muzzle-nut area without hiding barrel sections.
brake=lathe('dw715_muzzle_brake',[
 (-.0005,.0058),(.001,.0072),(.004,.0072),(.005,.0095),(.006,.0100),
 (.030,.0100),(.033,.0088),(.034,.0080),(.034,.00465),(-.0005,.00465)],materials['Steel'])
select(brake)
for x in [.012,.022]:
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,0,0))
    cutter=bpy.context.object;cutter.data.materials.append(materials['Steel']);cutter.dimensions=(.006,.032,.009);select(cutter);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bevel=cutter.modifiers.new('PortCorner','BEVEL');bevel.width=.0012;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
    select(brake);cut=brake.modifiers.new('PairedSidePorts','BOOLEAN');cut.operation='DIFFERENCE';cut.solver='EXACT';cut.object=cutter;bpy.ops.object.modifier_apply(modifier=cut.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
select(brake);bevel=brake.modifiers.new('MachinedEdges','BEVEL');bevel.width=.00028;bevel.segments=3;bevel.limit_method='ANGLE';bpy.ops.object.modifier_apply(modifier=bevel.name)
brake.data.materials.append(materials['DarkSteel'])
for p in brake.data.polygons:
    p.use_smooth=True
    if math.hypot(p.center.y,p.center.z)<.0055:p.material_index=1
planar_uv(brake)

parts={'dw715_rubber_grip':rubber,'dw715_target_wood_grip':wood,'dw715_muzzle_brake':brake}
for key,ob in parts.items():
    select(ob)
    tri=ob.modifiers.new('ExportTriangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    # Weighted hard-surface shading with fully authored normals in the delivered FBX.
    weighted=ob.modifiers.new('SurfaceNormals','WEIGHTED_NORMAL');weighted.keep_sharp=True
    bpy.ops.object.modifier_apply(modifier=weighted.name)
    fbx=O/('SM_'+key+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    report['parts'][key]={'fbx':str(fbx),'triangles':len(ob.data.polygons),'slots':[m.name for m in ob.data.materials],
        'mount':'WPN_SOCKET_Muzzle' if ob==brake else 'WPN_root','tip_cm':[3.4,0,0] if ob==brake else None}

# Keep source geometry and production materials editable, separate from icon-only lighting/grayscale.
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'DW715_GripBrake_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

# Shipped attachment artwork: grayscale material conversion, transparent 1024px PNG.
for mat in materials.values():
    bs=mat.node_tree.nodes.get('Principled BSDF');sock=bs.inputs['Base Color']
    if sock.is_linked:
        src=sock.links[0].from_socket;gray=mat.node_tree.nodes.new('ShaderNodeRGBToBW');mat.node_tree.links.new(src,gray.inputs[0]);mat.node_tree.links.new(gray.outputs[0],sock)
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.world=bpy.data.worlds.new('AttachmentIconWorld');scene.world.color=(.38,.38,.38)
camera_data=bpy.data.cameras.new('AttachmentIconCamera');camera=bpy.data.objects.new('AttachmentIconCamera',camera_data);scene.collection.objects.link(camera);scene.camera=camera;camera_data.type='ORTHO'
for name,loc,power,size in [('Key',(.08,.22,.24),18,.22),('Rim',(-.12,-.12,.14),12,.18),('Fill',(-.2,.18,.04),8,.18)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    lo=bpy.data.objects.new(name,light);scene.collection.objects.link(lo);lo.location=loc;lo.rotation_euler=(-lo.location).to_track_quat('-Z','Y').to_euler()
all_parts=list(parts.values())+[factory]
for key,ob in list(parts.items())+[('factory_grip',factory)]:
    for other in all_parts:other.hide_render=other!=ob
    points=[v.co for v in ob.data.vertices];lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)]);center=(lo+hi)*.5
    camera.location=center+Vector((-.055,.40,.045));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.ortho_scale=max(hi.z-lo.z,hi.x-lo.x)*1.27
    slot='muzzle' if ob==brake else 'reargrip';option='false' if ob==factory else key
    scene.render.filepath=str(ICONS/('ue_dan_wesson715_'+slot+'_'+option+'.png'))
    bpy.ops.render.render(write_still=True)
    if ob in [rubber,brake]:shutil.copyfile(scene.render.filepath,ICONS/('ue_dan_wesson715_category_'+slot+'.png'))
print('DW715_GRIP_BRAKE_AUTHORED '+str(O/'authoring.json'),flush=True)
