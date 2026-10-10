"""Adapt evildeer's purple Elemental Alchemy book; keep its authored exterior UVs.

Produces editable Blender, static FBX, skinned FBX and seven animation clips.
No rendering or game execution. Units are centimetres throughout the export.
"""
import bpy
import bmesh
import json
import math
import shutil
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'Export'
TEX = OUT / 'Textures'
TEX.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'source-import.blend'))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01
scene.render.fps = 30

# The purple-and-gold cover is source object book2, also instanced as book11.
# Source +Y is the spine; source -X is the illustrated front cover.
source = bpy.data.objects['book2']
points = [source.matrix_world @ v.co for v in source.data.vertices]
spine_y = max(v.y for v in points)
center_x = (min(v.x for v in points) + max(v.x for v in points)) / 2
center_z = (min(v.z for v in points) + max(v.z for v in points)) / 2
transform = Matrix(((0, -100, 0, spine_y*100), (0, 0, 100, -center_z*100), (-100, 0, 0, center_x*100), (0, 0, 0, 1)))
closed_mesh = source.data.copy()
closed_mesh.transform(transform @ source.matrix_world)
closed_mesh.uv_layers.active.name='UVMap'
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
width = max(v.co.x for v in closed_mesh.vertices)
height = max(v.co.y for v in closed_mesh.vertices)-min(v.co.y for v in closed_mesh.vertices)
thickness = max(v.co.z for v in closed_mesh.vertices)-min(v.co.z for v in closed_mesh.vertices)

maps = {
    'BookCover': {
        'BaseColor': 'книги texturing_DefaultMaterial_BaseColor.jpeg',
        'Roughness': 'книги texturing_DefaultMaterial_Roughness.jpeg',
        'Metallic': 'книги texturing_DefaultMaterial_Metallic.jpeg',
        'Normal': 'книги texturing_DefaultMaterial_Normal.jpeg',
    },
    'BookPages': {
        'BaseColor': 'DefaultMaterial_Base_Color.png',
        'Roughness': 'DefaultMaterial_Roughness.png',
        'Metallic': 'DefaultMaterial_Metallic.png',
        'Normal': 'DefaultMaterial_Normal_DirectX.png',
    },
}
material_manifest = {}
materials = {}
for key, entries in maps.items():
    mat = bpy.data.materials.new('M_' + key)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    manifest_maps = {}
    for channel, filename in entries.items():
        source_path = ROOT / 'Original/textures' / filename
        target = TEX / ('T_' + key + '_' + channel + source_path.suffix)
        shutil.copy2(source_path, target)
        img = bpy.data.images.load(str(target), check_existing=False)
        if channel != 'BaseColor': img.colorspace_settings.name = 'Non-Color'
        node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = img
        if channel == 'Normal':
            normal = mat.node_tree.nodes.new('ShaderNodeNormalMap')
            color_output = node.outputs['Color']
            if key == 'BookPages':
                separate = mat.node_tree.nodes.new('ShaderNodeSeparateColor')
                combine = mat.node_tree.nodes.new('ShaderNodeCombineColor')
                invert = mat.node_tree.nodes.new('ShaderNodeMath'); invert.operation = 'SUBTRACT'; invert.inputs[0].default_value = 1
                mat.node_tree.links.new(color_output, separate.inputs['Color'])
                mat.node_tree.links.new(separate.outputs['Green'], invert.inputs[1])
                mat.node_tree.links.new(separate.outputs['Red'], combine.inputs['Red'])
                mat.node_tree.links.new(invert.outputs[0], combine.inputs['Green'])
                mat.node_tree.links.new(separate.outputs['Blue'], combine.inputs['Blue'])
                color_output = combine.outputs['Color']
            mat.node_tree.links.new(color_output, normal.inputs['Color'])
            mat.node_tree.links.new(normal.outputs['Normal'], shader.inputs['Normal'])
        else:
            mat.node_tree.links.new(node.outputs['Color'], shader.inputs['Base Color' if channel == 'BaseColor' else channel])
        img.pack()
        manifest_maps[channel] = str(target.relative_to(OUT)).replace('\\', '/')
    materials[key] = mat
    material_manifest[mat.name] = {'maps': manifest_maps, 'normal_convention': 'DirectX' if key == 'BookPages' else 'OpenGL'}

