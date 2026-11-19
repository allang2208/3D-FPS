"""Create editable native-topology Jason morph and actual source-model previews."""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from muscle_shape import MuscleShape,neck_seam
from leg_proportions import LegProportions

OUT = Path(globals().get('variant_output','D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117/R2_LongLegs'))
BLEND_NAME=globals().get('variant_blend_name','Jason_StrongTall_R2')
ShapeClass=globals().get('variant_shape_class',MuscleShape)
OUT.mkdir(parents=True,exist_ok=True)
PREVIEW = OUT / 'Previews'
PREVIEW.mkdir(exist_ok=True)
DRAFT='--geometry-draft' in sys.argv
if DRAFT:
    snapshot=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/SetFitReview20261115/Captured/Jason_body.json').read_text())
    body=snapshot['source_model']
    body['triangle_uvs']=body['uv']
    body['materials']=[{'slot':slot,'asset':asset} for slot,asset in zip(body['material_slots'],body['materials'])]
    body['skeleton']=snapshot['skeleton']
    head=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/JasonPlayer20261003/head_geometry.json').read_text())
    head['source']='/Game/AsianMale_Jason/Mesh/Head/SKM_Jason_head.SKM_Jason_head'
    head['triangle_materials']=[0]*len(head['triangles'])
    head['triangle_uvs']=[[[0,0]]*3]*len(head['triangles'])
    inputs={}
else:
    body = json.loads((OUT/'body_source.json').read_text())
    head = json.loads((OUT/'head_source.json').read_text())
    inputs = json.loads((OUT/'material_inputs.json').read_text())
seam=neck_seam(body)
(OUT/'neck_seam.json').write_text(json.dumps(seam,separators=(',',':')))
morph = ShapeClass(body['bones'],seam_segments=seam)
proportions=LegProportions(body['bones'])
tall_basis=[proportions.point(p) for p in body['positions']]
strong = [proportions.deform(p,morph.deform(p, w)) for p, w in zip(body['positions'], body['weights'])]
(OUT/'strong_positions.json').write_text(json.dumps(strong, separators=(',', ':')))

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.cycles.device = 'CPU'
scene.render.resolution_x = 1800
scene.render.resolution_y = 1350
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.12,.14,.18,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35
scene.view_settings.view_transform = 'AgX'

material_cache = {}
def tex_node(nodes, file, noncolor=False):
    node = nodes.new('ShaderNodeTexImage')
    node.image = bpy.data.images.load(file, check_existing=True)
    if max(node.image.size)>4096:
        ratio=4096/max(node.image.size)
        node.image.scale(round(node.image.size[0]*ratio),round(node.image.size[1]*ratio))
    if noncolor:
        node.image.colorspace_settings.name = 'Non-Color'
    return node

