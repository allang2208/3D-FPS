"""Author the selected Thorn Crown pommel at the real Highland grip seat.

Blender source + FBX/GLB + baked PBR and production menu icon. No game test
or acceptance render. All dimensions are metres; socket origin is local Z=0.
"""
from pathlib import Path
import math
import json
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix

P=Path(__file__).resolve().parent
SOURCE=P.parent/'RidgePiercerRootV2_20260927/Highland_RidgePiercer_RootV2_Editable.blend'
NAME='SM_Highland_Pommel_ThornCrown_V1'
for name in ('Export','Textures','Icons'):(P/name).mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
factory=bpy.data.objects['SM_Highland_Pommel_factory']
MOUNT=factory.location.copy()
source_mat=factory.data.materials[0]
parts=[]
R=.026
CZ=-.040
ZCUT=-.004
PI=math.pi

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj

def material(name,color,metal,rough,grain=True):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    n=m.node_tree.nodes
    l=m.node_tree.links
    p=next(node for node in n if node.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal
    p.inputs['Roughness'].default_value=rough
    m.diffuse_color=(*color,1)
    if grain:
        tc=n.new('ShaderNodeTexCoord')
        noise=n.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value=5200
        noise.inputs['Detail'].default_value=2
        l.new(tc.outputs['Object'],noise.inputs['Vector'])
        mix=n.new('ShaderNodeMixRGB')
        mix.blend_type='MULTIPLY'
        mix.inputs[0].default_value=.18
        mix.inputs[1].default_value=(*color,1)
        l.new(noise.outputs['Fac'],mix.inputs[2])
        l.new(mix.outputs[0],p.inputs['Base Color'])
        remap=n.new('ShaderNodeMapRange')
        remap.inputs['To Min'].default_value=rough-.065
        remap.inputs['To Max'].default_value=rough+.065
        l.new(noise.outputs['Fac'],remap.inputs['Value'])
        l.new(remap.outputs['Result'],p.inputs['Roughness'])
        bump=n.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value=.20
        bump.inputs['Distance'].default_value=.000035
        l.new(noise.outputs['Fac'],bump.inputs['Height'])
        l.new(bump.outputs['Normal'],p.inputs['Normal'])
    return m

steel=material('ThornCrown_Author_SatinSilver',(.42,.445,.475),.94,.32)
polish=material('ThornCrown_Author_PolishedEdges',(.55,.575,.61),.96,.24)
dark=material('ThornCrown_Author_DarkRecess',(.075,.085,.105),.87,.43)
gem=material('ThornCrown_Author_AzureGem',(.006,.058,.19),0,.13,False)
gem_shader=next(node for node in gem.node_tree.nodes if node.type=='BSDF_PRINCIPLED')
gem_shader.inputs['IOR'].default_value=1.76
gem_shader.inputs['Coat Weight'].default_value=.35

def mesh_obj(name,verts,faces,mat,smooth=True):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces)
    data.update()
    # Production winding comes from connected shells; retain faceted gemstones.
    bm=bmesh.new();bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(data);bm.free()
    for poly in data.polygons:poly.use_smooth=smooth
    obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    data.materials.append(mat)
    parts.append(obj)
    return obj

def ring_surface(name,rows,mat,closed=False,smooth=True):
    n=len(rows[0]);verts=[tuple(v) for row in rows for v in row]
    faces=[]
    count=len(rows)
    for j in range(count if closed else count-1):
        k=(j+1)%count
        for i in range(n):
            faces.append((j*n+i,j*n+(i+1)%n,k*n+(i+1)%n,k*n+i))
    if not closed:
        faces.append(tuple(reversed(range(n))))
        faces.append(tuple((count-1)*n+i for i in range(n)))
    return mesh_obj(name,verts,faces,mat,smooth)

def lathe(name,profile,mat,segments=80):
    rows=[[(radius*math.cos(2*PI*i/segments),radius*math.sin(2*PI*i/segments),z)
           for i in range(segments)] for z,radius in profile]
    return ring_surface(name,rows,mat)

