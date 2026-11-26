"""Background Blender source repair and export. Scene stays at source metres;
the level installer applies the single 1.25 scale to the environment.
Door assets are baked to final dimensions because the native door uses cm.
"""
import ast
import importlib
import json
import math
import os
import sys
from pathlib import Path
# The user's full rebuild supersedes the imported low-poly assembly. Preserve
# this familiar entry while routing it to the saved, current authoring source.
_current = Path(__file__).resolve().parents[3] / 'SourceAssets/CyberpunkApartmentRebuild20261022'
if (_current / 'installed.json').exists():
    import runpy
    runpy.run_path(str(_current / 'author.py'), run_name='__main__')
    raise SystemExit(0)
import bpy
import bmesh
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from playable_config import ROOT, SCALE
BUILD = ROOT / 'build'
OUT = ROOT / 'export'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='D:/CyberpunkApartment/CyberpunkApartment.blend')
sys.path.insert(0, str(BUILD))
import cy_lib as cy

# Restore physical UV tile sizes without changing the saved, tuned materials.
tree = ast.parse((BUILD / 's0_materials.py').read_text(encoding='utf-8-sig'))
tiles = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == 'TILES' for t in n.targets))
for m in bpy.data.materials:
    cy.reg(m.name, m, tiles.get(m.name, 2.0))

targets = {'S_plate', 'S_floors', 'S_walls', 'S_facade', 'S_glazing', 'S_doors', 'S_joinery', 'S_finish',
           'LIV_furniture', 'FOY_room', 'FOY_clutter', 'COR_clutter', 'DET_wall_greeble',
           'MST_room', 'MST_clutter', 'B2_room', 'B3_room', 'KIT_dining', 'BA1_room', 'BA1_clutter'}
