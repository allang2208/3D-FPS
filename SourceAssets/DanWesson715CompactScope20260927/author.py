"""Produce two original DW715 game attachments and their shipped UI icons.
No gameplay/fit acceptance renders. Dimensions are visual asset coordinates.
"""
import ast, bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent; ROOT=O.parents[1]; SOURCES=O.parent
T=O/'Textures';T.mkdir(parents=True,exist_ok=True)
ICONS=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
bpy.context.preferences.filepaths.save_version=0
try:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCES/'DanWesson715MetalFinish20260914/DanWesson715_MetalFinish_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
rig=bpy.data.objects['SK_DW715_Manny'];inv=rig.data.bones['WPN_root'].matrix_local.inverted()
aim_frame=Matrix(((0,-1,0,0),(1,0,0,0),(0,0,1,0),(0,0,0,1)))
grip_source=bpy.data.objects['DW715_RubberGrip'].data
grip_vertices=[tuple(aim_frame@inv@v.co) for v in grip_source.vertices]
grip_faces=[list(p.vertices) for p in grip_source.polygons]
shroud=bpy.data.objects['DW715_BarrelShroud'].data
surface=BVHTree.FromPolygons([inv@v.co for v in shroud.vertices],[list(p.vertices) for p in shroud.polygons])
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
report={'source':'DanWesson715MetalFinish20260914/DanWesson715_MetalFinish_Editable.blend',
        'frame':'metres, +X forward +Z up. Grip origin WPN_root; optic origin same as accepted DW715 upper saddle.',
        'scope_mount_root_m':[0,-.120,.0615], 'textures':{},'parts':{},
        'provenance':'Original game geometry; source grip interface and shroud from project-owned DW715. No branded model or logo copied.',
        'state':'Production only; no gameplay or geometry acceptance tests.'}

def select(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

def mesh_object(name,verts,faces,material):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);me.materials.append(material)
    return ob

def physical_uv(ob):
    uv=ob.data.uv_layers.get('Physical10cm') or ob.data.uv_layers.new(name='Physical10cm')
    for p in ob.data.polygons:
        axis=max(range(3),key=lambda i:abs(p.normal[i]));axes=(0,2) if axis==1 else (1,2) if axis==0 else (0,1)
        for li in p.loop_indices:
            co=ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv=(co[axes[0]]/.1,co[axes[1]]/.1)

def finish(ob,bevel=0):
    select(ob)
    if bevel:
        mod=ob.modifiers.new('Machined edge','BEVEL');mod.width=bevel;mod.segments=2;mod.limit_method='ANGLE';mod.angle_limit=math.radians(35)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in ob.data.polygons:p.use_smooth=True
    ob.data.set_sharp_from_angle(angle=math.radians(38))
    weighted=ob.modifiers.new('Weighted corners','WEIGHTED_NORMAL');weighted.keep_sharp=True
    bpy.ops.object.modifier_apply(modifier=weighted.name)
    physical_uv(ob);return ob

def image(name,arr,color=False):
    im=bpy.data.images.new(name,width=arr.shape[1],height=arr.shape[0],alpha=True)
    im.colorspace_settings.name='sRGB' if color else 'Non-Color'
    rgba=np.ones((*arr.shape[:2],4),dtype=np.float32);rgba[:,:,:3]=np.clip(arr,0,1)
    im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(T/(name+'.png'));im.file_format='PNG';im.save();return im

def material(key,maps):
    mat=bpy.data.materials.new('DW715_'+key);mat.use_nodes=True
    n=mat.node_tree.nodes;l=mat.node_tree.links;bs=n.get('Principled BSDF')
    for kind,file in maps.items():
        im=bpy.data.images.load(str(file),check_existing=True);im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
        sample=n.new('ShaderNodeTexImage');sample.image=im
        if kind=='BaseColor':l.new(sample.outputs['Color'],bs.inputs['Base Color'])
        elif kind=='Normal':
            normal=n.new('ShaderNodeNormalMap');l.new(sample.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],bs.inputs['Normal'])
        else:
            sep=n.new('ShaderNodeSeparateColor');l.new(sample.outputs['Color'],sep.inputs['Color'])
            l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    report['textures'][key]={k:str(v) for k,v in maps.items()};return mat