def tube(name,path,radius,mat,sides=6,closed=False):
    rows=[]
    for i,p in enumerate(path):
        p=Vector(p)
        previous=Vector(path[(i-1)%len(path)] if closed or i else path[i])
        following=Vector(path[(i+1)%len(path)] if closed or i<len(path)-1 else path[i])
        t=(following-previous).normalized()
        up=(p-Vector((0,0,CZ))).normalized()
        if abs(t.dot(up))>.97:up=Vector((0,1,0))
        u=t.cross(up).normalized();v=t.cross(u).normalized()
        rows.append([p+radius*(u*math.cos(2*PI*k/sides)+v*math.sin(2*PI*k/sides)) for k in range(sides)])
    return ring_surface(name,rows,mat,closed)

def bevel(obj,width=.00018,segments=2):
    activate(obj)
    mod=obj.modifiers.new('Crafted edge microbevel','BEVEL')
    mod.width=width;mod.segments=segments
    mod.limit_method='ANGLE'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    # Flat main facets with smooth bevels, weighted corner normals on metal.
    for poly in obj.data.polygons:poly.use_smooth=True
    weighted=obj.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
    weighted.keep_sharp=True;weighted.weight=45
    bpy.ops.object.modifier_apply(modifier=weighted.name)

# Copy and clip only the first 4 mm of the actual factory socket, carrying UVs
# and stored author normals. Its original upper cap and hand contact stay exact.
collar=factory.copy();collar.data=factory.data.copy()
collar.name='ThornCrown_OriginalSeat_4mm'
scene.collection.objects.link(collar)
collar.location=(0,0,0)
nm=collar.data.attributes.new('SeatNormal','FLOAT_VECTOR','CORNER')
nm.data.foreach_set('vector',np.array([n.vector[:] for n in collar.data.corner_normals],np.float32).ravel())
bm=bmesh.new();bm.from_mesh(collar.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                      plane_co=(0,0,ZCUT),plane_no=(0,0,1),dist=1e-8,clear_inner=True,clear_outer=False)
bm.to_mesh(collar.data);bm.free();collar.data.update()
seat_points={tuple(round(x,9) for x in v.co) for v in collar.data.vertices if abs(v.co.z-ZCUT)<1e-7}
seat=sorted(seat_points,key=lambda p:math.atan2(p[1],p[0]))
angles=[math.atan2(p[1],p[0]) for p in seat]
for face in collar.data.polygons:face.use_smooth=True
collar.data.normals_split_custom_set([v.vector.normalized()[:] for v in collar.data.attributes['SeatNormal'].data])

# One contiguous neck and spherical body starts at the copied real cross-section.
profiles=[(ZCUT,None),(-.005,None),(-.007,.0180),(-.009,.0180),
          (-.012,.0178),(-.014,.0175),(-.016,.0172),(-.018,.01725),(-.020,.0176)]
rows=[]
for j,(z,r) in enumerate(profiles):
    if j==0:rows.append([Vector(p) for p in seat])
    elif j==1:
        rows.append([Vector((p[0]*.98+.018*math.cos(a)*.02,p[1]*.98+.018*math.sin(a)*.02,z)) for p,a in zip(seat,angles)])
    else:rows.append([Vector((r*math.cos(a),r*math.sin(a),z)) for a in angles])
for z in np.linspace(-.021,CZ-R+.00006,36):
    radius=math.sqrt(max(0,R*R-(z-CZ)**2))
    rows.append([Vector((radius*math.cos(a),radius*math.sin(a),float(z))) for a in angles])
body=ring_surface('ThornCrown_ForgedSphereAndShoulder',rows,steel)

# Collar rings frame an actual braided relief over a dark inlaid band.
lathe('ThornCrown_CollarChannel',[(-.0069,.01812),(-.0126,.01812)],dark)
for z in [-.0067,-.0127]:
    lathe('ThornCrown_CollarRim',[(z+.00042,.018),(z+.0002,.01865),
                               (z-.0002,.01865),(z-.00042,.018)],polish)
for k in range(2):
    path=[]
    for t in np.linspace(0,2*PI,321)[:-1]:
        w=8*t+k*PI
        r=.01855+.00035*math.cos(w)
        path.append((r*math.cos(t),r*math.sin(t),-.0097+.00155*math.sin(w)))
    tube('ThornCrown_CollarInterlace_'+str(k),path,.00038,polish,6,True)

def sphere(theta,phi,radius=R):
    return Vector((radius*math.sin(theta)*math.cos(phi),
                   radius*math.sin(theta)*math.sin(phi),CZ+radius*math.cos(theta)))

