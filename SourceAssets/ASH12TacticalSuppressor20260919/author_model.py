"""Reference-inspired ASH-only oversized game suppressor exterior.

External cosmetic mesh only. +X points toward the muzzle; x=0 is the rear
mounting face used by the existing ASH viewmodel attachment transform.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

O = Path(__file__).resolve().parent
T = O / 'Textures'
T.mkdir(exist_ok=True)
LENGTH = .260
N = 192
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.
materials = []
maps = {}


def smooth_array(a, b, x):
    w = np.clip((x-a)/(b-a), 0., 1.)
    return w*w*(3.-2.*w)


def pocket(x, theta):
    angle = (theta + math.pi/8.) % (math.pi/4.) - math.pi/8.
    along = max(abs(x-.180)-.048, 0.)
    sdf = math.sqrt(along*along + (.0375*angle)**2) - .0045
    w = max(0., min(1., (.0009-sdf)/.0018))
    return w*w*(3.-2.*w)


def write_image(name, rgb, srgb=False):
    size = rgb.shape[0]
    img = bpy.data.images.new(name, width=size, height=size, alpha=True)
    img.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    pixels = np.ones((size, size, 4), dtype=np.float32)
    pixels[:, :, :3] = rgb
    img.pixels.foreach_set(pixels.ravel())
    img.filepath_raw = str(T / (name+'.png'))
    img.file_format = 'PNG'
    img.save()
    return img


def material(part, color, roughness, metal):
    size = 2048
    v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
    rng = np.random.default_rng(3127 + len(materials))
    grain = rng.random((size,size), dtype=np.float32) - .5
    slow = np.sin(u*31.7 + np.sin(v*19.))*np.sin(v*47.3-u*9.1)
    height = grain*.0000025 + np.sin(v*math.tau*420.)*.0000008
    ao = np.ones((size,size),dtype=np.float32)
    if part == 'Shell':
        theta = v*math.tau
        angle = (theta+math.pi/8.) % (math.pi/4.) - math.pi/8.
        sdf = np.sqrt(np.maximum(np.abs(u*LENGTH-.180)-.048,0.)**2 + (.0375*angle)**2)-.0045
        ao -= .22*(1.-smooth_array(-.0009,.0009,sdf))
    rough = np.clip(roughness + grain*.045 + slow*.015, .06, .95)
    base = np.array(color,dtype=np.float32)[None,None,:]*(1.+grain[:,:,None]*.045+slow[:,:,None]*.035)
    # Store the authored linear coat in an sRGB color PNG.
    base = np.where(base <= .0031308, 12.92*base, 1.055*np.maximum(base,0.)**(1/2.4)-.055)
    color_img = write_image('T_ASH12_Tac_'+part+'_BaseColor',np.clip(base,0,1),True)
    orm = np.stack((ao,rough,np.full_like(rough,metal)),axis=2)
    orm_img = write_image('T_ASH12_Tac_'+part+'_ORM',orm)
    dx = (np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(2.*LENGTH/size)
    dy = (np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(2.*.24/size)
    normal = np.stack((-dx,-dy,np.ones_like(dx)),axis=2)
    normal /= np.linalg.norm(normal,axis=2)[:,:,None]
    gl = write_image('T_ASH12_Tac_'+part+'_NormalGL',normal*.5+.5)
    normal[:,:,1] *= -1.
    normal_dx = write_image('T_ASH12_Tac_'+part+'_NormalDX',normal*.5+.5)
    m = bpy.data.materials.new('ASH12Tac_'+part)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    col = nodes.new('ShaderNodeTexImage'); col.image = color_img
    packed = nodes.new('ShaderNodeTexImage'); packed.image = orm_img
    sep = nodes.new('ShaderNodeSeparateColor')
    links.new(col.outputs['Color'],bsdf.inputs['Base Color'])
    links.new(packed.outputs['Color'],sep.inputs['Color'])
    links.new(sep.outputs['Green'],bsdf.inputs['Roughness'])
    links.new(sep.outputs['Blue'],bsdf.inputs['Metallic'])
    tex = nodes.new('ShaderNodeTexImage'); tex.image = gl
    norm = nodes.new('ShaderNodeNormalMap')
    links.new(tex.outputs['Color'],norm.inputs['Color'])
    links.new(norm.outputs['Normal'],bsdf.inputs['Normal'])
    materials.append(m)
    maps[part] = {'base_color':color_img.filepath_raw,'orm':orm_img.filepath_raw,'normal':normal_dx.filepath_raw}
    return m


material('Shell',(.090,.095,.103),.46,.65)
material('Band',(.245,.190,.125),.52,.68)
material('Mount',(.044,.048,.055),.38,.80)
inner = bpy.data.materials.new('ASH12Tac_Inner')
inner.use_nodes = True
inner.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.006,.007,.008,1)
inner.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.90
inner.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=.05
materials.append(inner)
parts = []


def revolve(name, profile, mat, deformation=None):
    vertices, faces, uv_faces = [], [], []
    for x,r in profile:
        for j in range(N):
            theta = math.tau*j/N
            radius = deformation(x,r,theta) if deformation else r
            vertices.append((x,radius*math.cos(theta),radius*math.sin(theta)))
    for i in range(len(profile)-1):
        for j in range(N):
            k=(j+1)%N
            # Profile runs rear to front along +X; this winding faces out.
            faces.append((i*N+j,i*N+k,(i+1)*N+k,(i+1)*N+j))
            if abs(profile[i+1][0]-profile[i][0]) < 1e-7:
                uv_faces.append(tuple((.5+vertices[index][1]/.084,.5+vertices[index][2]/.084) for index in faces[-1]))
            else:
                uv_faces.append(((profile[i][0]/LENGTH,j/N),(profile[i][0]/LENGTH,(j+1)/N),
                                 (profile[i+1][0]/LENGTH,(j+1)/N),(profile[i+1][0]/LENGTH,j/N)))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    uv=mesh.uv_layers.new(name='UV0')
    for poly,coords in zip(mesh.polygons,uv_faces):
        poly.use_smooth=True
        for loop,xy in zip(poly.loop_indices,coords):uv.data[loop].uv=xy
    obj=bpy.data.objects.new(name,mesh)
    scene.collection.objects.link(obj)
    mesh.materials.append(mat)
    parts.append(obj)
    return obj


# Large smooth shell with eight real shallow, capsule-ended longitudinal cuts.
body_profile=[(.075,.039),(.080,.0395),(.085,.0385),(.090,.0375)]
body_profile += [(float(x),.0375) for x in np.linspace(.093,.245,82)]
body_profile += [(.250,.0370),(.254,.0358),(.257,.0340),(.260,.0318),
                 (.260,.0105),(.253,.0105)]
revolve('FlutedShell',body_profile,materials[0],lambda x,r,t:r-.0018*pocket(x,t) if .090<x<.249 else r)

# Broad bronze-toned grip sleeve. The diagonal ridges are actual surface
# geometry; the normal map only adds fine finish grain.
band_profile=[(.018,.0355),(.020,.0394),(.023,.0410)]
band_profile += [(float(x),.041) for x in np.linspace(.024,.073,27)]
band_profile += [(.076,.0407),(.079,.0395),(.080,.0385)]
def knurl(x,r,theta):
    fade=smooth_array(.020,.025,x)*(1.-smooth_array(.071,.077,x))
    phase=48.*(theta-(x-.024)*8.)
    return r-.0009*float(fade)*(.5+.5*math.cos(phase))
revolve('DiagonalSleeve',band_profile,materials[1],knurl)

# Cosmetic rear cap and stepped installation collar, referenced to x=0.
revolve('RearCap',[(.004,.013),(.004,.031),(.006,.0355),(.010,.0365),(.016,.0365),(.019,.0355)],materials[2])
revolve('RearTrim',[(.016,.0358),(.017,.0370),(.019,.0370),(.021,.0358)],materials[2])
revolve('MountCollar',[(0.,.011),(0.,.015),(.002,.017),(.009,.017),(.012,.0155)],materials[2])
revolve('FrontLip',[(.254,.0358),(.255,.0360),(.257,.0343),(.258,.0338)],materials[2])
# Short blind dark recess for the game silhouette, with no internal mechanism.
revolve('DarkFrontRecess',[(.2598,.01045),(.249,.01045),(.249,.00015)],materials[3])

construction=bpy.data.collections.new('EditableConstruction')
scene.collection.children.link(construction)
for obj in parts:
    source=obj.copy();source.data=obj.data.copy();source.name='SRC_'+obj.name
    construction.objects.link(source);source.hide_render=True;source.hide_viewport=True
bpy.ops.object.select_all(action='DESELECT')
for obj in parts:obj.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.object.join()
model=bpy.context.object
model.name='SM_ASH12_TacticalSuppressor'
scene.cursor.location=(0,0,0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
# Keep construction objects/material names in the editable source; output is
# one static attachment with three exterior regions plus its matte aperture.
edge_faces={}
for poly in model.data.polygons:
    for key in poly.edge_keys:edge_faces.setdefault(tuple(sorted(key)),[]).append(poly.normal.copy())
for edge in model.data.edges:
    normals=edge_faces.get(tuple(sorted(edge.vertices)),[])
    edge.use_edge_sharp=len(normals)==2 and normals[0].dot(normals[1]) < math.cos(math.radians(55.))
weighted=model.modifiers.new('AreaWeightedNormals','WEIGHTED_NORMAL')
weighted.keep_sharp=True
bpy.ops.object.modifier_apply(modifier=weighted.name)
tri=model.modifiers.new('ExportTriangulation','TRIANGULATE')
bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.ops.export_scene.fbx(filepath=str(O/'SM_ASH12_TacticalSuppressor.fbx'),
    use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    add_leaf_bones=False,bake_anim=False,use_tspace=True)

# Required production UI icon: actual model, muzzle forward to screen left,
# transparent 1024-square image. No inspection/acceptance render is produced.
scene.render.engine='CYCLES'
scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024
scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('NeutralIconWorld')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.12,.12,.12,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
center=Vector((LENGTH*.5,0,0))
camera_data=bpy.data.cameras.new('AttachmentIconCamera')
camera=bpy.data.objects.new('AttachmentIconCamera',camera_data)
scene.collection.objects.link(camera)
camera.location=center+Vector((0,.7,0))
camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO';camera_data.ortho_scale=LENGTH/.83
scene.camera=camera
for i,(location,energy,size) in enumerate([((.12,.26,.35),18,.35),((.00,-.18,.15),12,.25),((.35,.10,-.12),7,.22)]):
    data=bpy.data.lights.new('IconArea'+str(i),'AREA');data.energy=energy;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj)
    obj.location=location;obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(O/'ue_ash12_muzzle_ash12_tactical_suppressor.png')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ASH12_TacticalSuppressor_Editable.blend'))
bpy.ops.render.render(write_still=True)
report={'mesh':'SM_ASH12_TacticalSuppressor','fbx':str(O/'SM_ASH12_TacticalSuppressor.fbx'),
        'length_m':LENGTH,'max_diameter_m':.082,'triangles':len(model.data.polygons),
        'axis':'+X forward / +Z up','pivot':'rear mount plane at x=0',
        'reference':'Reference/user_suppressor.png','parts':['FlutedShell','DiagonalSleeve','RearCap','MountCollar','FrontLip','DarkFrontRecess'],
        'textures':maps,'icon':scene.render.filepath,'exclusive_weapon':'ue_ash12',
        'visual_test':'Not performed. Production icon rendered as a UI asset only.'}
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('ASH12_SUPPRESSOR_AUTHOR_COMPLETE '+json.dumps(report))