closed_mesh.materials.clear()
closed_mesh.materials.append(materials['BookCover'])
closed = bpy.data.objects.new('SM_Spellbook_Alchemy_Closed', closed_mesh)
bpy.context.collection.objects.link(closed)

def export_fbx(objects, name, animation=False):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.fbx(
        filepath=str(OUT / (name + '.fbx')), use_selection=True,
        object_types={'MESH', 'ARMATURE'}, axis_forward='-Y', axis_up='Z',
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
        mesh_smooth_type='FACE', use_tspace=False, add_leaf_bones=False,
        use_armature_deform_only=True, bake_anim=animation,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0, bake_anim_step=1,
        path_mode='STRIP', embed_textures=False)

export_fbx([closed], closed.name)

# All page illustrations come from the same licensed source set.
page_regions = [(.747, .690, .983, .985), (.012, .018, .214, .337), (.776, .018, .957, .293)]
page_x0, page_x1 = .65, width-.65
page_y0, page_y1 = -height/2+.70, height/2-.70

def page_uv(x, y, region, back=False, whole=False):
    u0,v0,u1,v1 = region
    u = x/width if whole else (x-page_x0)/(page_x1-page_x0)
    v = y/height+.5 if whole else (y-page_y0)/(page_y1-page_y0)
    if back: u = 1-u
    return u0+(u1-u0)*u, v0+(v1-v0)*v

def book_half(name, upper):
    mesh = closed_mesh.copy()
    mesh.materials.append(materials['BookPages'])
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces), dist=.00001,
        plane_co=(0,0,0), plane_no=(0,0,1), clear_inner=upper, clear_outer=not upper)
    rim = [edge for edge in bm.edges if edge.is_boundary and all(abs(v.co.z)<.0001 for v in edge.verts)]
    caps = bmesh.ops.holes_fill(bm, edges=rim, sides=0)['faces']
    uv = bm.loops.layers.uv.active
    for face in caps:
        face.material_index = 1
        face.smooth = False
        for loop in face.loops:
            loop[uv].uv = page_uv(loop.vert.co.x, loop.vert.co.y, page_regions[2 if upper else 1], back=upper, whole=True)
    # Cap boundaries contain collinear vertices from the author's triangles.
    # A centre fan avoids thin/zero-area ears when FBX triangulates the cap.
    bmesh.ops.poke(bm, faces=caps, offset=0, center_mode='MEAN_WEIGHTED')
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh); bm.free(); mesh.update()
    obj = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(obj)
    return obj

back = book_half('Book_BackHalf', False)
front = book_half('Book_FrontHalf', True)
arm_data = bpy.data.armatures.new('Spellbook_Alchemy_Skeleton')
arm = bpy.data.objects.new('SpellbookRig', arm_data)
bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
def make_bone(name, x, parent=None):
    b = arm_data.edit_bones.new(name); b.head=(x,0,0); b.tail=(x,1,0)
    if parent: b.parent=arm_data.edit_bones[parent]
    return b
make_bone('Book_Root', 0)
make_bone('Book_Back', 0, 'Book_Root')
make_bone('Cover_Front', 0, 'Book_Root')
SEGMENTS = 8
for page in range(3):
    for segment in range(SEGMENTS):
        make_bone(f'Page_{page+1}_{segment:02}', segment*page_x1/SEGMENTS,
                  'Book_Root' if segment==0 else f'Page_{page+1}_{segment-1:02}')
bpy.ops.object.mode_set(mode='OBJECT')

def attach(obj, rigid_bone=None):
    obj.parent = arm
    modifier = obj.modifiers.new('SpellbookDeform', 'ARMATURE'); modifier.object=arm
    if rigid_bone:
        obj.vertex_groups.new(name=rigid_bone).add(list(range(len(obj.data.vertices))),1,'REPLACE')