# Four visible meridian braids (two front, two rear), with sunken dark grounds.
# These are true geometric strands rather than painted interlace.
for band,phi in enumerate([-PI/2-.60,-PI/2+.60,PI/2-.60,PI/2+.60]):
    ts=np.linspace(.72,PI-.42,125)
    width=.0046
    rows=[]
    for theta in ts:
        base=sphere(theta,phi)
        across=Vector((-math.sin(phi),math.cos(phi),0))
        radial=(base-Vector((0,0,CZ))).normalized()
        rows.append([base+across*s+radial*d for s,d in
                     [(-width/2,-.00010),(-width/2,.00020),(width/2,.00020),(width/2,-.00010)]])
    ring_surface('ThornCrown_EngravingGround_'+str(band),rows,dark)
    for side in [-1,1]:
        path=[]
        for theta in ts:
            p=sphere(theta,phi)+Vector((-math.sin(phi),math.cos(phi),0))*side*width/2
            p=Vector((0,0,CZ))+(p-Vector((0,0,CZ))).normalized()*(R+.00048)
            path.append(p)
        tube('ThornCrown_BandSilverBorder',path,.00025,polish,5)
    for k in range(2):
        path=[]
        for f,theta in enumerate(ts):
            w=2*PI*4.5*f/(len(ts)-1)+k*PI
            p=sphere(theta,phi)+Vector((-math.sin(phi),math.cos(phi),0))*.00125*math.sin(w)
            p=Vector((0,0,CZ))+(p-Vector((0,0,CZ))).normalized()*(R+.00063+.00036*math.cos(w))
            path.append(p)
        tube('ThornCrown_InterlacedStrand',path,.00036,polish,6)

# Six short outward thorns; non-lateral ones slope gently away from the grip.
def thorn(name,direction,length):
    d=Vector(direction).normalized()
    up=Vector((0,0,1)) if abs(d.z)<.9 else Vector((0,1,0))
    u=d.cross(up).normalized();v=d.cross(u).normalized()
    root=Vector((0,0,CZ))+d*(R-.0012)
    rows=[]
    for distance,r in [(0,.0058),(.0014,.0059),(.0032,.0051),(length,.00015)]:
        rows.append([root+d*distance+(u*math.cos(2*PI*k/4+PI/4)+v*math.sin(2*PI*k/4+PI/4))*r for k in range(4)])
    obj=ring_surface(name,rows,steel,smooth=False)
    bevel(obj,.00014,2)
    # A thin round ferrule embeds each angular root in the sphere surface.
    ring=[]
    for t in np.linspace(0,2*PI,49)[:-1]:ring.append(root+d*.0008+(u*math.cos(t)+v*math.sin(t))*.0051)
    tube(name+'_RootBead',ring,.00032,polish,5,True)

for i in range(6):
    a=2*PI*i/6
    thorn('ThornCrown_RadialSpike_'+str(i+1),(math.cos(a),math.sin(a),0 if i in [0,3] else -.32),.015)
thorn('ThornCrown_TerminalSpike',(0,0,-1),.022)

# Opposed oval blue gemstones and real silver bezels match the approved front.
for sign in [-1,1]:
    for name,rx,rz,depth,tube_r in [('Outer',.0074,.0110,.00072,.00065),
                                  ('Inner',.0060,.0090,.00155,.00035)]:
        path=[]
        for t in np.linspace(0,2*PI,97)[:-1]:
            x=rx*math.cos(t);z=rz*math.sin(t)
            y=math.sqrt(R*R-x*x-z*z)+depth
            path.append((x,sign*y,CZ+z))
        tube('ThornCrown_GemBezel_'+name+str(sign),path,tube_r,polish,8,True)
    rows=[]
    for rx,rz,depth in [(.0068,.0100,.0248),(.0060,.0090,.0260),(.0034,.0053,.0292)]:
        rows.append([(rx*math.cos(2*PI*i/12),sign*depth,CZ+rz*math.sin(2*PI*i/12)) for i in range(12)])
    ring_surface('ThornCrown_FacetedAzure_'+str(sign),rows,gem,smooth=False)

# Store the authored assembly with its individual pieces and procedural finish.
for obj in list(scene.objects):
    if obj not in parts and obj!=collar:obj.hide_set(True);obj.hide_render=True
factory.hide_render=True
for obj in parts+[collar]:obj.location=MOUNT;obj.hide_render=False
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_ThornCrown_Editable.blend'))
print('THORN_CROWN_EDITABLE_SAVED',flush=True)