original_build = cy.MB.build
original_reset = cy.reset_col
original_text = cy.text_mesh
rebuilt = []
def selected_build(self, *args, **kwargs):
    if self.name not in targets:
        return bpy.data.objects.get(self.name)
    if len(self._stack) != 1:
        raise RuntimeError(f'Unbalanced transform stack: {self.name} depth {len(self._stack)}')
    old = bpy.data.objects.get(self.name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    ob = original_build(self, *args, **kwargs)
    rebuilt.append(self.name)
    return ob
cy.MB.build = selected_build
cy.reset_col = lambda name: cy.col(name)
cy.text_mesh = lambda name, *a, **kw: bpy.data.objects.get(name)
for name in ('s1_arch', 's2_living', 's3_kitchen', 's4_bedrooms', 's5_bath_foyer', 's6_details', 's12_joinery', 's13_finish'):
    importlib.import_module(name)
cy.MB.build, cy.reset_col, cy.text_mesh = original_build, original_reset, original_text

# Door dimensions describe the final opening, not the old generic 120 x 240 frame.
# Mesh X=thickness, Y=width, Z=height (the native class splits Y into two leaves).
doors = [
    dict(name='Entry', x=992, y=-1082, yaw=90, width=96, height=212, material='metal_steel'),
    dict(name='Master', x=197, y=-532, yaw=90, width=82, height=202, material='wood_walnut'),
    dict(name='Bed2', x=1148, y=-455, yaw=0, width=82, height=202, material='wood_walnut'),
    dict(name='Bed3', x=1148, y=-803, yaw=0, width=82, height=202, material='wood_walnut'),
    dict(name='Bath1', x=370, y=-800, yaw=90, width=84, height=200, material='paint_charcoal'),
    dict(name='Bath2', x=162, y=-800, yaw=90, width=88, height=200, material='paint_charcoal'),
    dict(name='Balcony', x=755, y=-17, yaw=90, width=101, height=232, material='glass_window'),
]
for d in doors:
    w, h = d['width'] * SCALE / 100, d['height'] * SCALE / 100
    leaf = cy.MB('DoorAsset_' + d['name'] + '_Leaf', 'GAMEPLAY_DOORS', bevel=.0015, bevel_seg=1)
    leaf.box((.045, w, h), (0, 0, h/2), key=d['material'])
    # Narrow borders keep glass readable; all geometry remains within nominal bounds.
    for y in (-w/2+.012, w/2-.012, 0):
        leaf.box((.048, .024, h), (0, y, h/2), key='metal_dark')
    for z in (.025, h-.025):
        leaf.box((.048, w, .05), (0, 0, z), key='metal_dark')
    for y in (-w/4, w/4):
        for x in (-.028, .028):
            leaf.box((.012, .018, .30), (x, y, h*.48), key='metal_brushed')
    leaf.build()
    frame = cy.MB('DoorAsset_' + d['name'] + '_Frame', 'GAMEPLAY_DOORS', bevel=.002, bevel_seg=1)
    for y in (-w/2-.018, w/2+.018):
        for x in (-.06, .06):
            frame.box((.02, .036, h+.04), (x, y, (h+.04)/2), key='metal_dark')
    frame.box((.14, w+.072, .04), (0, 0, h+.02), key='metal_dark')
    frame.build()
    d.update(width_cm=w*100, height_cm=h*100, slide_cm=w*50+1)

# A real enclosed entry landing, with a floor, walls and ceiling: opening the
# apartment entrance must not immediately expose the 190-metre exterior void.
mb = cy.MB('S_entry_landing', 'GAMEPLAY_LANDING', bevel=.003, bevel_seg=1)
mb.box((3.0, 2.8, .24), (9.92, 12.30, -.12), key='concrete_floor')
mb.box((3.0, 2.8, .20), (9.92, 12.30, 2.85), key='concrete_ceiling')
for x in (8.42, 11.42):
    mb.box((.16, 2.8, 2.75), (x, 12.30, 1.375), key='concrete_wall')
mb.box((3.0, .16, 2.75), (9.92, 13.70, 1.375), key='concrete_wall')
mb.box((1.2, .04, .035), (9.92, 13.60, 2.40), key='neon_strip_cool')
mb.build()

# Repair only malformed faces/UVs; keep every valid authored UV and silhouette.
surface_repairs=[]
for ob in (o for o in bpy.data.objects if o.type=='MESH'):
    me=ob.data
    me.calc_loop_triangles()
    bad_faces=set()
    for tri in me.loop_triangles:
        a,b,c=(me.vertices[i].co for i in tri.vertices)
        if (b-a).cross(c-a).length<1e-12:bad_faces.add(tri.polygon_index)
    removed=0
    if bad_faces:
        bm=bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bmesh.ops.triangulate(bm,faces=[bm.faces[i] for i in bad_faces])
        bad=[f for f in bm.faces if f.calc_area()<1e-12]
        removed=len(bad)
        bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
        bm.to_mesh(me)
        bm.free()
        me.update()
    if not me.uv_layers:
        cy.uv_box_project(ob,[m.name for m in me.materials])
    me.calc_loop_triangles()
    uv=me.uv_layers.active.data
    repair_uv=set()
    for tri in me.loop_triangles:
        a,b,c=(uv[i].uv.copy() for i in tri.loops)
        if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1e-12:
            repair_uv.add(tri.polygon_index)
    for index in repair_uv:
        face=me.polygons[index]
        axis=max(range(3),key=lambda i:abs(face.normal[i]))
        axes=((1,2),(0,2),(0,1))[axis]
        material=me.materials[face.material_index]
        tile=tiles.get(material.name,2.0)
        for li in face.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co
            uv[li].uv=(p[axes[0]]/tile,p[axes[1]]/tile)
    # A non-planar quad can still contain a triangle edge-on to the average
    # face normal. Split only those exceptional faces and project per triangle.
    me.calc_loop_triangles()
    remaining=set()
    for tri in me.loop_triangles:
        a,b,c=(uv[i].uv.copy() for i in tri.loops)
        if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1e-12:
            remaining.add(tri.polygon_index)
    if remaining:
        bm=bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bmesh.ops.triangulate(bm,faces=[bm.faces[i] for i in remaining])
        uv_layer=bm.loops.layers.uv.active
        bm.normal_update()
        for face in bm.faces:
            if len(face.loops)!=3:continue
            a,b,c=(loop[uv_layer].uv.copy() for loop in face.loops)
            if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>=1e-12:continue
            axis=max(range(3),key=lambda i:abs(face.normal[i]))
            axes=((1,2),(0,2),(0,1))[axis]
            tile=tiles.get(me.materials[face.material_index].name,2.0)
            first=face.loops[0].vert.co
            offset=(math.floor(first[axes[0]]/tile),math.floor(first[axes[1]]/tile))
            for loop in face.loops:
                p=loop.vert.co
                loop[uv_layer].uv=(p[axes[0]]/tile-offset[0],p[axes[1]]/tile-offset[1])
        bm.to_mesh(me)
        bm.free()
        me.update()
    if removed or repair_uv:
        surface_repairs.append(dict(name=ob.name,degenerate_faces_removed=removed,uv_faces_reprojected=len(repair_uv)))

# Inventory all material/geometry payloads; preserve finite nondegenerate surfaces.
inventory = []
for ob in sorted((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o:o.name):
    mesh = ob.data
    mesh.calc_loop_triangles()
    v = np.array([ob.matrix_world @ x.co for x in mesh.vertices], dtype=float)
    if not len(v) or not np.isfinite(v).all():
        raise RuntimeError('Invalid geometry: ' + ob.name)
    slots = [m.name if m else None for m in mesh.materials]
    if not all(slots):
        raise RuntimeError('Missing material: ' + ob.name)
    if not mesh.uv_layers:
        cy.uv_box_project(ob, slots)
    inventory.append(dict(name=ob.name, vertices=len(v), triangles=len(mesh.loop_triangles),
                          bounds_m=[v.min(0).tolist(), v.max(0).tolist()], materials=slots,
                          uv_layers=[uv.name for uv in mesh.uv_layers]))

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'CyberpunkApartmentPlayable.blend'))
bpy.ops.object.select_all(action='DESELECT')
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for ob in meshes:
    ob.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.export_scene.gltf(filepath=str(OUT/'CyberpunkApartmentPlayable.gltf'),
    export_format='GLTF_SEPARATE', use_selection=True, export_apply=True,
    export_yup=True, export_materials='EXPORT', export_image_format='AUTO',
    export_texcoords=True, export_normals=True, export_tangents=False,
    export_cameras=False, export_lights=False, export_extras=True)
(ROOT / 'authoring.json').write_text(json.dumps(dict(rebuilt=rebuilt, doors=doors,surface_repairs=surface_repairs,
    meshes=inventory, scale=SCALE, original_blend_unchanged=True), indent=2), encoding='utf-8')
print('PLAYABLE_SOURCE_SAVED', len(inventory), flush=True)
