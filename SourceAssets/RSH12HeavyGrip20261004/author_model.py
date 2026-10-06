"""RSH heavy rear grip exterior: retained contact shell and a sculpted heel.

Game-art authoring only. Keeps the host's upper grip UVs, split normals and
coordinates. Writes editable sources, exports, materials and assembly frame.
Does not alter the live gun, catalog, skeletal meshes or hand animation.
"""
import json
import math
import shutil
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

O = Path(__file__).resolve().parent
S = O.parent
E = O / 'Exports'
T = O / 'Textures'
for d in (E, T): d.mkdir(exist_ok=True)
raw = json.loads((S/'RSH12Integration20261003/canonical_parts.json').read_text())
grip = next(p for p in raw if p['name'] == '9_l')
surface_source = json.loads((S/'RSH12GripSurfaces20261004/authoring.json').read_text())
component = Matrix(surface_source['canonical_to_component_m'])
finish = json.loads((S/'RSH12Optics20261004/finish_reference.json').read_text())
panels = json.loads((O/'panel_inputs.json').read_text())['panels']
source_textures = S/'RSH12Integration20261003/Original/Extracted/textures'
ZCUT = -.0645
TEX = 2048
UV_METERS = .10
MODEL = 'SM_RSH12_HeavyGrip'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.

def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

construction = collection('EDITABLE_HeavyGrip_Parts')
export_collection = collection('GAME_Exports')
reference = collection('REFERENCE_Host_DoNotExport')
guides = collection('INTERFACE_OriginalGrip')
materials = {}
maps = {}

def new_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    n, l = m.node_tree.nodes, m.node_tree.links
    p = n.new('ShaderNodeBsdfPrincipled')
    out = n.new('ShaderNodeOutputMaterial')
    l.new(p.outputs['BSDF'], out.inputs['Surface'])
    return m, n, l, p

def host_material():
    m,n,l,p = new_material('RSH12HeavyGrip_OriginalContactShell')
    copied = {}
    for suffix, socket, space in [('albedo.jpg','Base Color','sRGB'),
                                  ('roughness.jpg','Roughness','Non-Color'),
                                  ('metallic.jpg','Metallic','Non-Color'),
                                  ('normal.png',None,'Non-Color')]:
        src = source_textures/('DefaultMaterial_'+suffix)
        dst = T/('T_RSH12_Original_'+suffix)
        if not dst.exists(): shutil.copy2(src,dst)
        im = bpy.data.images.load(str(dst),check_existing=True)
        im.colorspace_settings.name = space
        tex = n.new('ShaderNodeTexImage'); tex.image=im
        if socket: l.new(tex.outputs['Color'],p.inputs[socket])
        else:
            nm = n.new('ShaderNodeNormalMap'); nm.uv_map='UV0'
            l.new(tex.outputs['Color'],nm.inputs['Color'])
            l.new(nm.outputs['Normal'],p.inputs['Normal'])
        copied[suffix]=str(dst.relative_to(O))
    maps['OriginalContactShell']=copied
    materials['Original']=m
    return m

def save_image(name, rgb, srgb=False):
    h,w=rgb.shape[:2]
    im=bpy.data.images.new(name,width=w,height=h,alpha=True)
    im.colorspace_settings.name='sRGB' if srgb else 'Non-Color'
    rgba=np.ones((h,w,4),dtype=np.float32);rgba[:,:,:3]=rgb
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw=str(T/(name+'.png'));im.file_format='PNG';im.save()
    return im

