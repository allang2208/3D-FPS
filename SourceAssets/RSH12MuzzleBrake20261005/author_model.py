"""RSH MUZZLE BRAKE: game exterior from the user-approved concept.

Writes editable Blender sources, PBR textures and mesh exports only.
No UE changes, rendering, gameplay tests, or functional internal geometry.
"""
import json
import math
import shutil
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

O=Path(__file__).resolve().parent
S=O.parent
E=O/'Exports'
T=O/'Textures'
for folder in (E,T,O/'Reference'):folder.mkdir(parents=True,exist_ok=True)
concept=S/'RSH12MuzzleBrakeConcept20261005/RSH12_MuzzleBrake_Concept_v1.png'
shutil.copy2(concept,O/'Reference'/concept.name)
raw=json.loads((S/'RSH12Integration20261003/canonical_parts.json').read_text())
old=json.loads((S/'RSH12HeavySuppressor20261004/authoring.json').read_text())
finish=json.loads((S/'RSH12Optics20261004/finish_reference.json').read_text())
to_gun=Matrix(old['interface']['accessory_to_canonical_m'])
from_gun=to_gun.inverted()

# The accessory origin remains the game's existing muzzle frame. The visible
# rear shoulder instead follows the original SHROUD face, behind that origin.
front_points=[]
for name in ('1_l','2_l'):
    part=next(p for p in raw if p['name']==name)
    front=min(v[1] for v in part['verts'])
    front_points.extend(from_gun@Vector(v) for v in part['verts'] if abs(v[1]-front)<.00004)
rear_x=sum(p.x for p in front_points)/len(front_points)

def hull(points):
    pts=sorted(set(tuple(p) for p in points))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[]
    for p in pts:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=1.e-12:lower.pop()
        lower.append(p)
    upper=[]
    for p in reversed(pts):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=1.e-12:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]

contact=hull([(p.y,p.z) for p in front_points])
ZC=(max(p[1] for p in contact)+min(p[1] for p in contact))*.5
LENGTH=.075
WIDTH=.036
HEIGHT=.063
Z0=ZC-HEIGHT*.5
Z1=ZC+HEIGHT*.5
TEX=2048
UV_METERS=.12
MODEL='SM_RSH12_MuzzleBrake'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1.

def collection(name):
    c=bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

construction=collection('EDITABLE_ExteriorParts')
cutters=collection('EDITABLE_ReliefCutters')
output=collection('GAME_Export')
guides=collection('INTERFACE_Guides')
parts=[]
materials={}
maps={}

def image(name,rgb,srgb=False):
    h,w=rgb.shape[:2]
    im=bpy.data.images.new(name,width=w,height=h,alpha=True)
    im.colorspace_settings.name='sRGB' if srgb else 'Non-Color'
    pixels=np.ones((h,w,4),dtype=np.float32)
    pixels[:,:,:3]=rgb
    im.pixels.foreach_set(pixels.ravel())
    im.filepath_raw=str(T/(name+'.png'))
    im.file_format='PNG'
    im.save()
    return im

def srgb(linear):
    return np.where(linear<=.0031308,linear*12.92,1.055*np.maximum(linear,0.)**(1./2.4)-.055)

