"""Replace only the low mortar skin; retain installed ceramics and support islands."""
import json
import math
import re
from pathlib import Path

import bpy
import bmesh

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT/'Config/surface.json').read_text())
INPUTS = json.loads((ROOT/'Sources/scene-inputs.json').read_text())
SOURCE = ROOT.parent/'DungeonAtmosphereV2_20260921/Authored/DungeonAtmosphereV2_Structure.blend'
OUT = ROOT/'Authored'
OUT.mkdir(parents=True, exist_ok=True)
SCALE = CFG['tile_size_cm']/100
SPANS = {
    'EntryEnd': [('y', 0, 4, 0, 1)],
    'Corridor_South': [('x', 0, 4.4, 0, 1), ('x', 9.6, 14.4, 0, 1), ('x', 16.2, 26, 0, 1)],
    'Corridor_North': [('x', 0, 8.3, 4, -1), ('x', 12.7, 15, 4, -1), ('x', 21.5, 22, 4, -1)],
    'Workshop': [('x', 4, 10, -4.2, 1), ('y', -4.2, 0, 4, 1), ('y', -4.2, 0, 10, -1)],
    'MachineBay': [('x', 8, 13, 8, -1), ('y', 4, 8, 8, 1), ('y', 4, 8, 13, -1)],
    'ServiceRecess': [('x', 14, 16.6, -2.2, 1), ('y', -2.2, 0, 14, 1), ('y', -2.2, 0, 16.6, -1)],
    'Dogleg': [('y', 0, 10, 26, -1), ('y', 4, 14, 22, 1)],
    'EndLanding': [('x', 22, 29, 14, -1), ('y', 10, 14, 29, -1), ('x', 26, 29, 10, 1)],
}
bpy.ops.wm.read_factory_settings(use_empty=True)
source_names = ['SM_V2_'+a['label'].removeprefix('DGN_AV2_') for a in INPUTS['actors']]
with bpy.data.libraries.load(str(SOURCE), link=False) as (available, dest):
    missing = set(source_names)-set(available.objects)
    if missing:
        raise RuntimeError('Required source wall absent: '+str(missing))
    dest.objects = source_names
for obj in dest.objects:
    bpy.context.scene.collection.objects.link(obj)


def material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    manifest = json.loads((OUT/'material-manifest.json').read_text())
    for channel in ('BaseColor', 'Normal', 'Surface'):
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(manifest['channels'][channel], check_existing=True)
        tex.image.colorspace_settings.name = 'sRGB' if channel == 'BaseColor' else 'Non-Color'
        if channel == 'BaseColor':
            links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        elif channel == 'Normal':
            n = nodes.new('ShaderNodeNormalMap')
            n.inputs['Strength'].default_value = 1 if name.endswith('Bed') else .16
            links.new(tex.outputs['Color'], n.inputs['Color'])
            links.new(n.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            split = nodes.new('ShaderNodeSeparateColor')
            links.new(tex.outputs['Color'], split.inputs[0])
            links.new(split.outputs['Red'], bsdf.inputs['Roughness'])
    return mat


bedmat = material('V2_WallReliefBed')
finishmat = material('V2_WallReliefFinish')


def coordinates(co, span):
    axis, a, b, fixed, inside = span
    return (co.x, (co.y-fixed)*inside, co.z) if axis == 'x' else (co.y, (co.x-fixed)*inside, co.z)


def bed_height(t, z, phase):
    # Smooth low-frequency undulation only. Millimetre pores and scrape channels
    # are carried by the separate height map, avoiding double displacement.
    value = (.46*math.sin(t*9.1+z*6.7+phase) + .27*math.sin(t*16.3-z*11.2+phase*.7)
             + .17*math.sin(t*26.4+z*23.1-phase) + .10*math.sin(t*40.2-z*31.7))
    return CFG['bed_center_m']+CFG['bed_amplitude_m']*value


manifest = dict(source=str(SOURCE), objects=[], config=CFG, tests_run=False)
for entry in INPUTS['actors']:
    key = entry['label'].removeprefix('DGN_AV2_').removesuffix('_Tiles')
    obj = bpy.data.objects['SM_V2_'+key+'_Tiles']
    slots = list(obj.data.materials)
    mortar_ids = {i for i, mat in enumerate(slots) if mat and 'Mortar' in mat.name}
    finish_id = len(slots)
    obj.data.materials.append(finishmat)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.active
    removed = []
    for face in bm.faces:
        if face.material_index not in mortar_ids:
            continue
        center = face.calc_center_median()
        span = min(SPANS[key], key=lambda s: abs(coordinates(center, s)[1]-.125) +
                   max(s[1]-coordinates(center, s)[0], 0) + max(coordinates(center, s)[0]-s[2], 0))
        points = [coordinates(v.co, span) for v in face.verts]
        # Removes the old low bed, isolated hard comb strips and flat low skim;
        # grout at 13.8/13.9 cm and retained-ceramic support at 13.5/13.6 cm stay.
        if all(.100 < d < .131 and .14 < z < 1.61 for t, d, z in points):
            removed.append(face)
        else:
            face.material_index = finish_id
            for loop in face.loops:
                t, d, z = coordinates(loop.vert.co, span)
                loop[uv_layer].uv = (t/SCALE, z/SCALE)
    bmesh.ops.delete(bm, geom=removed, context='FACES')
    bm.to_mesh(obj.data)
    bm.free()
    vertices, faces, coords = [], [], []
    for index, span in enumerate(SPANS[key]):
        axis, a, b, fixed, inside = span
        nx = math.ceil((b-a)/(CFG['bed_grid_cm']/100))
        nz = math.ceil(1.435/(CFG['bed_grid_cm']/100))
        start = len(vertices)
        phase = fixed*.43 + index*.61
        for i in range(nx+1):
            t = a+(b-a)*i/nx
            for j in range(nz+1):
                z = .155+1.435*j/nz
                d = bed_height(t, z, phase)
                vertices.append((t, fixed+inside*d, z) if axis == 'x' else (fixed+inside*d, t, z))
                coords.append((t/SCALE, z/SCALE))
        for i in range(nx):
            for j in range(nz):
                p = start+i*(nz+1)+j
                ids = [p, p+nz+1, p+nz+2, p+1]
                if (axis == 'x' and inside == 1) or (axis == 'y' and inside == -1):
                    ids.reverse()
                faces.append(ids)
    mesh = bpy.data.meshes.new(key+'_ContinuousBed')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(bedmat)
    uv = mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            uv.data[li].uv = coords[mesh.loops[li].vertex_index]
    bed = bpy.data.objects.new(key+'_ContinuousBed', mesh)
    bpy.context.scene.collection.objects.link(bed)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bed.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
    mod = obj.modifiers.new('Relief export triangulation', 'TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.name = 'SM_WallRelief_'+key
    file = OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file), use_selection=True, object_types={'MESH'}, axis_forward='-Y',
                            axis_up='Z', bake_anim=False, mesh_smooth_type='FACE', use_tspace=True, add_leaf_bones=False)
    old_materials = {re.sub(r'\.\d{3}$', '', slot['name']): slot['material'] for slot in entry['slots']}
    manifest['objects'].append(dict(name=obj.name, actor=entry['label'], previous_mesh=entry['mesh'],
                                    fbx=str(file), materials=old_materials,
                                    old_low_mortar_faces_removed=len(removed), bed_quads=len(faces)))
    print('AUTHORED_WALL', key, 'removed low mortar faces', len(removed), 'continuous bed quads', len(faces), flush=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonWallRelief_Source.blend'))
(OUT/'geometry-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