def texture_material(name,color,rough,metal,seed,rubber=False):
    rng=np.random.default_rng(seed)
    grain=rng.random((TEX,TEX),dtype=np.float32)-.5
    v,u=np.mgrid[0:TEX,0:TEX].astype(np.float32)/TEX
    coarse=(np.sin(u*47.+np.sin(v*23.))*np.cos(v*69.)+np.sin(v*101.+u*17.))*.5
    scratches=np.zeros_like(u)
    if not rubber:
        for _ in range(160):
            xy=rng.uniform(0,TEX,2);angle=rng.uniform(0,math.tau);length=rng.uniform(2,22)
            points=xy[None,:]+np.linspace(0,length,int(length*2)+1)[:,None]*np.array([math.cos(angle),math.sin(angle)])
            scratches[points[:,1].astype(int)%TEX,points[:,0].astype(int)%TEX]=rng.uniform(.04,.19)
    base=np.asarray(color,dtype=np.float32)[None,None,:]*(1+grain[:,:,None]*.09+coarse[:,:,None]*.04)
    base=base*(1-scratches[:,:,None])+np.array([.13,.135,.14])*scratches[:,:,None]
    height=grain*(.000009 if rubber else .0000012)+coarse*.000001-scratches*.000008
    if rubber:
        # Closely spaced rounded micrograin; texture-only, the palm silhouette stays fixed.
        dots=(np.sin(u*math.tau*153)*np.sin(v*math.tau*151))
        height+=np.maximum(dots,0)**2*.000027
    du=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*UV_METERS/TEX)
    dv=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*UV_METERS/TEX)
    normal=np.stack((-du,-dv,np.ones_like(u)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    rough_map=np.clip(rough+grain*.065+coarse*.022-scratches*.1,.1,.95)
    srgb=np.where(base<=.0031308,base*12.92,1.055*np.maximum(base,0)**(1/2.4)-.055)
    prefix='T_RSH12_HeavyGrip_'+name
    bc=save_image(prefix+'_BaseColor',np.clip(srgb,0,1),True)
    orm=save_image(prefix+'_ORM',np.stack((np.ones_like(u),rough_map,np.full_like(u,metal)),axis=-1))
    ng=save_image(prefix+'_NormalGL',normal*.5+.5)
    normal[:,:,1]*=-1
    nd=save_image(prefix+'_NormalDX',normal*.5+.5)
    m,n,l,p=new_material('RSH12HeavyGrip_'+name);m.diffuse_color=(*color,1)
    for im,socket in [(bc,'Base Color'),(orm,None),(ng,'Normal')]:
        t=n.new('ShaderNodeTexImage');t.image=im
        if socket=='Base Color': l.new(t.outputs['Color'],p.inputs[socket])
        elif socket=='Normal':
            nm=n.new('ShaderNodeNormalMap');nm.uv_map='UV0'
            l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
        else:
            sep=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sep.inputs['Color'])
            l.new(sep.outputs['Green'],p.inputs['Roughness']);l.new(sep.outputs['Blue'],p.inputs['Metallic'])
    maps[name]={key:str(Path(im.filepath_raw).relative_to(O)) for key,im in [('base_color',bc),('orm',orm),('normal_gl',ng),('normal_dx',nd)]}
    materials[name]=m
    return m

host=host_material()
metal=texture_material('GraphiteHeel',tuple(finish['base_color']),.44,1.,127042)
rubber=texture_material('RubberPanel',(.012,.014,.015),.72,0.,127043,True)
trim,n,l,p=new_material('RSH12HeavyGrip_EdgeAndSpine')
p.inputs['Base Color'].default_value=(.065,.069,.075,1)
p.inputs['Roughness'].default_value=.38;p.inputs['Metallic'].default_value=1
materials['Trim']=trim
seam,n,l,p=new_material('RSH12HeavyGrip_Recess')
p.inputs['Base Color'].default_value=(.004,.005,.006,1)
p.inputs['Roughness'].default_value=.85
materials['Seam']=seam

def mesh(name,verts,faces,mat,uv=None,normals=None,dest=construction):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces);data.update()
    data.materials.append(mat)
    layer=data.uv_layers.new(name='UV0')
    if uv is not None:
        for dst,value in zip(layer.data,uv):dst.uv=value
    else:
        for face in data.polygons:
            axis=max(range(3),key=lambda k:abs(face.normal[k]))
            axes=[k for k in range(3) if k!=axis]
            for li in face.loop_indices:
                co=data.vertices[data.loops[li].vertex_index].co
                layer.data[li].uv=(co[axes[0]]/UV_METERS,co[axes[1]]/UV_METERS)
    for face in data.polygons:face.use_smooth=True
    if normals is not None:data.normals_split_custom_set(normals)
    ob=bpy.data.objects.new(name,data);dest.objects.link(ob)
    return ob

def cut_height(y):return ZCUT+.035*(y-.15)

def clip(poly,extra=0.):
    """Clip tuples (position, corner UV, corner normal); interpolate attributes."""
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=a[0].z-cut_height(a[0].y)-extra
        db=b[0].z-cut_height(b[0].y)-extra
        if da>=0:result.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db)
            result.append((a[0].lerp(b[0],t),a[1].lerp(b[1],t),a[2].lerp(b[2],t).normalized()))
    return result

V=[];F=[];UV=[];N=[];lookup={};cut_points={};cursor=0
for face in grip['faces']:
    poly=[(Vector(grip['verts'][idx]),Vector(grip['uv'][cursor+k]),Vector(grip['normals'][cursor+k])) for k,idx in enumerate(face)]
    cursor+=len(face)
    out=clip(poly)
    if len(out)<3:continue
    face_indices=[]
    for co,uv,no in out:
        key=tuple(round(x,10) for x in co)
        if key not in lookup:lookup[key]=len(V);V.append(tuple(co))
        face_indices.append(lookup[key]);UV.append(tuple(uv));N.append(tuple(no))
        if abs(co.z-cut_height(co.y))<1e-8:cut_points[key]=co.copy()
    F.append(face_indices)