attach(back, 'Book_Back'); attach(front, 'Cover_Front')

pages=[]
NX, NY = 32, 8
for page in range(3):
    verts=[]; faces=[]; face_sides=[]
    for side in (1,-1):
        for ix in range(NX+1):
            for iy in range(NY+1):
                verts.append((page_x0+(page_x1-page_x0)*ix/NX, page_y0+(page_y1-page_y0)*iy/NY, side*.006))
    layer=(NX+1)*(NY+1)
    for side in range(2):
        for ix in range(NX):
            for iy in range(NY):
                a=side*layer+ix*(NY+1)+iy; q=(a,a+NY+1,a+NY+2,a+1)
                faces.append(q if side==0 else tuple(reversed(q))); face_sides.append(side)
    rim=[]
    rim += [ix*(NY+1) for ix in range(NX+1)]
    rim += [NX*(NY+1)+iy for iy in range(1,NY+1)]
    rim += [ix*(NY+1)+NY for ix in range(NX-1,-1,-1)]
    rim += [iy for iy in range(NY-1,0,-1)]
    for a,b in zip(rim, rim[1:]+rim[:1]):
        faces.append((a,a+layer,b+layer,b)); face_sides.append(2)
    mesh=bpy.data.meshes.new(f'PageLeaf_{page+1}')
    mesh.from_pydata(verts,[],faces); mesh.materials.append(materials['BookPages'])
    uv=mesh.uv_layers.new(name='UVMap')
    for face,side in zip(mesh.polygons,face_sides):
        face.use_smooth = side!=2
        for corner,li in enumerate(face.loop_indices):
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            if side==2:
                # A separate paper-colour patch gives the thin edge real UV area.
                uv.data[li].uv=((.56,.51),(.57,.51),(.57,.52),(.56,.52))[corner]
            else:
                uv.data[li].uv=page_uv(co.x,co.y,page_regions[(page+(side==1))%3],back=side==1)
    obj=bpy.data.objects.new(f'Book_Page_{page+1}',mesh); bpy.context.collection.objects.link(obj)
    groups=[obj.vertex_groups.new(name=f'Page_{page+1}_{i:02}') for i in range(SEGMENTS)]
    for vertex in mesh.vertices:
        t=max(0., min(SEGMENTS-1.,vertex.co.x/page_x1*SEGMENTS-.5))
        a=int(t); b=min(a+1,SEGMENTS-1); mix=t-a
        groups[a].add([vertex.index],1-mix,'REPLACE')
        if b!=a and mix>0: groups[b].add([vertex.index],mix,'REPLACE')
    attach(obj); pages.append(obj)

parts=[back,front]+pages
bpy.ops.object.select_all(action='DESELECT')
for obj in parts:obj.select_set(True)
bpy.context.view_layer.objects.active=back
bpy.ops.object.join()
skin=back; skin.name='SK_Spellbook_Alchemy'
arm.animation_data_create()
for bone in arm.pose.bones: bone.rotation_mode='XYZ'

def smooth(t):
    t=max(0.,min(1.,t)); return t*t*(3-2*t)

def pose(open_fraction=1., flips=(0.,0.,0.)):
    for bone in arm.pose.bones:
        bone.rotation_euler=(0,0,0); bone.location=(0,0,0); bone.scale=(1,1,1)
    arm.pose.bones['Cover_Front'].rotation_euler.y=math.radians(-165)*open_fraction
    for p,t in enumerate(flips):
        wave=math.sin(math.pi*t)
        root=arm.pose.bones[f'Page_{p+1}_00']
        root.rotation_euler.y=math.radians(-165)*t
        # World vertical clearance keeps the turned leaf above either page block.
        root.location.z=.05 + .021*((2-p)*(1-t)+p*t)
        for s in range(1,SEGMENTS):
            arm.pose.bones[f'Page_{p+1}_{s:02}'].rotation_euler.y=math.radians(7)*wave*math.sin(math.pi*s/SEGMENTS)

