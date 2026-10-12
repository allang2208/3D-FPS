"""Sixteen illustrated page faces; retain the accepted exterior and V27 opening.

Seven real double-sided leaves plus the two fixed inner surfaces. No render.
"""
import bpy
import bmesh
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'Export'
OUT.mkdir(exist_ok=True)
LEAVES, SEGMENTS, NX, NY = 7, 8, 32, 8
GROUPS = ('Herbal', 'Alchemy', 'Celestial', 'Arcane')
data = json.loads((ROOT / 'Focus/PalmUpOpeningV24/candidate.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Spellbook_Alchemy.blend'))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01
scene.render.fps = 60
arm = bpy.data.objects['SpellbookRig']
skin = bpy.data.objects['SK_Spellbook_Alchemy']
arm.animation_data_clear()
arm.matrix_world = Matrix.Identity(4)
for bone in arm.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)

# Keep the original halves, cover UVs, and fixed inner surfaces. Remove only the
# old three leaf meshes from this new in-memory copy, never the accepted source.
page_groups = {g.index for g in skin.vertex_groups if g.name.startswith('Page_')}
front_group = skin.vertex_groups['Cover_Front'].index
bm = bmesh.new()
bm.from_mesh(skin.data)
weights = bm.verts.layers.deform.verify()
bmesh.ops.delete(bm, geom=[v for v in bm.verts if any(g in page_groups for g in v[weights].keys())], context='VERTS')
bm.to_mesh(skin.data)
bm.free()
width = max(v.co.x for v in skin.data.vertices)
height = max(v.co.y for v in skin.data.vertices)-min(v.co.y for v in skin.data.vertices)
x0, x1, y0, y1 = .65, width-.65, -height/2+.70, height/2-.70
old_paper = bpy.data.materials['M_BookPages']
edge_slot = next(i for i, m in enumerate(skin.data.materials) if m == old_paper)
illustrations = []
for group in GROUPS:
    mat = bpy.data.materials.new('M_SpellbookPages_' + group)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = .88
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(HERE / 'Textures' / ('T_SpellbookPages_' + group + '.png')))
    tex.image.colorspace_settings.name = 'sRGB'
    mat.node_tree.links.new(tex.outputs['Color'], shader.inputs['Base Color'])
    illustrations.append(mat)
    skin.data.materials.append(mat)
atlas_slots = [next(i for i, m in enumerate(skin.data.materials) if m == target) for target in illustrations]

def page_uv(x, y, page, back=False, whole=False):
    u = x/width if whole else (x-x0)/(x1-x0)
    v = y/height+.5 if whole else (y-y0)/(y1-y0)
    u, v = max(0., min(1., u)), max(0., min(1., v))
    if back:
        u = 1-u
    # OrientationV2: rotate only the printed face, within its own atlas cell.
    u, v = 1-u, 1-v
    tile = page % 4
    col, row = tile % 2, tile // 2
    pu, pv = 3./1024, 3./1536
    return col*.5+pu+(.5-2*pu)*u, 1-(row+1)*.5+pv+(.5-2*pv)*v