def material(path):
    if path in material_cache:
        return material_cache[path]
    mat = bpy.data.materials.new(path.rsplit('/',1)[-1].split('.')[0])
    mat.use_nodes = True
    mat['unreal_material'] = path
    n, l = mat.node_tree.nodes, mat.node_tree.links
    n.clear()
    bs = n.new('ShaderNodeBsdfPrincipled')
    output=n.new('ShaderNodeOutputMaterial')
    l.new(bs.outputs[0],output.inputs['Surface'])
    bs.inputs['Base Color'].default_value = (.42,.42,.42,1) if DRAFT else (.32,.18,.12,1)
    bs.inputs['Roughness'].default_value = .56
    bs.inputs['Specular IOR Level'].default_value = .30
    bs.inputs['Subsurface Weight'].default_value = .065
    bs.inputs['Subsurface Radius'].default_value = (1., .40, .20)
    bs.inputs['Subsurface Scale'].default_value = .012
    textures = inputs.get(path, {}).get('textures', {})
    color = textures.get('Basecolor Baked')
    if not color or 'file' not in color:
        color = next((v for k,v in textures.items() if 'file' in v and any(s in k.lower() for s in ('diffuse','albedo','basecolor','base color'))), None)
    if color and 'file' in color:
        t = tex_node(n, color['file'])
        l.new(t.outputs['Color'], bs.inputs['Base Color'])
    srmf=textures.get('SRMF Baked')
    if srmf and 'file' in srmf:
        t=tex_node(n,srmf['file'],True)
        sep=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sep.inputs['Color'])
        scalar=inputs.get(path,{}).get('scalars',{})
        rough=n.new('ShaderNodeMath');rough.operation='MULTIPLY_ADD';rough.use_clamp=True
        rough.inputs[1].default_value=scalar.get('Roughness Global Multiply Post-Bake',1.)
        rough.inputs[2].default_value=scalar.get('Roughness Global Offset Post-Bake',0.)
        l.new(sep.outputs['Green'],rough.inputs[0]);l.new(rough.outputs[0],bs.inputs['Roughness'])
    normal = textures.get('Normal Baked')
    if normal and 'file' in normal:
        t = tex_node(n, normal['file'], True)
        separate = n.new('ShaderNodeSeparateColor')
        combine = n.new('ShaderNodeCombineColor')
        invert = n.new('ShaderNodeMath'); invert.operation='SUBTRACT'; invert.inputs[0].default_value=1
        l.new(t.outputs['Color'],separate.inputs['Color'])
        l.new(separate.outputs['Red'],combine.inputs['Red'])
        l.new(separate.outputs['Green'],invert.inputs[1])
        l.new(invert.outputs[0],combine.inputs['Green'])
        l.new(separate.outputs['Blue'],combine.inputs['Blue'])
        nm = n.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value=.65
        l.new(combine.outputs[0],nm.inputs['Color'])
        l.new(nm.outputs['Normal'],bs.inputs['Normal'])
    low = path.lower()
    if 'eye' in low:
        bs.inputs['Roughness'].default_value=.2
        bs.inputs['Subsurface Weight'].default_value=0
    if 'mi_eyel_baked' in low and not DRAFT:
        # Reproduce the separate native iris/sclera inputs in the Blender preview.
        # UE keeps its original eye material and refraction implementation.
        iris_data=textures.get('Iris Basecolor Baked')
        sclera_data=textures.get('Sclera Basecolor Baked')
        if iris_data and sclera_data and 'file' in iris_data and 'file' in sclera_data:
            uv_node=n.new('ShaderNodeTexCoord')
            delta=n.new('ShaderNodeVectorMath');delta.operation='SUBTRACT';delta.inputs[1].default_value=(.5,.5,0)
            l.new(uv_node.outputs['UV'],delta.inputs[0])
            length=n.new('ShaderNodeVectorMath');length.operation='LENGTH';l.new(delta.outputs[0],length.inputs[0])
            mask=n.new('ShaderNodeMapRange');mask.clamp=True
            mask.inputs['From Min'].default_value=.145;mask.inputs['From Max'].default_value=.155
            mask.inputs['To Min'].default_value=1.;mask.inputs['To Max'].default_value=0.
            l.new(length.outputs['Value'],mask.inputs['Value'])
            scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs['Scale'].default_value=.5/.15
            l.new(delta.outputs[0],scale.inputs[0])
            center=n.new('ShaderNodeVectorMath');center.operation='ADD';center.inputs[1].default_value=(.5,.5,0)
            l.new(scale.outputs[0],center.inputs[0])
            iris=tex_node(n,iris_data['file']);l.new(center.outputs[0],iris.inputs['Vector'])
            sclera=tex_node(n,sclera_data['file'])
            mix=n.new('ShaderNodeMixRGB');l.new(mask.outputs[0],mix.inputs[0])
            l.new(sclera.outputs['Color'],mix.inputs[1]);l.new(iris.outputs['Color'],mix.inputs[2])
            l.new(mix.outputs[0],bs.inputs['Base Color'])
            bs.inputs['Coat Weight'].default_value=.25
    if 'occlusion' in low or 'tear' in low:
        bs.inputs['Base Color'].default_value=(.10,.035,.025,1)
    if 'eyeshell' in low or 'lacrimal' in low or 'eyelashes' in low:
        # UE's specialized transparent eye-shell/groom shading is not a skin shader.
        transparent=n.new('ShaderNodeBsdfTransparent')
        l.new(transparent.outputs[0],output.inputs['Surface'])
    material_cache[path]=mat
    return mat