clips={}
specs=[('IdleClosed',30),('Open',36),('IdleOpen',30),('FlipPages',120),('IdleOpenTurned',30),('FlipBack',120),('Close',36)]
for clip, frames in specs:
    action=bpy.data.actions.new('A_Spellbook_'+clip); action.use_fake_user=True
    arm.animation_data.action=action
    scene.frame_start=1;scene.frame_end=frames+1
    for frame in range(1,frames+2):
        t=(frame-1)/frames
        if clip=='IdleClosed': opening,flips=0,(0,0,0)
        elif clip=='Open': opening,flips=smooth(t),(0,0,0)
        elif clip=='Close': opening,flips=1-smooth(t),(0,0,0)
        elif clip=='IdleOpenTurned': opening,flips=1,(1,1,1)
        elif clip=='FlipPages': opening,flips=1,tuple(smooth((t*120-p*30)/60) for p in range(3))
        elif clip=='FlipBack': opening,flips=1,tuple(1-smooth((t*120-(2-p)*30)/60) for p in range(3))
        else: opening,flips=1,(0,0,0)
        pose(opening,flips)
        for bone in arm.pose.bones:
            bone.keyframe_insert('rotation_euler',frame=frame,group=bone.name)
            bone.keyframe_insert('location',frame=frame,group=bone.name)
    scene.frame_set(1)
    export_fbx([arm,skin], action.name, animation=True)
    clips[clip]={'file':action.name+'.fbx','frames':frames+1,'seconds':frames/30}

arm.animation_data.action=None
pose(0,(0,0,0))
# Export a true rest pose; thin leaves overlap the mid-plane until animated.
for bone in arm.pose.bones: bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
export_fbx([arm,skin],skin.name)
pose(1,(0,0,0));bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get()
open_mesh=bpy.data.meshes.new_from_object(skin.evaluated_get(deps),depsgraph=deps)
opened=bpy.data.objects.new('SM_Spellbook_Alchemy_Open',open_mesh)
bpy.context.collection.objects.link(opened)
export_fbx([opened],opened.name)

# The author file opens on the skinned open book; originals remain in their own collection.
reference=bpy.data.collections.new('Static_Exports');scene.collection.children.link(reference)
for obj in (closed,opened):
    for collection in list(obj.users_collection):collection.objects.unlink(obj)
    reference.objects.link(obj)
reference.hide_viewport=True;reference.hide_render=True
arm.animation_data.action=bpy.data.actions['A_Spellbook_IdleOpen']
scene.frame_start=1;scene.frame_end=31;scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);skin.select_set(True)
bpy.context.view_layer.objects.active=arm
manifest={
    'source_uid':'ee1747b4d426446ba5f14bcf2aec8400','author':'evildeer','license':'CC BY 4.0',
    'selected_source_object':'book2','selected_cover':'Elemental Alchemy / blue-purple and gold',
    'closed_dimensions_cm':{'width':width,'height':height,'thickness':thickness},
    'coordinates':'centimetres; +X spine to fore-edge, +Y bottom to top, +Z front cover normal; root at spine/mid-plane',
    'static_meshes':[closed.name+'.fbx',opened.name+'.fbx'], 'skeletal_mesh':skin.name+'.fbx',
    'materials':material_manifest,'animations':clips,'page_leaf_count':3,'page_bones_per_leaf':SEGMENTS,
    'changes':['Original purple book exterior and UV retained', 'Book divided at middle page plane; illustrated inner page surfaces added', 'Three double-sided thin page leaves with eight-bone bending chains', 'Open, close and forward/backward page-turn clips authored'],
    'runtime_integration':False,'visual_or_game_testing_performed':False,
    'animation_contract':'Open -> IdleOpen -> FlipPages -> IdleOpenTurned -> FlipBack -> IdleOpen -> Close. Blend/interruption handled by the future weapon controller.'
}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Spellbook_Alchemy.blend'))
print('SPELLBOOK_AUTHOR_COMPLETE '+json.dumps({'selected':'book2 / Elemental Alchemy','clips':list(clips),'out':str(OUT)}))