# Join only new surfaces and unwrap one independent atlas; original seat keeps UV0.
bpy.ops.object.select_all(action='DESELECT')
for obj in parts:obj.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.object.join()
authored=bpy.context.object
authored.name='ThornCrown_PBR_BakeSource'
activate(authored)
if not authored.data.uv_layers:authored.data.uv_layers.new(name='UVMap')
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.004,area_weight=.8)
bpy.ops.object.mode_set(mode='OBJECT')
scene.render.engine='CYCLES';scene.cycles.samples=24
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    gpu=[d for d in prefs.devices if d.type=='OPTIX']
    for dev in prefs.devices:dev.use=dev in gpu
    if gpu:scene.cycles.device='GPU'
except Exception:pass
scene.render.bake.use_selected_to_active=False
scene.render.bake.margin=12
scene.render.bake.use_clear=True
scene.render.bake.normal_space='TANGENT'
mats=list(authored.data.materials)
size=2048

def image_new(name,color=False):
    im=bpy.data.images.new(name,width=size,height=size,alpha=False,float_buffer=False)
    im.colorspace_settings.name='sRGB' if color else 'Non-Color'
    return im

def save_image(im):
    im.filepath_raw=str(P/'Textures'/(im.name+'.png'))
    im.file_format='PNG';im.save()

def bake(kind,name,channel=None,color=False):
    im=image_new(name,color)
    records=[]
    for mat in mats:
        nt=mat.node_tree;n=nt.nodes;l=nt.links
        target=n.new('ShaderNodeTexImage');target.image=im
        n.active=target
        output=next(n for n in n if n.type=='OUTPUT_MATERIAL')
        original=output.inputs['Surface'].links[0].from_socket
        emission=None
        if channel:
            p=next(n for n in n if n.type=='BSDF_PRINCIPLED')
            inp=p.inputs[channel]
            emission=n.new('ShaderNodeEmission')
            if inp.is_linked:l.new(inp.links[0].from_socket,emission.inputs['Color'])
            else:
                value=inp.default_value
                emission.inputs['Color'].default_value=tuple(value) if channel=='Base Color' else (value,value,value,1)
            l.new(emission.outputs[0],output.inputs['Surface'])
        records.append((mat,target,emission,original,output))
    bpy.ops.object.bake(type=kind)
    for mat,target,emission,original,output in records:
        if emission:
            mat.node_tree.links.new(original,output.inputs['Surface'])
            mat.node_tree.nodes.remove(emission)
        mat.node_tree.nodes.remove(target)
    save_image(im)
    print('THORN_CROWN_BAKED '+name,flush=True)
    return im

base=bake('EMIT','T_ThornCrown_BaseColor','Base Color',True)
rough=bake('EMIT','T_ThornCrown_Roughness','Roughness')
metal=bake('EMIT','T_ThornCrown_Metallic','Metallic')
normal=bake('NORMAL','T_ThornCrown_NormalGL')
ao=bake('AO','T_ThornCrown_AO')
packed=np.ones((size*size,4),np.float32)
for channel,im in enumerate([ao,rough,metal]):
    values=np.empty(size*size*4,np.float32);im.pixels.foreach_get(values)
    packed[:,channel]=values.reshape(-1,4)[:,0]
orm=image_new('T_ThornCrown_ORM');orm.pixels.foreach_set(packed.ravel());save_image(orm)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_ThornCrown_BakeSource.blend'))

# Opaque faceted gemstone is explicitly nonmetallic in the packed B channel;
# the atlas also carries silver, patina and local ambient occlusion.
final=bpy.data.materials.new('M_ThornCrown_PBR');final.use_nodes=True
n=final.node_tree.nodes;l=final.node_tree.links;p=next(node for node in n if node.type=='BSDF_PRINCIPLED')
for im,target in [(base,'Base Color'),(rough,'Roughness'),(metal,'Metallic')]:
    tex=n.new('ShaderNodeTexImage');tex.image=im;l.new(tex.outputs['Color'],p.inputs[target])
tex=n.new('ShaderNodeTexImage');tex.image=normal
nm=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
authored.data.materials.clear();authored.data.materials.append(final)
for poly in authored.data.polygons:poly.material_index=0