# First left page and final right page bookend the fourteen moving faces.
uv = skin.data.uv_layers.active.data
for face in skin.data.polygons:
    if face.material_index != edge_slot:
        continue
    front = any(g.group == front_group and g.weight > .5 for g in skin.data.vertices[face.vertices[0]].groups)
    page = 0 if front else 15
    face.material_index = atlas_slots[page//4]
    for li in face.loop_indices:
        co = skin.data.vertices[skin.data.loops[li].vertex_index].co
        uv[li].uv = page_uv(co.x, co.y, page, back=front, whole=True)

bpy.ops.object.select_all(action='DESELECT')
arm.hide_set(False)
skin.hide_set(False)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for bone in list(arm.data.edit_bones):
    if bone.name.startswith('Page_'):
        arm.data.edit_bones.remove(bone)
for page in range(LEAVES):
    for segment in range(SEGMENTS):
        bone = arm.data.edit_bones.new(f'Page_{page+1}_{segment:02}')
        bone.head = (segment*x1/SEGMENTS, 0, 0)
        bone.tail = (segment*x1/SEGMENTS, 1, 0)
        bone.parent = arm.data.edit_bones['Book_Root' if segment == 0 else f'Page_{page+1}_{segment-1:02}']
bpy.ops.object.mode_set(mode='OBJECT')

leaves = []
for page in range(LEAVES):
    verts, faces, sides = [], [], []
    for sign in (1, -1):
        for ix in range(NX+1):
            for iy in range(NY+1):
                verts.append((x0+(x1-x0)*ix/NX, y0+(y1-y0)*iy/NY, sign*.006))
    layer = (NX+1)*(NY+1)
    for side in range(2):
        for ix in range(NX):
            for iy in range(NY):
                a = side*layer+ix*(NY+1)+iy
                q = (a, a+NY+1, a+NY+2, a+1)
                faces.append(q if side == 0 else tuple(reversed(q)))
                sides.append(side)
    rim = [ix*(NY+1) for ix in range(NX+1)]
    rim += [NX*(NY+1)+iy for iy in range(1, NY+1)]
    rim += [ix*(NY+1)+NY for ix in range(NX-1, -1, -1)]
    rim += [iy for iy in range(NY-1, 0, -1)]
    for a, b in zip(rim, rim[1:]+rim[:1]):
        faces.append((a, a+layer, b+layer, b))
        sides.append(2)
    mesh = bpy.data.meshes.new(f'IllustratedLeaf_{page+1}')
    mesh.from_pydata(verts, [], faces)
    for mat in [old_paper]+illustrations:
        mesh.materials.append(mat)
    uv = mesh.uv_layers.new(name='UVMap').data
    for face, side in zip(mesh.polygons, sides):
        face.use_smooth = side != 2
        printed_page = 1+page*2+side
        face.material_index = 0 if side == 2 else 1+printed_page//4
        for corner, li in enumerate(face.loop_indices):
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            uv[li].uv = ((.56,.51),(.57,.51),(.57,.52),(.56,.52))[corner] if side == 2 else page_uv(co.x, co.y, printed_page, back=side == 1)
    obj = bpy.data.objects.new(f'Book_Page_{page+1}', mesh)
    bpy.context.collection.objects.link(obj)
    groups = [obj.vertex_groups.new(name=f'Page_{page+1}_{i:02}') for i in range(SEGMENTS)]
    for vertex in mesh.vertices:
        t = max(0., min(SEGMENTS-1., vertex.co.x/x1*SEGMENTS-.5))
        a, b = int(t), min(int(t)+1, SEGMENTS-1)
        mix = t-a
        groups[a].add([vertex.index], 1-mix, 'REPLACE')
        if a != b and mix > 0:
            groups[b].add([vertex.index], mix, 'REPLACE')
    obj.parent = arm
    obj.modifiers.new('SpellbookDeform', 'ARMATURE').object = arm
    leaves.append(obj)
bpy.ops.object.select_all(action='DESELECT')
for obj in [skin]+leaves:
    obj.select_set(True)
bpy.context.view_layer.objects.active = skin
bpy.ops.object.join()
skin.name = 'SK_Spellbook_Alchemy_16Pages'

S = Matrix.Diagonal((1,-1,1))
C = Matrix.Diagonal((1,-1,-1))
def pose(opening, alignment, progress=None):
    for bone in arm.pose.bones:
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = (0,0,0)
        bone.location = (0,0,0)
        bone.scale = (1,1,1)
    root = arm.pose.bones['Book_Root']
    root.rotation_mode = 'QUATERNION'
    root.rotation_quaternion = (S@C@Matrix(alignment).to_3x3()@C@S).to_quaternion()
    back = math.radians(90)*opening
    arm.pose.bones['Book_Back'].rotation_euler.y = back
    arm.pose.bones['Cover_Front'].rotation_euler.y = math.radians(-75)*opening
    for p in range(LEAVES):
        t = 0. if progress is None else max(0., min(1., (progress*(30*(LEAVES-1)+60)-p*30)/60))
        flip = t*t*(3-2*t)
        leaf = arm.pose.bones[f'Page_{p+1}_00']
        leaf.rotation_euler.y = back-math.radians(165)*flip-math.radians(6*p/(LEAVES-1))*math.sin(math.pi*opening)
        leaf.location = Matrix.Rotation(back,3,'Y')@Vector((0,0,.05+.021*((LEAVES-1-p)*(1-flip)+p*flip)))
        for segment in range(1,SEGMENTS):
            arm.pose.bones[f'Page_{p+1}_{segment:02}'].rotation_euler.y = (math.radians(3)*math.sin(math.pi*opening)+math.radians(7)*math.sin(math.pi*flip))*math.sin(math.pi*segment/SEGMENTS)

def export_fbx(name, animation):
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    skin.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')), use_selection=True, object_types={'MESH','ARMATURE'},
        axis_forward='-Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
        mesh_smooth_type='FACE', use_tspace=False, add_leaf_bones=False, use_armature_deform_only=True,
        bake_anim=animation, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0, bake_anim_step=1, path_mode='STRIP', embed_textures=False)

for bone in arm.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
export_fbx(skin.name, False)
arm.animation_data_create()
clips = []
for name, count, reading in [('A_Spellbook_16Pages_Open', math.ceil(data['events']['open_end']*60)+1, False), ('A_Spellbook_16Pages_Flip', 481, True)]:
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    arm.animation_data.action = action
    scene.frame_start, scene.frame_end = 0, count-1
    for f in range(count):
        scene.frame_set(f)
        if reading:
            pose(1., data['book_root_alignment'][-1], f/(count-1))
        else:
            pose(data['opening_alpha'][f], data['book_root_alignment'][f])
        for bone in arm.pose.bones:
            bone.keyframe_insert('rotation_quaternion' if bone.rotation_mode == 'QUATERNION' else 'rotation_euler', frame=f)
            bone.keyframe_insert('location', frame=f)
    if len(action.slots):
        arm.animation_data.action_slot = action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
    scene.frame_set(0)
    export_fbx(name, True)
    clips.append(dict(name=name, frames=count, seconds=(count-1)/60))
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'Spellbook_16Pages.blend'))
manifest = dict(mesh=skin.name, leaves=LEAVES, illustrated_faces=16, bones=len(arm.data.bones),
    material_slots=[m.name for m in skin.data.materials], animations=clips, rendered=False,
    paper_groups=list(GROUPS), runtime_page_cycle_seconds=16*LEAVES/3)
(HERE/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('SPELLBOOK_16PAGES_AUTHORED '+json.dumps(manifest))