def make_mesh(name, data, positions):
    mesh=bpy.data.meshes.new(name)
    # Native UE centimetres -> metre-scale Blender scene; no topology changes.
    mesh.from_pydata([[v*.01 for v in p] for p in positions],[],data['triangles'])
    mesh.update()
    ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob)
    for m in data['materials']:
        mesh.materials.append(material(m['asset']))
    uv=mesh.uv_layers.new(name='UV0')
    for polygon, coords, mid in zip(mesh.polygons,data['triangle_uvs'],data['triangle_materials']):
        polygon.material_index=mid
        polygon.use_smooth=True
        for li, value in zip(polygon.loop_indices,coords):
            uv.data[li].uv=(value[0],1-value[1])
    # Native triangle winding is retained, with outward normals for the preview.
    ob['unreal_source']=data['source']
    return ob

original=make_mesh('Jason_Original',body,body['positions'])
derived=make_mesh(BLEND_NAME,body,tall_basis)
derived.shape_key_add(name='Basis')
key=derived.shape_key_add(name='Muscle_'+OUT.name.split('_')[0])
for vertex,p in zip(key.data,strong):
    vertex.co=[v*.01 for v in p]
key.value=1.0
derived['unreal_skeleton']=body['skeleton']
derived['preserved']='Native topology, UVs, weights, bone names/hierarchy and face. Original material assets reused in UE.'
derived['leg_height_increase_cm']=proportions.total_gain
for b in body['bones']:
    derived.vertex_groups.new(name=b['name'])
for vi, weights in enumerate(body['weights']):
    for index,weight in weights:
        derived.vertex_groups[index].add([vi],weight,'REPLACE')

arm=bpy.data.armatures.new('Jason_NativeSkeleton')
rig=bpy.data.objects.new('Jason_NativeSkeleton',arm);scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
edit={}
for b in body['bones']:
    eb=arm.edit_bones.new(b['name']);eb.head=Vector(proportions.point(b['position']))*.01
    children=[c for c in body['bones'] if c['parent']==b['index']]
    length=min([(Vector(proportions.point(c['position']))-Vector(proportions.point(b['position']))).length for c in children if (Vector(c['position'])-Vector(b['position'])).length>.2] or [1.])*.01
    eb.tail=eb.head+Vector(b['axes'][0])*max(.003,min(length,.35))
    eb.align_roll(Vector(b['axes'][2]));edit[b['index']]=eb
    if b['parent'] in edit:
        eb.parent=edit[b['parent']]
bpy.ops.object.mode_set(mode='OBJECT')
rig.hide_render=True;rig.show_in_front=True
rig.hide_set(True)
rig['native_bones_json']=json.dumps(body['bones'],separators=(',',':'))
rig['derived_bones_json']=json.dumps([dict(b,position=proportions.point(b['position'])) for b in body['bones']],separators=(',',':'))
rig['unreal_skeleton']=body['skeleton']
mod=derived.modifiers.new('NativeSkinWeights','ARMATURE');mod.object=rig

face_original=make_mesh('Jason_OriginalHead',head,head['positions'])
face_derived=bpy.data.objects.new('Jason_UnchangedHead',face_original.data);scene.collection.objects.link(face_derived)
face_derived.location.z=proportions.total_gain*.01
# The native head also includes the collar/shoulder border. Keep that border
# following the body in this editable preview; facial-only bones remain neutral.
body_names={b['name']:b['index'] for b in body['bones']}
head_map={}
for b in head['bones']:
    ancestor=b
    while ancestor['name'] not in body_names and ancestor['parent']>=0:
        ancestor=head['bones'][ancestor['parent']]
    head_map[b['index']]=body_names[ancestor['name']]