# Preserve the donor seat's attributes in their original UV layer; assembled
# source uses the host transform, while exported meshes have the socket at zero.
authored.data.uv_layers[0].name=collar.data.uv_layers[0].name
activate(authored);collar.hide_set(False);collar.select_set(True)
bpy.ops.object.join()
game=bpy.context.object;game.name=NAME;game.data.name=NAME
game['interface']='highland_hilt_v1';game['socket_origin']='factory pommel local Z=0'
game['source']='Selected Thorn Crown concept; explicit Blender model with actual donor seat'
tri=game.modifiers.new('Export triangles','TRIANGULATE')
tri.keep_custom_normals=True
bpy.ops.object.modifier_apply(modifier=tri.name)
game.location=(0,0,0)
activate(game)
fbx=P/'Export'/(NAME+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,
    mesh_smooth_type='FACE',use_tspace=False)
bpy.ops.export_scene.gltf(filepath=str(P/'Export'/(NAME+'.glb')),export_format='GLB',
    use_selection=True,export_texcoords=True,export_normals=True,export_materials='EXPORT')
game.location=MOUNT
host_names={'SM_Highland_Blade_RidgePiercer_V1','SM_Highland_Guard_factory_JunctionV5','SM_Highland_Grip_factory'}
for obj in list(scene.objects):
    visible=obj==game or obj.name in host_names
    obj.hide_set(not visible);obj.hide_render=not visible
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_ThornCrown_Assembly.blend'))

# Production single-part transparent menu asset, not an acceptance screenshot.
for obj in scene.objects:obj.hide_render=obj!=game
scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024
scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.world=bpy.data.worlds.new('Thorn Crown menu studio');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.25,.25,.25,1);bg.inputs['Strength'].default_value=.7
camera=bpy.data.objects.new('Menu camera sword tip left',bpy.data.cameras.new('Menu camera sword tip left'))
scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.clip_start=.001
camera.rotation_euler=Matrix(((0,1,0),(0,0,-1),(-1,0,0))).to_euler()
bpy.context.view_layer.update()
corners=[game.matrix_world@Vector(v) for v in game.bound_box]
center=sum(corners,Vector())/8
extent=max(max(p.x for p in corners)-min(p.x for p in corners),max(p.z for p in corners)-min(p.z for p in corners))
camera.location=center+Vector((0,-.50,0));camera.data.ortho_scale=extent/.82
for name,offset,energy,diameter in [('Key',(.13,-.22,.16),12,.30),('Fill',(-.18,-.15,-.07),6,.26),('Rim',(.12,.12,.08),10,.2)]:
    lamp=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(lamp)
    lamp.data.energy=energy;lamp.data.shape='DISK';lamp.data.size=diameter
    lamp.location=center+Vector(offset);lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
icon='ue_highland_claymore_pommel_highland_thorn_crown.png'
scene.render.filepath=str(P/'Icons'/icon)
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_ThornCrown_MenuIcon.blend'))
game.data.calc_loop_triangles()
receipt={'name':'棘冠配重球','mesh':NAME,'option_candidate':'highland_thorn_crown',
         'source_blend':str(SOURCE),'donor_object':factory.name,'reference':'../SpikedPommelConcept20260927/Highland_SpikedPommel_Concept01.png',
         'fbx':str(fbx),'glb':str(P/'Export'/(NAME+'.glb')),'icon':icon,
         'ue_folder':'/Game/Weapons/HighlandClaymore20260922/ThornCrown20260927',
         'interface':{'name':'highland_hilt_v1','location_cm':[float(v)*100 for v in MOUNT],
                      'units':'metres; +Z toward blade, X blade width, Y blade depth',
                      'preserved_socket_band_mm':4,'vertices_in_lower_ring':len(seat)},
         'design':{'core_diameter_cm':5.2,'short_spikes':6,'tail_spikes':1,'gemstones':2,
                   'short_spike_projection_mm':13.8,'tail_spike_projection_mm':20.8,'braid_meridians':4},
         'materials':['M_ThornCrown_PBR',source_mat.name],
         'textures':{'size':2048,'normal_convention':'OpenGL +Y; UE flips green once','orm':'R AO / G Roughness / B Metallic','ao_baked':True},
         'topology':{'vertices':len(game.data.vertices),'triangles':len(game.data.loop_triangles)},
         'status':'authored and exported; import separately; gameplay stats unset',
         'tested':False,'acceptance_rendered':False}
(P/'authoring.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('THORN_CROWN_AUTHORED '+str(P/'authoring.json'),flush=True)