body=mesh('01_Retained_ContactShell',V,F,host,UV,N)
body['preserved']='Original interface, tang, trigger clearance, palm and finger curves; UV0 and corner normals retained above heel seam'
shell_rubber=rubber.copy();shell_rubber.name='RSH12HeavyGrip_RubberContactShell'
uvmap=shell_rubber.node_tree.nodes.new('ShaderNodeUVMap');uvmap.uv_map='UV1'
for node in shell_rubber.node_tree.nodes:
    if node.type=='TEX_IMAGE':shell_rubber.node_tree.links.new(uvmap.outputs['UV'],node.inputs['Vector'])
    elif node.type=='NORMAL_MAP':node.uv_map='UV1'
shell_uv=body.data.uv_layers.new(name='UV1')
for face in body.data.polygons:
    axis=max(range(3),key=lambda k:abs(face.normal[k]));axes=[k for k in range(3) if k!=axis]
    for li in face.loop_indices:
        co=body.data.vertices[body.data.loops[li].vertex_index].co
        shell_uv.data[li].uv=(co[axes[0]]/UV_METERS,co[axes[1]]/UV_METERS)
body.data.materials[0]=shell_rubber

# A ring from the actual source cut defines all heel transitions.
ring=list(cut_points.values())
center=sum(ring,Vector())/len(ring)
ring.sort(key=lambda p:math.atan2(p.y-center.y,p.x-center.x))

def ring_at(drop,sx=1.,sy=1.):
    return [Vector((center.x+(p.x-center.x)*sx,center.y+(p.y-center.y)*sy,p.z-drop)) for p in ring]

def loft(name,rings,mat,caps=True):
    count=len(rings[0]);verts=[tuple(v) for r in rings for v in r];faces=[]
    for a in range(len(rings)-1):
        for k in range(count):faces.append((a*count+k,(a+1)*count+k,(a+1)*count+(k+1)%count,a*count+(k+1)%count))
    if caps:faces.extend([tuple(range(count)),tuple(reversed([(len(rings)-1)*count+k for k in range(count)]))])
    ob=mesh(name,verts,faces,mat)
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    # Broad lower panels remain flat; rounded source corners inherit their ring shape.
    for face in ob.data.polygons:face.use_smooth=False
    return ob

joint=loft('02_RubberToMetal_Seam',[ring_at(-.00003),ring_at(.00045,1.005,1.003)],seam)
shoulder=loft('03_Continuous_HeelShoulder',[ring_at(.00045,1.005,1.003),ring_at(.00125,1.035,1.012),ring_at(.00335,1.07,1.024)],metal)
rim=loft('04_Satin_HeelRim',[ring_at(.00335,1.07,1.024),ring_at(.00380,1.072,1.025),ring_at(.00425,1.07,1.024)],trim)
base=loft('05_Weighted_HeelShoe',[ring_at(.00425,1.07,1.024),ring_at(.0051,1.075,1.028),ring_at(.0185,1.12,1.060),ring_at(.0208,1.075,1.027)],metal)
sole=loft('06_HeelSole',[ring_at(.0208,1.075,1.027),ring_at(.02125,1.065,1.020)],seam)
for ob in (shoulder,rim,base):
    bevel=ob.modifiers.new('Soft_Machined_Edges','BEVEL');bevel.width=.00030;bevel.segments=3
    bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(16);bevel.harden_normals=True

