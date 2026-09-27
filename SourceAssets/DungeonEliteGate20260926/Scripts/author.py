"""Resize the accepted corridor grille recipe into a four-track encounter gate.

Reuses its actual panel/box/rod/weld authoring functions and material identities.
No rendering, no edits to the original corridor gate or its materials.
Blender coordinates: X across opening, Y away from room, Z up, metres.
UE exports use X across opening, Y into room, Z up, centimetres.
"""
import ast
import json
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
CFG = json.loads((ROOT / 'Config/design.json').read_text())
SOURCE = ROOT.parent / CFG['source']
OUT = ROOT / 'Authored'
OUT.mkdir(parents=True, exist_ok=True)
(ROOT / 'Receipts').mkdir(exist_ok=True)
text = SOURCE.read_text(encoding='utf-8')
# Stop before the original whole gate/puddle assembly and all source saves.
scope = {'__file__': str(SOURCE), '__name__': 'accepted_grille_library'}
exec(compile(text.split("y=CFG['gate']['plane_y_m']", 1)[0], str(SOURCE), 'exec'), scope)
panel_node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == 'panel')
exec(compile(ast.Module(body=[panel_node], type_ignores=[]), str(SOURCE), 'exec'), scope)
scope['y'] = -.008  # panel(door=False) puts the grille on Y=0.
box, rod, bolt = scope['box'], scope['rod'], scope['bolt']
w = CFG['nominal_width_cm'] / 100
h = CFG['nominal_height_cm'] / 100
overlap = CFG['panel_overlap_cm'] / 100
side = CFG['side_overlap_cm'] / 100
pitch = h / CFG['panel_count']
panel_height = pitch + overlap
top = h + CFG['open_clearance_cm'] / 100 + panel_height
guide_height = top + CFG['hood_margin_cm'] / 100
tracks = [(CFG['first_track_cm'] + i * CFG['track_pitch_cm']) / 100 for i in range(CFG['panel_count'])]
objects = []

def begin():
    scope['parts'].clear()

