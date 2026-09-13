"""Resize accepted pistol tactical bodies and rebuild their contoured frame contact."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent
S=O.parent
bpy.context.preferences.filepaths.save_version=0
fit=json.loads((S/'M1911Tactical20260913/fit_source.json').read_text())
try:
    bpy.ops.wm.open_mainfile(filepath=str(S/'M1911RearRain20260913/M1911_RearFinish_Editable.blend'))
except RuntimeError:
    if 'SK_M1911_Manny' not in bpy.data.objects: raise
rig=bpy.data.objects['SK_M1911_Manny']
root=rig.matrix_world @ rig.data.bones['WPN_root'].matrix_local
frame=bpy.data.objects['M1911_Frame']
points=[root.inverted() @ frame.matrix_world @ v.co for v in frame.data.vertices]
frame_surface=BVHTree.FromPolygons(points,[list(p.vertices) for p in frame.data.polygons])

def select(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

def physical_uv(ob,index):
    while len(ob.data.uv_layers)>index: ob.data.uv_layers.remove(ob.data.uv_layers[-1])
    uv=ob.data.uv_layers.new(name='M1911Coating')
    for face in ob.data.polygons:
        axis=max(range(3),key=lambda i:abs(face.normal[i]))
        axes=[i for i in range(3) if i!=axis]
        for li in face.loop_indices:
            p=ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv=(p[axes[0]]/.1+.5,p[axes[1]]/.1+.5)

def coat_material(material,collar=False):
    material.use_nodes=True
    n=material.node_tree.nodes;l=material.node_tree.links
    bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    uv=n.new('ShaderNodeUVMap');uv.uv_map='M1911Coating'
    samples={}
    for kind in ['BaseColor','ORM']:
        tex=n.new('ShaderNodeTexImage')
        tex.image=bpy.data.images.load(str(S/'M1911Attachments20260913/Textures'/('T_M1911_Attachment_'+kind+'.png')),check_existing=True)
        tex.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
        l.new(uv.outputs['UV'],tex.inputs['Vector']);samples[kind]=tex
    orm=n.new('ShaderNodeSeparateColor');l.new(samples['ORM'].outputs['Color'],orm.inputs[0])
    vertex=n.new('ShaderNodeVertexColor');vertex.layer_name='MetalRegion'
    mask=n.new('ShaderNodeSeparateColor');l.new(vertex.outputs['Color'],mask.inputs[0])
    for name,source in [('Base Color',samples['BaseColor'].outputs['Color']),('Roughness',orm.outputs['Green']),('Metallic',orm.outputs['Blue'])]:
        socket=bs.inputs[name]
        if collar:l.new(source,socket);continue
        blend=n.new('ShaderNodeMixRGB');blend.blend_type='MIX'
        value=socket.default_value
        blend.inputs[1].default_value=tuple(value) if name=='Base Color' else (value,value,value,1)
        if socket.links:l.new(socket.links[0].from_socket,blend.inputs[1])
        l.new(source,blend.inputs[2]);l.new(mask.outputs['Red'],blend.inputs[0]);l.new(blend.outputs[0],socket)
    material['M1911Finish']='Accepted slide coating; UV1; physical tile 0.1 m'

report={}
for kind in ['laser','flashlight']:
    source=fit['devices'][kind]
    bpy.ops.wm.open_mainfile(filepath=source['source'])
    ob=bpy.data.objects['SM_TacticalDevice']
    emitter=Vector(source['emitter_m'])
    for other in list(bpy.context.scene.objects):
        if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
    # Retain the accepted body identity and rebuild the saddle after pistol sizing.
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=0],context='FACES')
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bm.to_mesh(ob.data);bm.free()
    body_material=ob.data.materials[0].copy();body_material.name='M_Tactical_'+kind
    ob.data.materials.clear();ob.data.materials.append(body_material)
    for face in ob.data.polygons:face.material_index=0
    body_scale=.70 if kind=='laser' else .72
    rotation=Matrix.Rotation(math.pi/2,4,'Y') @ Matrix.Diagonal((body_scale,body_scale,body_scale,1.))
    rotated=[rotation @ v.co for v in ob.data.vertices]
    lo=Vector([min(p[i] for p in rotated) for i in range(3)])
    hi=Vector([max(p[i] for p in rotated) for i in range(3)])
    # Tail stops forward of the trigger guard. Source clamp turns upward to the frame.
    offset=Vector((-(lo.x+hi.x)*.5,-.064-hi.y,-.0010-hi.z))
    transform=Matrix.Translation(offset) @ rotation
    ob.data.transform(transform);emitter=transform @ emitter
    optical_center=emitter+Vector((0,.002*body_scale,0))
    low_y=min(v.co.y for v in ob.data.vertices)
    colors=ob.data.color_attributes['MetalRegion']
    for face in ob.data.polygons:
        for li in face.loop_indices:
            p=ob.data.vertices[ob.data.loops[li].vertex_index].co
            metal=colors.data[li].color[0]
            if kind=='flashlight' and p.y>low_y+.008*body_scale:metal=1.
            aperture=float(kind=='laser' and (p-optical_center).length<.0065*body_scale and metal<.5)
            colors.data[li].color=(metal,aperture,metal,1)
    device_surface=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[list(p.vertices) for p in ob.data.polygons])
    nx,ny=8,12
    top=[];bottom=[]
    for iy in range(ny+1):
        for ix in range(nx+1):
            x=(ix/nx-.5)*.016;y=-.083+(iy/ny-.5)*.026
            frame_hit,_,_,_=frame_surface.ray_cast(Vector((x,y,-.15)),Vector((0,0,1)),.25)
            device_hit,_,_,_=device_surface.ray_cast(Vector((x,y,.02)),Vector((0,0,-1)),.2)
            if frame_hit is None:raise RuntimeError('Missing pistol frame contact '+kind)
            top.append((x,y,frame_hit.z+.00015));bottom.append((x,y,device_hit.z-.00015 if device_hit else None))
    solid=[p for p in bottom if p[2] is not None]
    if not solid:raise RuntimeError('No device contact under the saddle '+kind)
    # The mount spans recesses in the generated clamp, just as the rifle saddle does.
    bridged=sum(p[2] is None for p in bottom)
    bottom=[p if p[2] is not None else (p[0],p[1],min(solid,key=lambda q:(q[0]-p[0])**2+(q[1]-p[1])**2)[2]) for p in bottom]
    count=len(top);faces=[]
    for iy in range(ny):
        for ix in range(nx):
            a=iy*(nx+1)+ix;b=a+1;c=b+nx+1;d=a+nx+1
            faces.extend([(a,b,c,d),(d+count,c+count,b+count,a+count)])
    edge=list(range(nx+1))+[iy*(nx+1)+nx for iy in range(1,ny+1)]+[ny*(nx+1)+ix for ix in range(nx-1,-1,-1)]+[iy*(nx+1) for iy in range(ny-1,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]):faces.append((a,a+count,b+count,b))
    mesh=bpy.data.meshes.new('M1911DustCoverSaddle');mesh.from_pydata(top+bottom,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    saddle=bpy.data.objects.new('M1911DustCoverSaddle',mesh);bpy.context.collection.objects.link(saddle)
    collar=bpy.data.materials.new('M_Tactical_Collar');mesh.materials.append(collar)
    physical_uv(saddle,0)
    mesh.uv_layers[0].name=ob.data.uv_layers[0].name
    color=mesh.color_attributes.new(name='MetalRegion',type='BYTE_COLOR',domain='CORNER');mesh.color_attributes.active_color=color
    for c in color.data:c.color=(1,0,1,1)
    select(saddle)
    bevel=saddle.modifiers.new('Machined saddle edge','BEVEL');bevel.width=.0002;bevel.segments=2;bevel.limit_method='ANGLE'
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    select(ob);saddle.select_set(True);bpy.ops.object.join()
    physical_uv(ob,1);ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
    coat_material(body_material);coat_material(collar,True)
    select(ob)
    for name,point in [('Emitter',emitter),('AimGuide',emitter+Vector((0,-.03,0)))]:
        socket=bpy.data.objects.new('SOCKET_'+name,None);bpy.context.collection.objects.link(socket)
        socket.parent=ob;socket.location=point;socket.select_set(True)
    folder=O/kind;folder.mkdir(exist_ok=True)
    file=folder/'SM_TacticalDevice.fbx'
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'M1911_Device_Editable.blend'))
    report[kind]={'fbx':str(file),'source':source['source'],'body_scale':body_scale,'reference_frame':'M1911 WPN_root authoring metres; FBX centimetres, +Y forward',
                  'uv_index':1,'physical_tile_m':.1,'emitter_blender_m':list(emitter),'emitter_ue_cm':[emitter.x*100,-emitter.y*100,emitter.z*100],
                  'tail_y_m':-.064,'saddle_center_m':[0,-.083],'saddle_length_m':.026,'bounds_m':{'min':[min(v.co[i] for v in ob.data.vertices) for i in range(3)],'max':[max(v.co[i] for v in ob.data.vertices) for i in range(3)]},'saddle_bridged_samples':bridged,'slots':[m.name for m in ob.data.materials]}
    print('M1911_TACTICAL_AUTHORED '+kind,flush=True)
(O/'tactical_authoring.json').write_text(json.dumps(report,indent=2))

# Keep a fitted editable assembly on the current accepted pistol source.
try:bpy.ops.wm.open_mainfile(filepath=str(S/'M1911RearRain20260913/M1911_RearFinish_Editable.blend'))
except RuntimeError:
    if 'SK_M1911_Manny' not in bpy.data.objects:raise
rig=bpy.data.objects['SK_M1911_Manny'];rig.data.pose_position='REST';bpy.context.view_layer.update()
root=rig.matrix_world @ rig.data.bones['WPN_root'].matrix_local
collection=bpy.data.collections.new('M1911_TACTICAL_ALTERNATIVES');bpy.context.scene.collection.children.link(collection)
for kind in ['laser','flashlight']:
    with bpy.data.libraries.load(str(O/kind/'M1911_Device_Editable.blend'),link=False) as (src,dst):dst.objects=['SM_TacticalDevice']
    ob=dst.objects[0];collection.objects.link(ob);ob.name='M1911_'+kind
    ob.parent=rig;ob.parent_type='BONE';ob.parent_bone='WPN_root';ob.matrix_world=root
    ob.hide_set(kind=='flashlight');ob.hide_render=kind=='flashlight'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_CompactTactical_Assembly_Editable.blend'))
print('M1911_TACTICAL_ASSEMBLY_SAVED',flush=True)