bvh=BVHTree.FromPolygons([Vector(v) for v in grip['verts']],grip['faces'])
# Preserve the native anti-slip skin's side boundaries and screw holes; clip
# only the bottom to stay above the new metal shoulder. Same physical UVs.
PV=[];PF=[];PUV=[];PN=[]
for panel in panels:
    side=panel['side'];slope=panel['slope_y_from_z'];scale=math.sqrt(1+slope*slope)
    points=[]
    for idx,(y,z) in enumerate(panel['positions_yz']):
        hit,normal,_,_=bvh.ray_cast(Vector((side*.055,y,z)),Vector((-side,0,0)))
        if hit is None:raise RuntimeError('Source contact domain has no surface')
        points.append((hit,Vector(((y-slope*z)/(.1*scale),(slope*y+z)/(.1*scale))),normal))
    local_v=[];local_uv=[];local_f=[];indices={}
    for triangle in panel['triangles_ccw']:
        out=clip([points[i] for i in (triangle if side>0 else triangle[::-1])],.0014)
        if len(out)<3:continue
        face=[]
        for co,uv,no in out:
            key=tuple(round(v,10) for v in co)
            if key not in indices:indices[key]=len(local_v);local_v.append(co);local_uv.append(uv)
            face.append(indices[key])
        local_f.append(face)
    count=len(local_v);start=len(PV);edges={};directions={}
    boundaries=[panel['boundary_yz'],*panel['holes_yz']]
    segments=[(Vector(a),Vector(b)) for loop in boundaries for a,b in zip(loop,loop[1:])]
    for backing in (False,True):
        for co in local_v:
            pt=Vector((co.y,co.z));distance=1.
            for a,b in segments:
                edge=b-a;t=max(0.,min(1.,(pt-a).dot(edge)/max(edge.length_squared,1e-16)))
                distance=min(distance,(pt-a-edge*t).length)
            blend=min(1.,distance/.0012);blend=blend*blend*(3-2*blend)
            offset=.00004 if backing else .000065+.000135*blend
            PV.append(tuple(co+Vector((side*offset,0,0))))
    for f in local_f:
        PF.append([start+i for i in f]);PUV.extend(local_uv[i] for i in f)
        PN.extend([(side,0,0)]*len(f))
        PF.append([start+count+i for i in reversed(f)]);PUV.extend(local_uv[i] for i in reversed(f))
        PN.extend([(-side,0,0)]*len(f))
        for a,b in zip(f,f[1:]+f[:1]):
            key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1;directions[key]=(a,b)
    for edge,n in edges.items():
        if n==1:
            a,b=directions[edge];PF.append([start+b,start+a,start+count+a,start+count+b]);PUV.extend([local_uv[b],local_uv[a],local_uv[a],local_uv[b]])
            delta=local_v[b]-local_v[a];normal=Vector((0,delta.z,-delta.y)).normalized()*side
            PN.extend([tuple(normal)]*4)
surface=mesh('07_Replaceable_AntiSlip_Surface',PV,PF,rubber,PUV,PN)
surface['compatible_finishes']='pistol_grip_granular / pistol_grip_diamond / pistol_grip_quickdot'
surface['material_policy']='Independent surface export; never apply rubber to heel, screw or metal frame'

# Slim rear accent follows the native curve and adds only shallow surface relief.
SV=[];SF=[]
rows=35;cols=5
for j in range(rows):
    z=ZCUT+.001+(0.013-ZCUT-.001)*j/(rows-1)
    for i in range(cols):
        x=-.0026+.0052*i/(cols-1)
        hit,no,_,_=bvh.ray_cast(Vector((x,.25,z)),Vector((0,-1,0)))
        if hit is None:raise RuntimeError('Rear accent outside original grip')
        edge=min(i,cols-1-i)/2
        SV.append(tuple(hit+Vector((0,.000055+.00008*edge,0))))
for j in range(rows-1):
    for i in range(cols-1):
        a=j*cols+i;SF.append((a,a+1,a+1+cols,a+cols))
spine=mesh('08_Flush_RearSpine',SV,SF,metal)
solid=spine.modifiers.new('Closed_Shallow_Accent','SOLIDIFY');solid.thickness=.000045;solid.offset=-1
spine['contact']='Follows original rear surface; shallow decorative accent'

parts=[body,joint,shoulder,rim,base,sole,spine]
for side in (-1,1):
    hit,_,_,_=bvh.ray_cast(Vector((side*.055,.151,-.046)),Vector((-side,0,0)))
    # A shallow closed cosmetic disk: only exterior prop detail.
    for label,radius,depth,offset,mat in [('Seat',.00305,.00009,.00004,seam),('Rim',.00255,.00012,.00012,trim),('Head',.00195,.00010,.00019,metal)]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=40,radius=radius,depth=depth,location=hit+Vector((side*offset,0,0)),rotation=(0,math.pi/2,0))
        ob=bpy.context.object;ob.name=f'09_CosmeticFastener_{side}_{label}'
        for c in list(ob.users_collection):c.objects.unlink(ob)
        construction.objects.link(ob);ob.data.materials.append(mat)
        ob.data.uv_layers.active.name='UV0'
        bevel=ob.modifiers.new('Rounded_Head_Edge','BEVEL');bevel.width=.00007;bevel.segments=2
        parts.append(ob)