N=1024;v,u=np.mgrid[0:N,0:N].astype(np.float32)/N
weave=np.sin(2*np.pi*(u+v)*91)*np.sin(2*np.pi*(u-v)*89)
stripes=(.5+.5*np.cos(2*np.pi*(u*53+v*16)))**8
micro=np.sin(u*2*np.pi*233)*np.sin(v*2*np.pi*241)
materials={}
for key,color,rough,height,metal in [
    ('CompactG10',np.stack([.035+weave*.004+stripes*.009]*3,-1),.54+weave*.055,stripes*.00006+micro*.000005,0),
    ('OpticalBlack',np.stack([.014+micro*.001]*3,-1),.7+micro*.012,micro*.000002,0),
    ('CoatedGlass',np.stack([np.full_like(u,.028),np.full_like(u,.055),np.full_like(u,.063)],-1),np.full_like(u,.085),micro*.0000002,0),
]:
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(.2/N)
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(.2/N)
    norm=np.stack([-dx,-dy,np.ones_like(dx)],-1);norm/=np.linalg.norm(norm,axis=-1,keepdims=True)
    maps={k:Path(im.filepath_raw) for k,im in {
        'BaseColor':image('T_DW715_'+key+'_BaseColor',color,True),
        'Normal':image('T_DW715_'+key+'_NormalGL',norm*.5+.5),
        'ORM':image('T_DW715_'+key+'_ORM',np.stack([np.ones_like(rough),rough,np.full_like(rough,metal)],-1))}.items()}
    materials[key]=material(key,maps)
# Accepted 715 metal finish, not a rifle's unrelated coating.
finish_tiles=SOURCES/'DanWesson715Attachments20260914/Textures'
materials['ScopeSteel']=material('ScopeSteel',{
    'BaseColor':finish_tiles/'T_DW715_Attachment_BaseColor.png',
    'Normal':SOURCES/'DanWesson715GripBrake20260927/Textures/T_DW715_Steel_NormalGL.png',
    'ORM':finish_tiles/'T_DW715_Attachment_ORM.png'})

grip=mesh_object('dw715_compact_grip',grip_vertices,grip_faces,materials['CompactG10'])
# Introduce transition loops so narrowing the exposed rear heel cannot pull the
# long source triangles across the support palm. The neck/front/finger band stays.
bm=bmesh.new();bm.from_mesh(grip.data)
for axis,values in [(2,[-.083,-.089,-.093]),(0,[-.067,-.075,-.081])]:
    normal=[0,0,0];normal[axis]=1
    for value in values:
        point=[0,0,0];point[axis]=value
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,
            plane_co=point,plane_no=normal,clear_inner=False,clear_outer=False)
bm.to_mesh(grip.data);bm.free()
def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
for vert in grip.data.vertices:
    c=vert.co;t=smooth((-c.z-.083)/.013734)*smooth((-c.x-.067)/.017592)
    c.x+=.0055*t;c.z+=.004*t;c.y*=1-.22*t
grip.data.update();finish(grip)

scope_parts=[]
def add(ob):scope_parts.append(ob);return ob
def lathe(name,profile,mat,center=(0,0,.025),segments=64):
    verts=[];faces=[]
    for x,r in profile:
        for i in range(segments):
            a=2*math.pi*i/segments;verts.append((x+center[0],math.cos(a)*r+center[1],math.sin(a)*r+center[2]))
    for row in range(len(profile)):
        nr=(row+1)%len(profile)
        for i in range(segments):
            j=(i+1)%segments;faces.append((row*segments+i,row*segments+j,nr*segments+j,nr*segments+i))
    return finish(mesh_object(name,verts,faces,mat))