def export(name, pivot=(0, 0, 0)):
    parts = list(scope['parts'])
    for obj in parts:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        mesh = obj.data
        uv = mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
        vc = mesh.color_attributes.new(name='Wear', type='BYTE_COLOR', domain='CORNER')
        low = [min(v.co[i] for v in mesh.vertices) for i in range(3)]
        high = [max(v.co[i] for v in mesh.vertices) for i in range(3)]
        for face in mesh.polygons:
            axes = sorted(range(3), key=lambda i: abs(face.normal[i]))[:2]
            for li in face.loop_indices:
                v = mesh.vertices[mesh.loops[li].vertex_index].co
                world = obj.matrix_world @ v
                uv.data[li].uv = (world[axes[0]] / .45, world[axes[1]] / .45)
                distances = sorted(min(abs(v[i] - low[i]), abs(high[i] - v[i])) for i in range(3))
                damp = max(0, 1 - world.z / .52)
                vc.data[li].color = (max(0, 1 - distances[1] / .009) * obj['wear'], damp * .4,
                                     min(1, obj['rust'] + damp * .48), 1)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    bpy.context.scene.cursor.location = pivot
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    obj.location = (0, 0, 0)
    tri = obj.modifiers.new('Export triangles', 'TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=tri.name)
    path = OUT / (name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH'},
                            axis_forward='-Y', axis_up='Z', bake_anim=False,
                            mesh_smooth_type='FACE', use_tspace=True, colors_type='LINEAR')
    material_map = {m.name: '/Game/Dungeons/AtmosphereV2/GateWater/Materials/M_DungeonGate_' +
                    m.name.removeprefix('GateWater_') for m in obj.data.materials}
    objects.append(dict(name=name, fbx=str(path), materials=material_map,
                        triangles=len(obj.data.polygons), collision='runtime_boxes'))
    # Leave an assembled, editable source scene; FBX coordinates stay component-local.
    obj.location = pivot
    return obj

begin()
# Use the source's intact welded panel, recut to the target dimensions. 0.3 m
# suppresses its hinged-door kickplate/lock-height stiffener; no hinges on a lift.
left, right = -w / 2 - side + .0225, w / 2 + side - .0225
bottom, upper = .3, .3 + panel_height - .044
scope['panel'](left, right, bottom, upper, False)
leaf = export('SM_EliteGrillePanel', (0, 0, bottom - .022))
leaf.location = (0, -tracks[0], -overlap / 2)
for i in range(1, CFG['panel_count']):
    copy = leaf.copy()
    bpy.context.collection.objects.link(copy)
    copy.location = (0, -tracks[i], -overlap / 2 + i * pitch)

for sign, label in ((-1, 'Left'), (1, 'Right')):
    begin()
    # Four real open C channels: their mouths face the grille; nothing narrows
    # the authored 300 cm opening. Rear anchor tabs meet the old 32 cm frame.
    for depth in tracks:
        box('Guide channel back', (sign * (w / 2 + .070), -depth, guide_height / 2),
            (.012, .072, guide_height), bevel=.001)
        for face in (-1, 1):
            box('Guide channel flange', (sign * (w / 2 + .038), -depth + face * .0345, guide_height / 2),
                (.076, .003, guide_height), 'Steel', .0007, .35, .15)
        box('Replaceable guide rubbing strip', (sign * (w / 2 + .059), -depth, guide_height / 2),
            (.006, .052, guide_height), 'Dark', .0005, .1, .08)
    for z in (.18, .90, 1.65, 2.48, 2.76):
        box('Standoff anchor', (sign * (w / 2 + .076), -.194, z), (.060, .068, .055),
            'Steel', .001, .35, .24)
        box('Anchor tab', (sign * (w / 2 + .061), -.156, z), (.122, .008, .084), wear=.5, rust=.3)
        bolt(sign * (w / 2 + .083), -.165, z)
    export('SM_EliteGrilleGuide' + label, (sign * w / 2, 0, 0))

begin()
hood_bottom = h + .005
hood_top = guide_height
hood_depth_min, hood_depth_max = tracks[0] - .05, tracks[-1] + .055
hood_center = (hood_depth_min + hood_depth_max) / 2
hood_width = w + .22
hood_height = hood_top - hood_bottom
for depth in (hood_depth_min, hood_depth_max):
    box('Folded storage fascia', (0, -depth, (hood_bottom + hood_top) / 2),
        (hood_width, .012, hood_height), wear=.44, rust=.16)
box('Storage top', (0, -hood_center, hood_top - .006),
    (hood_width, hood_depth_max - hood_depth_min, .012), wear=.3, rust=.13)
for sign in (-1, 1):
    box('Storage end cap', (sign * (hood_width / 2 - .006), -hood_center, (hood_bottom + hood_top) / 2),
        (.012, hood_depth_max - hood_depth_min, hood_height), wear=.42, rust=.19)
    # Bolted inspection cover in the source gate's finish and fastener language.
for x in (-w * .43, -w * .2, 0, w * .2, w * .43):
    for z in (hood_bottom + .055, hood_top - .055):
        bolt(x, -hood_depth_max - .007, z)
export('SM_EliteGrilleHead', (0, 0, h))

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'DungeonEliteGrille.blend'))
(OUT / 'manifest.json').write_text(json.dumps(dict(source=str(SOURCE), design=CFG, objects=objects,
    tests_run=False, rendered=False), indent=2), encoding='utf-8')
# Shared dimensions for the runtime consumer, generated from the same authoring inputs.
names = {'nominal_width_cm':'NominalWidth', 'nominal_height_cm':'NominalHeight',
         'panel_count':'PanelCount', 'panel_overlap_cm':'PanelOverlap', 'side_overlap_cm':'SideOverlap',
         'first_track_cm':'FirstTrack', 'track_pitch_cm':'TrackPitch', 'panel_thickness_cm':'PanelThickness',
         'open_clearance_cm':'OpenClearance', 'hood_margin_cm':'HoodMargin', 'travel_seconds':'TravelSeconds'}
lines = ['#pragma once', '// Generated by DungeonEliteGate20260926/Scripts/author.py; edit Config/design.json.',
         'namespace DungeonRoomGateDimensions', '{']
for key, symbol in names.items():
    lines.append(f'    inline constexpr {"int32" if key == "panel_count" else "double"} {symbol} = {CFG[key]};')
lines.append('}')
(PROJECT / 'Source/FPSGAME/Dungeons/DungeonRoomGateDimensions.h').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('ELITE_GRILLE_AUTHORED', len(objects), 'meshes; original corridor unchanged; no render')
