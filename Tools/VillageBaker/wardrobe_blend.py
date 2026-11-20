"""Assemble the new patterns on the original strong male armature and save the editable body."""
import pickle
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/VillageBaker/WardrobeR1'
R4 = ROOT / 'SourceAssets/JasonStrong20261117/R4_PoseRefined/Jason_StrongTall_R4.blend'


def material(slot):
    base = bpy.data.materials.new('M_Baker_' + slot)
    base.use_nodes = True
    nodes, links = base.node_tree.nodes, base.node_tree.links
    shader = nodes.get('Principled BSDF')
    for i, suffix in enumerate(('BC', 'N', 'ORM')):
        tex = nodes.new('ShaderNodeTexImage')
        tex.location = (-760, 270 - 275 * i)
        tex.image = bpy.data.images.load(str(OUT / 'Textures' / f'T_Baker_{slot}_{suffix}.png'), check_existing=True)
        tex.label = {'BC': 'Albedo', 'N': 'Tangent normal · OpenGL', 'ORM': 'AO / roughness / metallic'}[suffix]
        if suffix == 'BC':
            links.new(tex.outputs['Color'], shader.inputs['Base Color'])
        elif suffix == 'N':
            tex.image.colorspace_settings.name = 'Non-Color'
            normal = nodes.new('ShaderNodeNormalMap')
            normal.location = (-390, -40)
            normal.inputs['Strength'].default_value = .67 if slot in ('Skin', 'NativeNeck') else .82
            links.new(tex.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], shader.inputs['Normal'])
        else:
            tex.image.colorspace_settings.name = 'Non-Color'
            split = nodes.new('ShaderNodeSeparateColor')
            split.location = (-400, -290)
            links.new(tex.outputs['Color'], split.inputs['Color'])
            links.new(split.outputs['Green'], shader.inputs['Roughness'])
            links.new(split.outputs['Blue'], shader.inputs['Metallic'])
    if slot in ('Skin', 'NativeNeck'):
        shader.inputs['Subsurface Weight'].default_value = .055
        shader.inputs['Subsurface Radius'].default_value = (1., .4, .21)
        shader.inputs['Subsurface Scale'].default_value = .012
    elif slot in ('Shirt', 'Apron', 'Towel', 'Sash', 'Cuff', 'Pants'):
        shader.inputs['Sheen Weight'].default_value = .19
        shader.inputs['Sheen Roughness'].default_value = .78
    swatches = {'Shirt': (.075, .072, .09), 'Apron': (.36, .235, .15), 'Cuff': (.14, .13, .14),
                'Sash': (.38, .26, .17), 'Towel': (.58, .46, .34), 'Pants': (.078, .052, .035),
                'Boot': (.07, .043, .03), 'Sole': (.032, .023, .017), 'Thread': (.20, .15, .12),
                'Button': (.17, .09, .043), 'Skin': (.48, .28, .19), 'NativeNeck': (.48, .28, .19)}
    base.diffuse_color = (*swatches[slot], 1)
    return base


def make_object(name, cuts, rig, bone_names, library, keep_patterns):
    positions, faces, coords, indices = [], [], [], []
    normal_slices = []
    material_names = []
    v_start = f_start = 0
    for piece in cuts:
        p, f = piece['positions'], piece['faces']
        positions.append(p * .01)
        faces.append(f + v_start)
        tex = piece['uv'].copy()
        tex[:, :, 1] = 1 - tex[:, :, 1]
        coords.append(tex)
        for label in piece['materials']:
            if label not in material_names:
                material_names.append(label)
        palette = [material_names.index(label) for label in piece['materials']]
        face_ids = piece['indices']
        indices.append(np.full(len(f), palette[0], dtype=np.int32) if face_ids is None else np.asarray(palette)[face_ids])
        if piece['normals'] is not None:
            normal_slices.append((f_start * 3, (f_start + len(f)) * 3, piece['normals'].reshape(-1, 3)))
        v_start += len(p)
        f_start += len(f)
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.concatenate(positions).tolist(), [], np.concatenate(faces).tolist())
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for slot in material_names:
        me.materials.append(library[slot])
    uv_layer = me.uv_layers.new(name='UVMap')
    uv_layer.data.foreach_set('uv', np.concatenate(coords).ravel())
    me.polygons.foreach_set('material_index', np.concatenate(indices).astype('i'))
    me.polygons.foreach_set('use_smooth', np.ones(len(me.polygons), dtype=bool))
    me.update()
    if normal_slices:
        normal = np.empty(3 * len(me.loops), dtype='f')
        me.corner_normals.foreach_get('vector', normal)
        normal = normal.reshape(-1, 3)
        for lo, hi, supplied in normal_slices:
            normal[lo:hi] = supplied
        me.normals_split_custom_set(normal.tolist())
    groups = {}
    v_start = 0
    for piece in cuts:
        for v, row in enumerate(piece['weights'], v_start):
            for index, amount in row:
                if index not in groups:
                    groups[index] = ob.vertex_groups.new(name=bone_names[index])
                if amount > 0.:
                    groups[index].add([v], amount, 'REPLACE')
        if keep_patterns:
            sel = ob.vertex_groups.new(name='Cut | ' + piece['name'])
            sel.add(list(range(v_start, v_start + len(piece['positions']))), 1., 'REPLACE')
        if 'upper_ring' in piece:
            ring = ob.vertex_groups.new(name='Join | native neck at 154.50 cm')
            ring.add(np.unique(piece['upper_ring']).tolist(), 1., 'REPLACE')
        v_start += len(piece['positions'])
    ob.parent = rig
    modifier = ob.modifiers.new('Jason native skin weights', 'ARMATURE')
    modifier.object = rig
    return ob