for b in body['bones']:face_derived.vertex_groups.new(name=b['name'])
for vi,weights in enumerate(head['weights']):
    mapped={}
    for index,weight in weights:mapped[head_map[index]]=mapped.get(head_map[index],0.)+weight
    for index,weight in mapped.items():face_derived.vertex_groups[index].add([vi],weight,'REPLACE')
head_mod=face_derived.modifiers.new('NativeHeadBorderBodyPose','ARMATURE');head_mod.object=rig
face_derived['preview_rig_note']='Native collar weights follow matching body bones; facial-only weights follow their body ancestor in this preview. UE head and facial skeleton remain unchanged.'
for ob in (original,face_original):ob.location.x=.68
for ob in (derived,face_derived,rig):ob.location.x=-.68

# A neutral studio setup, shared by both bodies at every camera angle.
floor_mat=bpy.data.materials.new('StudioFloor');floor_mat.diffuse_color=(.09,.105,.13,1);floor_mat.use_nodes=True
floor_mat.node_tree.nodes.clear()
floor_bs=floor_mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
floor_out=floor_mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
floor_mat.node_tree.links.new(floor_bs.outputs[0],floor_out.inputs['Surface'])
floor_bs.inputs['Base Color'].default_value=(.09,.105,.13,1)
floor_bs.inputs['Roughness'].default_value=.88
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.004))
floor=bpy.context.object;floor.name='PreviewFloor';floor.data.materials.append(floor_mat)

def area(name,point,power,size,color):
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size;light.color=color
    ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=point
    ob.rotation_euler=(Vector((0,0,1.))-ob.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-3,4,4),650,4,(1.,.9,.82))
area('Fill',(3,2,2.8),420,3,(.8,.88,1.))
area('Rim',(0,-3,3.5),800,3,(.88,.93,1.))
cam_data=bpy.data.cameras.new('ComparisonCamera');cam=bpy.data.objects.new('ComparisonCamera',cam_data);scene.collection.objects.link(cam)
scene.camera=cam;cam_data.type='ORTHO';cam_data.ortho_scale=3.0
cam.location=(0,6,1.0)
cam.rotation_euler=(Vector((0,0,.88))-cam.location).to_track_quat('-Z','Y').to_euler()
cam_data.ortho_scale=2.8
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'

def shot(name,angle,scale=2.8,target_z=.88):
    # Rotate both pairs in place so each uses exactly the same viewing angle.
    for ob in (original,face_original,derived,face_derived,rig):ob.rotation_euler.z=math.radians(angle)
    cam.location=(0,6,target_z+.12)
    cam.rotation_euler=(Vector((0,0,target_z))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam_data.ortho_scale=scale
    scene.render.filepath=str(PREVIEW/(name+'.png'))
    bpy.ops.render.render(write_still=True)

# This is an actual mesh preview; hair grooms remain native UE assets, not Blender curves.
scene['preview_note']='Geometry draft with native body UV and weights; shader placeholders only. Right body gains 4.5 cm through legs.' if DRAFT else 'Blender source geometry using exported native skin textures. UE hair grooms are not converted. Left original; right '+BLEND_NAME+'.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(BLEND_NAME+('_Geometry' if DRAFT else '')+'.blend')))
if DRAFT:
    print('JASON_STRONG_EDITABLE_GEOMETRY_SAVED',flush=True)
    sys.exit(0)
for name,angle in globals().get('variant_preview_shots',[('01_front',0),('02_three_quarter',-35),('03_back',180),('04_side',-90)]):
    shot(name,angle)
print('JASON_STRONG_BLENDER_SAVED',flush=True)