def box(name,center,size,mat,bevel=.00035):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);ob=bpy.context.object;ob.name=name;ob.dimensions=size
    select(ob);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);ob.data.materials.append(mat)
    return finish(ob,bevel)
def cylinder(name,center,radius,depth,mat,axis='Z',verts=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth,location=center)
    ob=bpy.context.object;ob.name=name
    ob.rotation_euler=(0,math.pi/2,0) if axis=='X' else (math.pi/2,0,0) if axis=='Y' else (0,0,0)
    select(ob);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);ob.data.materials.append(mat)
    return finish(ob,.00015)

steel=materials['ScopeSteel'];black=materials['OpticalBlack']
add(lathe('SilverFixedPowerBody',[
    (-.088,.0168),(-.085,.0175),(-.062,.0175),(-.058,.0142),(-.05,.0127),
    (.054,.0127),(.06,.0142),(.078,.0142),(.08,.0135),(.08,.0105),
    (.058,.0105),(-.052,.0105),(-.06,.0135),(-.088,.0135)],steel))
add(lathe('MatteOcularEyecup',[(-.095,.0163),(-.094,.018),(-.085,.018),(-.083,.0171),(-.083,.0136),(-.095,.0136)],black))
add(lathe('ObjectiveRecess',[(.072,.0119),(.080,.0119),(.080,.0103),(.072,.0103)],black))
# World-facing optical surfaces; the owner ADS picture is the independent overlay.
for name,x,r in [('OcularGlass',-.090,.0135),('ObjectiveGlass',.073,.0104)]:
    add(cylinder(name,(x,0,.025),r,.00045,materials['CoatedGlass'],'X',64))
# Two rings on the fixed shroud. Ring feet and conforming saddle are authored
# together in the existing 715 optic frame; the cylinder is not a mount parent.
for x in [-.020,.036]:
    add(lathe('SplitMountRing',[(x-.0045,.0145),(x+.0045,.0145),(x+.0045,.0127),(x-.0045,.0127)],steel))
    add(box('RingFoot',(x,0,.009),(.012,.017,.014),steel))
    for y in [-.016,.016]:
        add(box('RingEar',(x,y,.025),(.009,.004,.005),steel,.0002))
        add(cylinder('RingFastener',(x,y,.028),.00155,.0012,black,verts=24))
# Ray-sampled contact surface from the real author shroud (production fitting).
nx,ny=20,8;upper=[];lower=[]
for ix in range(nx+1):
    x=.012+(ix/nx-.5)*.076
    for iy in range(ny+1):
        y=(iy/ny-.5)*.010
        point=surface.ray_cast(Vector((y,-.120-x,.12)),Vector((0,0,-1)),.2)[0]
        if point is None:raise RuntimeError('Cannot author the saddle without a shroud contact surface')
        lower.append((x,y,point.z-.0615-.00012));upper.append((x,y*1.7,.004))
count=len(upper);faces=[]
for ix in range(nx):
    for iy in range(ny):
        a=ix*(ny+1)+iy;b=a+1;c=b+ny+1;d=a+ny+1
        faces.extend([(a,b,c,d),(d+count,c+count,b+count,a+count)])
edge=list(range(ny+1))+[i*(ny+1)+ny for i in range(1,nx+1)]+[nx*(ny+1)+i for i in range(ny-1,-1,-1)]+[i*(ny+1) for i in range(nx-1,0,-1)]
for a,b in zip(edge,edge[1:]+edge[:1]):faces.append((a,a+count,b+count,b))
add(finish(mesh_object('DW715ConformingSaddle',upper+lower,faces,steel),.00012))
# Compact elevation/windage caps and shallow grip ribs, no moving magnification ring.
add(box('AdjustmentBlock',(.004,0,.025),(.017,.027,.027),steel,.0006))
for axis,center in [('Z',(.004,0,.041)),('Y',(.004,-.016,.025))]:
    add(cylinder('AdjustmentCap',center,.007,.007,steel,axis,48))
    for i in range(20):
        a=2*math.pi*i/20
        c=Vector(center)
        if axis=='Z':c+=Vector((math.cos(a)*.007,math.sin(a)*.007,0));size=(.0006,.0006,.005)
        else:c+=Vector((math.cos(a)*.007,0,math.sin(a)*.007));size=(.0006,.005,.0006)
        add(box('CapRib',c,size,black,.00008))