def export_object(name,objects,matrix=None):
    bpy.ops.object.select_all(action='DESELECT')
    copies=[]
    for src in objects:
        ob=src.copy();ob.data=src.data.copy();export_collection.objects.link(ob)
        ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
        for mod in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
        ob.select_set(False);copies.append(ob)
    for ob in copies:ob.select_set(True)
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join()
    ob=bpy.context.object;ob.name=name
    if matrix is not None:ob.data.transform(matrix)
    tri=ob.modifiers.new('Export_Triangulate','TRIANGULATE');tri.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=tri.name)
    fbx=E/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='RELATIVE')
    ob.hide_set(True);ob.hide_render=True
    return ob

main=export_object(MODEL,parts,component)
skin=export_object(MODEL+'_Surface', [surface],component)
assembly=export_object(MODEL+'_Canonical',[*parts,surface])
assembly.hide_set(False);assembly.hide_render=False
bpy.ops.object.select_all(action='DESELECT');assembly.select_set(True);bpy.context.view_layer.objects.active=assembly
bpy.ops.export_scene.gltf(filepath=str(E/(MODEL+'.glb')),export_format='GLB',use_selection=True,export_texcoords=True,export_normals=True,export_tangents=True,export_materials='EXPORT')
assembly.hide_set(True);assembly.hide_render=True

for part in raw:
    if part['name'] in ('9_l','10_l'):continue
    ref=mesh('REF_'+part['name'],part['verts'],part['faces'],host,part['uv'],part['normals'],reference)
    ref.hide_select=True
with bpy.data.libraries.load(str(S/'RSH12CubeSuppressor20261004/RSH12_CubeSuppressor_Long_Editable.blend'),link=False) as (src,dst):
    dst.objects=['SM_RSH12_CubeSuppressor_Long']
cube=dst.objects[0];reference.objects.link(cube)
cube.name='REF_Approved_CubeSuppressor'
cube.matrix_world=Matrix(json.loads((S/'RSH12CubeSuppressor20261004/authoring.json').read_text())['interface']['accessory_to_canonical_m'])
cube.hide_render=False;cube.hide_set(False);cube.hide_select=True
reference.hide_render=True;reference.hide_viewport=True
for name,co in [('Source_Grip_Origin',(0,0,0)),('Heel_SourceSection',center),('Canonical_to_Component',component.translation)]:
    ob=bpy.data.objects.new(name,None);guides.objects.link(ob);ob.location=co;ob.empty_display_size=.007
guides.hide_render=True
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath:im.pack()
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_location=Vector((0,.145,-.025))
            area.spaces.active.region_3d.view_distance=.22
            area.spaces.active.clip_start=.001
blend=O/'RSH12_HeavyGrip_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))

record=dict(status='model_authored_and_exported',exclusive_weapon='ue_rsh12',proposed_option_id='rsh12_heavy_grip',
    concept='Reference/RSH12_HeavyGrip_Concept.png',concept_tool='built-in image_gen',blend=str(blend),
    fbx=str(E/(MODEL+'.fbx')),surface_fbx=str(E/(MODEL+'_Surface.fbx')),glb=str(E/(MODEL+'.glb')),
    triangles=len(main.data.polygons),surface_triangles=len(skin.data.polygons),
    assembly_triangles=len(assembly.data.polygons),material_slots=[m.name for m in main.data.materials],
    texture_size=TEX,textures=maps,texture_tile_m=UV_METERS,
    source_part='9_l',source=str(S/'RSH12Integration20261003/canonical_parts.json'),
    interface=dict(canonical_axes='+X lateral / -Y forward / +Z up',canonical_to_component_m=[list(r) for r in component],
        export_frame='same native component reference as accepted RSH grip surfaces',bone='WPN_root',
        runtime_binding='reuse RSH native component-to-WPN_root binding; no additional artist offset',
        retained_region='all original grip geometry above the lower heel seam',source_heel_ring=[list(p) for p in ring],
        original_grip_section='9_l must be hidden/replaced during later integration',surface_export='separate mesh; existing skin cannot be reused below the metal seam'),
    author_parts=[p.name for p in [*parts,surface]],
    provenance='Upper contact shell derived from Rsh-12 by Medji, CC BY 4.0; new heel/spine/PBR authored for this game. See Docs/ThirdParty/RSH12-Medji-CCBY4.md',
    scope='Exterior game model and images; no functional internals',
    ue_imported=False,runtime_integrated=False,animation_changed=False,catalog_changed=False,gameplay_tested=False)
(O/'authoring.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print('RSH_HEAVY_GRIP_AUTHORED',json.dumps({k:record[k] for k in ('triangles','surface_triangles','assembly_triangles','blend','fbx','glb')}),flush=True)