def material(name,color,rough,metal,seed,scratches):
    # Physical-size planar UVs keep the new length's grain and scratches the
    # same size. The actual chamfers, collar and relief remain real geometry.
    rng=np.random.default_rng(seed)
    v,u=np.mgrid[0:TEX,0:TEX].astype(np.float32)/TEX
    grain=rng.random((TEX,TEX),dtype=np.float32)-.5
    mottle=(np.sin(u*31.+np.sin(v*19.))*np.sin(v*43.+u*7.)+np.sin(u*91.-v*37.))*.5
    scratch=np.zeros((TEX,TEX),dtype=np.float32)
    for _ in range(scratches):
        a=rng.random(2)*TEX
        angle=rng.uniform(-math.pi,math.pi)
        length=rng.uniform(2.,38.)
        n=max(3,int(length*2))
        xy=a[None,:]+np.linspace(0.,length,n)[:,None]*np.array([math.cos(angle),math.sin(angle)])[None,:]
        x=xy[:,0].astype(int)%TEX;y=xy[:,1].astype(int)%TEX
        scratch[y,x]=np.maximum(scratch[y,x],rng.uniform(.15,.72))
    scratch=(scratch*4.+np.roll(scratch,1,0)+np.roll(scratch,-1,0)+np.roll(scratch,1,1)+np.roll(scratch,-1,1))/8.
    base=np.asarray(color,dtype=np.float32)[None,None,:]*(1.+grain[:,:,None]*.045)
    base=base*(1.-scratch[:,:,None]) + np.array([.20,.205,.21])[None,None,:]*scratch[:,:,None]
    r=np.clip(rough+grain*.035-scratch*.14,.15,.95)
    height=grain*.0000015+np.sin(v*math.tau*370.+np.sin(u*math.tau*3.)*.15)*.0000008-scratch*.000009
    du=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*UV_METERS/TEX)
    dv=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*UV_METERS/TEX)
    normal=np.stack((-du,-dv,np.ones_like(du)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    prefix='T_RSH12_Brake_'+name
    bc=image(prefix+'_BaseColor',np.clip(srgb(base),0.,1.),True)
    orm=image(prefix+'_ORM',np.stack((np.ones_like(r),r,np.full_like(r,metal)),axis=-1))
    ng=image(prefix+'_NormalGL',normal*.5+.5)
    normal[:,:,1]*=-1.
    nd=image(prefix+'_NormalDX',normal*.5+.5)
    m=bpy.data.materials.new('RSH12Brake_'+name)
    m.use_nodes=True;m.diffuse_color=(*color,1.)
    n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    tex=n.new('ShaderNodeTexImage');tex.image=bc
    packed=n.new('ShaderNodeTexImage');packed.image=orm
    sep=n.new('ShaderNodeSeparateColor')
    nt=n.new('ShaderNodeTexImage');nt.image=ng
    nm=n.new('ShaderNodeNormalMap');nm.uv_map='UV0'
    l.new(tex.outputs['Color'],p.inputs['Base Color'])
    l.new(packed.outputs['Color'],sep.inputs['Color'])
    l.new(sep.outputs['Green'],p.inputs['Roughness'])
    l.new(sep.outputs['Blue'],p.inputs['Metallic'])
    l.new(nt.outputs['Color'],nm.inputs['Color'])
    l.new(nm.outputs['Normal'],p.inputs['Normal'])
    maps[name]=dict(base_color=str(Path(bc.filepath_raw).relative_to(O)),orm=str(Path(orm.filepath_raw).relative_to(O)),
        normal_gl=str(Path(ng.filepath_raw).relative_to(O)),normal_dx=str(Path(nd.filepath_raw).relative_to(O)),
        base_color_linear=list(color),roughness=rough,metallic=metal)
    materials[name]=m
    return m

material('Shell',tuple(finish['base_color']),float(finish['roughness'][0]),1.,127054,0)
material('Trim',(.049,.050,.051),.42,1.,127055,0)
recess=bpy.data.materials.new('RSH12Brake_Recess')
recess.use_nodes=True;recess.diffuse_color=(.006,.0065,.007,1.)
p=recess.node_tree.nodes.get('Principled BSDF')
p.inputs['Base Color'].default_value=recess.diffuse_color
p.inputs['Roughness'].default_value=.85;p.inputs['Metallic'].default_value=0.
materials['Recess']=recess

def mesh_object(name,verts,faces,region='Shell',dest=None):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces);mesh.update()
    for m in materials.values():mesh.materials.append(m)
    for face in mesh.polygons:face.material_index=list(materials).index(region)
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    ob=bpy.data.objects.new(name,mesh)
    (dest or construction).objects.link(ob)
    if dest!=cutters:parts.append(ob)
    return ob

def bevel(ob,name,width,segments,material_index=-1,angle=30.):
    mod=ob.modifiers.new(name,'BEVEL');mod.width=width;mod.segments=segments
    mod.limit_method='ANGLE';mod.angle_limit=math.radians(angle)
    mod.use_clamp_overlap=True;mod.harden_normals=True;mod.material=material_index
    return mod

def rectangle(half_y,lo,hi,cut):
    return [(-half_y+cut,lo),(half_y-cut,lo),(half_y,lo+cut),(half_y,hi-cut),
        (half_y-cut,hi),(-half_y+cut,hi),(-half_y,hi-cut),(-half_y,lo+cut)]

def loft(name,rings,region='Shell',cap=True,dest=None):
    count=len(rings[0]);verts=[p for r in rings for p in r];faces=[]
    for a in range(len(rings)-1):
        for i in range(count):faces.append((a*count+i,a*count+(i+1)%count,(a+1)*count+(i+1)%count,(a+1)*count+i))
    if cap:
        faces.extend([tuple(reversed(range(count))),tuple((len(rings)-1)*count+i for i in range(count))])
    return mesh_object(name,verts,faces,region,dest)

def section(x,half_y,lo,hi,cut):return [(x,y,z) for y,z in rectangle(half_y,lo,hi,cut)]

def prism_xz(name,poly,ya,yb,region='Shell',dest=None):
    return loft(name,[[(x,ya,z) for x,z in poly],[(x,yb,z) for x,z in poly]],region,True,dest)

def boolean(ob,cutter):
    mod=ob.modifiers.new('ShallowExteriorRelief_'+cutter.name,'BOOLEAN')
    mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter

# Compact solid game-prop body with six blind exterior side pockets.
# Dark closed cavity backs preserve the concept appearance without internal mechanics.
body=loft('Compact_ThreeWindow_Body',[
    section(.010,WIDTH*.5-.0005,Z0+.0005,Z1-.0005,.0045),
    section(.014,WIDTH*.5,Z0,Z1,.005),
    section(LENGTH-.012,WIDTH*.5,Z0,Z1,.005),
    section(LENGTH-.008,WIDTH*.5-.0007,Z0+.0007,Z1-.0007,.0048)])

def rounded_rect(cx,cz,w,h,r,steps=9,sweep=0.):
    points=[]
    for dx,dz,start in ((1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)):
        center_x=cx+dx*(w*.5-r);center_z=cz+dz*(h*.5-r)
        for i in range(steps+1):
            a=math.radians(start+i*90/steps)
            z=center_z+r*math.sin(a)
            points.append((center_x+r*math.cos(a)+sweep*(z-cz)/h,z))
    return points

for index,x in enumerate((.0238,.0407,.0576)):
    outline=rounded_rect(x,ZC,.0118,.043,.003,9,.0018)
    for side in (-1,1):
        ys=sorted([side*.0102,side*.025])
        c=prism_xz('SideWindow_%d_%s'%(index+1,side),outline,*ys,'Recess',cutters)
        boolean(body,c)

# Two shallow roof recesses repeat the approved top-side rhythm.
for index,x in enumerate((.029,.051)):
    outline=rounded_rect(x,0.,.014,.020,.0022,8)
    rings=[[(a,b,z) for a,b in outline] for z in (Z1-.004,Z1+.005)]
    c=loft('RoofWindow_'+str(index+1),rings,'Recess',True,cutters)
    boolean(body,c)
bevel(body,'Continuous_Port_Edge_Break',.00032,3,1,25.)

# The rear visual bridge starts exactly on the source shroud outline. A convex
# outer boundary is intentional here; holes in the host's face are not copied
# into this closed, decorative attachment exterior.
center=Vector((0.,ZC))
body_outline=rectangle(WIDTH*.5-.0002,Z0+.0002,Z1-.0002,.0049)

def ray_polygon(poly,theta):
    ray=Vector((math.cos(theta),math.sin(theta)))
    cross=lambda a,b:a.x*b.y-a.y*b.x
    hits=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        a=Vector(a)-center;b=Vector(b)-center;e=b-a
        den=cross(ray,e)
        if abs(den)<1.e-12:continue
        distance=cross(a,e)/den
        t=cross(a,ray)/den
        if distance>0. and -.000001<=t<=1.000001:hits.append(distance)
    return center+ray*min(hits)

angles=sorted(set(round(math.atan2(z-ZC,y)%math.tau,10) for y,z in contact+body_outline))
back=[ray_polygon(contact,t) for t in angles]
front=[ray_polygon(body_outline,t) for t in angles]
adapter_rings=[]
for x,t in [(rear_x,0.),(rear_x+.001,0.),(-.003,.48),(.006,.86),(.014,1.)]:
    adapter_rings.append([(x,*(a.lerp(b,t))) for a,b in zip(back,front)])
adapter=loft('Shroud_Contour_Transition',adapter_rings)
bevel(adapter,'Transition_Edge_Break',.00018,3,-1,38.)

# Dog-leg graphite collar follows the approved exterior silhouette. Its step is cosmetic,
# while the independent black transition underneath carries the contact shape.
outline=rectangle(WIDTH*.5+.0008,Z0-.0008,Z1+.0008,.0054)
def collar_shift(z):
    t=max(0.,min(1.,(ZC+.011-z)/.014))
    return .010*t

collar_rings=[]
for base_x,inset in [(-.007,.0005),(-.006,0.),(.003,0.),(.004,.0005)]:
    ring=[]
    for y,z in outline:
        yz=center+(Vector((y,z))-center)*(1.-inset/(HEIGHT*.5))
        ring.append((base_x+collar_shift(z),yz.x,yz.y))
    collar_rings.append(ring)
collar=loft('Stepped_Graphite_Collar',collar_rings,'Trim')
bevel(collar,'Collar_Micro_Bevel',.00022,3,-1,24.)

# Deliberately shallow closed front face: visual lip and dark inset only.
gasket=loft('Front_Dark_Seam',[
    section(LENGTH-.011,WIDTH*.5-.0003,Z0+.0003,Z1-.0003,.0049),
    section(LENGTH-.0085,WIDTH*.5-.0003,Z0+.0003,Z1-.0003,.0049)],'Recess')
cap=loft('Chamfered_Front_Cap',[
    section(LENGTH-.0088,WIDTH*.5,Z0,Z1,.005),
    section(LENGTH-.006,WIDTH*.5,Z0,Z1,.005),
    section(LENGTH-.001,WIDTH*.5-.0024,Z0+.0024,Z1-.0024,.0046),
    section(LENGTH,WIDTH*.5-.0029,Z0+.0029,Z1-.0029,.0044)])
bevel(cap,'Front_Cap_Edge_Break',.0002,3,1,25.)

# Face inset is an opaque panel. The lowered dark mouth is merely a shallow
# visual recess for the game's muzzle flash anchor, with a closed backing.
panel=loft('Front_Inset_Panel',[
    section(LENGTH-.0003,WIDTH*.5-.0041,Z0+.0042,Z1-.0042,.0034),
    section(LENGTH+.00015,WIDTH*.5-.0041,Z0+.0042,Z1-.0042,.0034)],'Recess')
bevel(panel,'Panel_Edge_Break',.00018,3,-1,28.)

# An opaque, shallow inset circle completes the game-facing front silhouette.
# It ends immediately in a dark backing; no tube or internal assembly exists.
n=64
mouth_cut=loft('Front_CosmeticInset_Cutter',[
    [(x,.0074*math.cos(math.tau*i/n),.0074*math.sin(math.tau*i/n)) for i in range(n)]
    for x in (LENGTH-.0015,LENGTH+.003)],'Recess',True,cutters)
boolean(cap,mouth_cut);boolean(panel,mouth_cut)
mouth_rings=[(LENGTH+.00017,.0081),(LENGTH+.00055,.0078),
             (LENGTH+.00055,.0072),(LENGTH-.0012,.0072)]
verts=[(x,r*math.cos(math.tau*i/n),r*math.sin(math.tau*i/n)) for x,r in mouth_rings for i in range(n)]
faces=[]
for j in range(len(mouth_rings)-1):
    for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
faces.append(tuple((len(mouth_rings)-1)*n+i for i in range(n)))
mouth=mesh_object('Closed_Cosmetic_FrontInset',verts,faces)
for p in mouth.data.polygons:
    if p.index>=2*n:p.material_index=2

def disk_y(name,x,y,z,r,depth,region):
    n=48
    ring=[(x+r*math.cos(math.tau*i/n),z+r*math.sin(math.tau*i/n)) for i in range(n)]
    return prism_xz(name,ring,y-depth*.5,y+depth*.5,region)

for side in (-1,1):
    z=ZC-.009
    x=-.0015+collar_shift(z)
    y=side*(WIDTH*.5+.00085)
    seat=disk_y('Collar_Dark_FastenerSeat_'+str(side),x,y,z,.0027,.00025,'Recess')
    head=disk_y('Collar_Cosmetic_Fastener_'+str(side),x,y+side*.0002,z,.00215,.00055,'Trim')
    bevel(head,'Fastener_Edge_Break',.00015,3,-1,28.)
    # Dark, closed cross marks, not threaded fastener geometry.
    for orientation in (0,1):
        half_long=.00135;half_short=.00024
        points=[(-half_long,-half_short),(half_long,-half_short),(half_long,half_short),(-half_long,half_short)]
        if orientation:points=[(-b,a) for a,b in points]
        mark=[(x+a,z+b) for a,b in points]
        pos=y+side*.00050
        prism_xz('Fastener_Mark_%s_%s'%(side,orientation),mark,pos-.00004,pos+.00004,'Recess')

def planar_uv(mesh):
    if mesh.uv_layers.get('UV0'):mesh.uv_layers.remove(mesh.uv_layers['UV0'])
    uv=mesh.uv_layers.new(name='UV0')
    for p in mesh.polygons:
        normal=p.normal
        axis=max(range(3),key=lambda i:abs(normal[i]))
        for loop in p.loop_indices:
            v=mesh.vertices[mesh.loops[loop].vertex_index].co
            if axis==0:a,b=v.y,v.z
            elif axis==1:a,b=v.x,v.z
            else:a,b=v.x,v.y
            uv.data[loop].uv=(a/UV_METERS+.5,b/UV_METERS+.5)

def production_copy(source,segments):
    ob=source.copy();ob.data=source.data.copy();output.objects.link(ob)
    bpy.context.view_layer.objects.active=ob
    ob.select_set(True)
    for mod in list(ob.modifiers):
        if mod.type=='BEVEL':mod.segments=segments
        bpy.ops.object.modifier_apply(modifier=mod.name)
    mesh=ob.data
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for edge in bm.edges:
        edge.smooth=not edge.is_manifold or edge.calc_face_angle()<math.radians(38.)
    bm.to_mesh(mesh);bm.free()
    for p in mesh.polygons:p.use_smooth=True
    planar_uv(mesh)
    weighted=ob.modifiers.new('Broad_Plane_Normals','WEIGHTED_NORMAL')
    weighted.keep_sharp=True;weighted.weight=50
    bpy.ops.object.modifier_apply(modifier=weighted.name)
    return ob

def make_export(name,segments):
    bpy.ops.object.select_all(action='DESELECT')
    generated=[]
    for source in parts:
        ob=production_copy(source,segments)
        generated.append(ob)
        ob.select_set(False)
    for ob in generated:ob.select_set(True)
    bpy.context.view_layer.objects.active=generated[0]
    bpy.ops.object.join()
    ob=bpy.context.object;ob.name=name
    scene.cursor.location=(0,0,0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    mod=ob.modifiers.new('Export_Triangles','TRIANGULATE');mod.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    ob['GameProp']='RSH-12 muzzle brake game exterior; closed visual pockets'
    ob['SourceConcept']='RSH12_MuzzleBrake_Concept_v1.png'
    ob['ExclusiveWeapon']='ue_rsh12'
    ob['MountFrame']='Same local origin as existing RSH muzzle attachment'
    fbx=E/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE',path_mode='RELATIVE')
    return ob,fbx

model,fbx=make_export(MODEL,3)
glb=E/(MODEL+'.glb')
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
    export_texcoords=True,export_normals=True,export_tangents=True,export_materials='EXPORT')
lod,lod_fbx=make_export(MODEL+'_LOD1',1)
lod.hide_set(True);lod.hide_render=True

for name,loc in [('MountFace',(0,0,0)),('MuzzleExit',(LENGTH+.00055,0,0)),('ShroudContact',(rear_x,0,ZC))]:
    ob=bpy.data.objects.new(name,None);ob.empty_display_type='ARROWS'
    ob.empty_display_size=.012;ob.location=loc;guides.objects.link(ob)
construction.hide_viewport=True;construction.hide_render=True
cutters.hide_viewport=True;cutters.hide_render=True
for ob in cutters.objects:ob.hide_render=True;ob.display_type='WIRE'
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath:im.pack()
bpy.ops.object.select_all(action='DESELECT');model.select_set(True)
bpy.context.view_layer.objects.active=model
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            space.region_3d.view_location=Vector((LENGTH*.5,0,ZC))
            space.region_3d.view_distance=.36
            space.clip_start=.001
            space.shading.color_type='MATERIAL'
blend=O/'RSH12_MuzzleBrake_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))

# An optional assembly SOURCE, not a render or an engine replacement.
reference=collection('REFERENCE_RSH_Static_DoNotExport')
refmat=bpy.data.materials.new('REFERENCE_RSH_Grey')
refmat.diffuse_color=(.09,.10,.11,1.)
for part in raw:
    if part['name']=='10_l':continue
    mesh=bpy.data.meshes.new('REF_'+part['name'])
    mesh.from_pydata([from_gun@Vector(v) for v in part['verts']],[],part['faces']);mesh.update()
    mesh.materials.append(refmat)
    uv=mesh.uv_layers.new(name='UV0')
    for entry,value in zip(uv.data,part['uv']):entry.uv=value
    for p in mesh.polygons:p.use_smooth=True
    mesh.normals_split_custom_set([(from_gun.to_3x3()@Vector(n)).normalized() for n in part['normals']])
    ob=bpy.data.objects.new(mesh.name,mesh);reference.objects.link(ob);ob.hide_select=True
reference.hide_render=True
fit=O/'RSH12_MuzzleBrake_FitSource.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(fit))

report=dict(status='authored_and_exported',exclusive_weapon='ue_rsh12',proposed_option_id='rsh12_large_caliber_brake',
    model=MODEL,blend=str(blend),placement_source=str(fit),fbx=str(fbx),glb=str(glb),lod1_fbx=str(lod_fbx),
    art_scale_m=dict(forward_length=LENGTH,width=WIDTH,height=HEIGHT,center_z=ZC),
    triangles=len(model.data.polygons),vertices=len(model.data.vertices),lod1_triangles=len(lod.data.polygons),
    material_slots=[m.name for m in model.data.materials],texture_size=TEX,textures=maps,uv_physical_tile_m=UV_METERS,
    parts=[ob.name for ob in parts],finish_reference=finish,
    provenance='Original game exterior; RSH host contact contour derived from Rsh-12 by Medji, CC BY 4.0. Attribution: Docs/ThirdParty/RSH12-Medji-CCBY4.md',
    interface=dict(source_parts=['1_l','2_l','3_l'],pivot_source='same frame as existing RSH12HeavySuppressor game asset',
        source_shroud_contact_yz_local_m=contact,shroud_contact_x_m=rear_x,accessory_to_canonical_m=[list(row) for row in to_gun],
        mount_local_m=[0,0,0],muzzle_exit_local_m=[LENGTH+.00055,0,0],local_axes='+X forward / +Y right / +Z up'),
    references=[str(concept),str(S/'RSH12Integration20261003/canonical_parts.json')],
    reference_interpretation='Approved compact exterior with three side pockets per side and two roof recesses; shallow closed front inset; no internal mechanics',
    imported_to_ue=False,runtime_integrated=False,rendered=False,tested=False)
(O/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('RSH_MUZZLE_BRAKE_AUTHORED',json.dumps({k:report[k] for k in ('triangles','lod1_triangles','material_slots','blend','fbx','glb')}),flush=True)