# Fine ocular collar grooves read at arm's length without a heavy knurl mesh.
for x in [-.081,-.077,-.073,-.069]:
    add(lathe('OcularCollarGroove',[(x-.00035,.01757),(x+.00035,.01757),(x+.00035,.01725),(x-.00035,.01725)],black,segments=64))

select(scope_parts[0])
for ob in scope_parts:ob.select_set(True)
bpy.ops.object.join();scope=bpy.context.object;scope.name='dw715_handgun_scope_2x'
parts={'dw715_compact_grip':grip,'dw715_handgun_scope_2x':scope}
for key,ob in parts.items():
    select(ob);tri=ob.modifiers.new('ExportTriangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    sockets={}
    if ob==scope:
        for name,co in {'AimCenter':(-.090,0,.025),'MountForward':(.03,0,0),'MountUp':(0,0,.03)}.items():
            empty=bpy.data.objects.new('SOCKET_'+name,None);scene.collection.objects.link(empty);empty.parent=ob;empty.location=co;empty.select_set(True)
            sockets[name]=[v*100 for v in co]
    fbx=O/('SM_'+key+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    bounds=[[min(v.co[i] for v in ob.data.vertices)*100 for i in range(3)],[max(v.co[i] for v in ob.data.vertices)*100 for i in range(3)]]
    report['parts'][key]={'fbx':str(fbx),'triangles':len(ob.data.polygons),'slots':[m.name for m in ob.data.materials],
        'mount':'DW715 existing optic saddle' if ob==scope else 'WPN_root','bounds_cm':bounds,'sockets_cm':sockets}
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'DW715_CompactScope_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

# Actual shipped inventory icons, grayscale only. No additional acceptance images.
for mat in materials.values():
    bs=mat.node_tree.nodes.get('Principled BSDF');socket=bs.inputs['Base Color']
    if socket.is_linked:
        src=socket.links[0].from_socket;gray=mat.node_tree.nodes.new('ShaderNodeRGBToBW')
        mat.node_tree.links.new(src,gray.inputs[0]);mat.node_tree.links.new(gray.outputs[0],socket)
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.world=bpy.data.worlds.new('IconWorld');scene.world.color=(.38,.38,.38)
cd=bpy.data.cameras.new('IconCamera');camera=bpy.data.objects.new('IconCamera',cd);scene.collection.objects.link(camera);scene.camera=camera;cd.type='ORTHO'
for name,loc,power,size in [('Key',(.08,.22,.24),18,.22),('Rim',(-.12,-.12,.14),12,.18),('Fill',(-.2,.18,.04),8,.18)]:
    ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.shape='DISK';ld.size=size
    light=bpy.data.objects.new(name,ld);scene.collection.objects.link(light);light.location=loc;light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
for key,ob in parts.items():
    for other in parts.values():other.hide_render=other!=ob
    lo=Vector([min(v.co[i] for v in ob.data.vertices) for i in range(3)]);hi=Vector([max(v.co[i] for v in ob.data.vertices) for i in range(3)]);center=(lo+hi)*.5
    camera.location=center+Vector((-.10,.40,0));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=max(hi.z-lo.z,hi.x-lo.x)*1.22
    slot='optic' if ob==scope else 'reargrip'
    scene.render.filepath=str(ICONS/('ue_dan_wesson715_'+slot+'_'+key+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'DW715_CompactScope_IconScene.blend'))
print('DW715_COMPACT_SCOPE_AUTHORED',flush=True)