def main():
    with Path(sys.argv[-1]).open('rb') as package:
        pieces, bone_names = pickle.load(package)
    bpy.ops.wm.open_mainfile(filepath=str(R4))
    bpy.context.preferences.filepaths.save_version = 0
    body = bpy.data.objects['Jason_StrongTall_R4']
    rig = bpy.data.objects['Jason_NativeSkeleton']
    calc = bpy.data.objects['R4 joint angle components']
    for ob in list(bpy.context.scene.objects):
        if ob not in (body, rig, calc):
            bpy.data.objects.remove(ob, do_unlink=True)
    body.location.x = rig.location.x = 0
    body.name = 'SK_Baker_Body'
    body.parent = rig
    body['source_variant'] = 'Jason StrongTall R4'
    body['source_asset'] = str(R4)
    body['UE_asset'] = body.get('unreal_source', 'Jason StrongTall R4 body')
    rig.hide_set(False)
    rig.show_in_front = False
    rig.hide_render = False
    library = {s: material(s) for s in sorted({s for p in pieces for s in p['materials']} | {'Skin'})}
    for i in range(len(body.data.materials)):
        body.data.materials[i] = library['NativeNeck' if i == 5 else 'Skin']
    # Leave the original mesh and all R4 shape keys intact. Only the visible
    # workwear view masks the split lower skin panels underneath the trousers.
    keep = {index for polygon in body.data.polygons if polygon.material_index in (0, 1, 2, 3, 5)
            for index in polygon.vertices}
    group = body.vertex_groups.new(name='Baker | visible under workwear')
    group.add(sorted(keep), 1., 'REPLACE')
    covered = body.modifiers.new('Workwear | conceal covered lower skin', 'MASK')
    covered.vertex_group = group.name
    outfit = make_object('SK_Baker_Workwear', [p for p in pieces if p['name'] != 'Baker_Neck_Base'],
                         rig, bone_names, library, keep_patterns=True)
    neck = make_object('Baker_Neck_Base', [p for p in pieces if p['name'] == 'Baker_Neck_Base'],
                       rig, bone_names, library, keep_patterns=False)
    neck['upper_ring_world_metres'] = 1.545
    neck['assembly'] = 'Native collar below 154.50 cm. Replace this separate object when fitting a head with its own native lower collar.'
    scene = bpy.context.scene
    scene['preview_note'] = 'Village baker R1 | body and workwear on Jason StrongTall R4, front +Y, anatomical left +X, units metres.'
    scene['upper_neck_cut_metres'] = 1.545
    scene['body_source'] = str(R4)
    bpy.ops.object.select_all(action='DESELECT')
    outfit.select_set(True)
    bpy.context.view_layer.objects.active = outfit
    for win in bpy.data.screens:
        for area in win.areas:
            if area.type == 'VIEW_3D':
                view = area.spaces.active
                view.region_3d.view_perspective = 'ORTHO'
                view.region_3d.view_rotation = Vector((0, -1, -.035)).to_track_quat('-Z', 'Y')
                view.region_3d.view_distance = 2.95
                view.region_3d.view_location = (0., 0., .84)
                view.shading.color_type = 'MATERIAL'
    bpy.data.orphans_purge(do_recursive=True)
    for im in bpy.data.images:
        if im.source == 'FILE' and im.users and not im.packed_file:
            im.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Baker_Body.blend'), compress=True, relative_remap=True)
    print('Baker R4 body and workwear saved:', OUT / 'Baker_Body.blend', flush=True)


if __name__ == '__main__':
    main()
