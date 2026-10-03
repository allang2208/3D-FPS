"""Scoped topology investigation requested for the meteor pommel; no render."""
import bpy, bmesh, json, sys
from pathlib import Path
from collections import Counter

P = Path(__file__).parent
SOURCE = P.parent
rows = []

def geometry(obj, label):
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(deps)
    me = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(obj.matrix_world)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    bm.normal_update()
    boundaries = [e for e in bm.edges if e.is_boundary]
    bins = Counter(round(v.co.z * 100, 3) for e in boundaries for v in e.verts)
    caps = [f for f in bm.faces if abs(f.normal.z) > .99]
    body_sides = [f for f in bm.faces if -.080 < f.calc_center_median().z < -.060
                  and f.calc_center_median().xy.length > .035]
    row = {
        'label': label, 'object': obj.name,
        'vertices_welded': len(bm.verts), 'faces': len(bm.faces),
        'boundary_edges': len(boundaries),
        'boundary_z_cm': dict(bins),
        'nonmanifold_edges': sum(not e.is_manifold for e in bm.edges),
        'signed_volume_cm3': bm.calc_volume(signed=True) * 1000000,
        'body_sides_outward': sum(f.normal.xy.dot(f.calc_center_median().xy) > 0 for f in body_sides),
        'body_sides_inward': sum(f.normal.xy.dot(f.calc_center_median().xy) < 0 for f in body_sides),
        'bounds_local_cm': [[min(v.co[i] for v in bm.verts) * 100 for i in range(3)],
                            [max(v.co[i] for v in bm.verts) * 100 for i in range(3)]],
        'horizontal_faces': [{'z_cm': round(f.calc_center_median().z * 100, 5),
                              'normal_z': round(f.normal.z, 5), 'vertices': len(f.verts),
                              'area_cm2': f.calc_area() * 10000,
                              'material': obj.material_slots[f.material_index].name if f.material_index < len(obj.material_slots) else str(f.material_index)} for f in caps],
    }
    rows.append(row)
    print('METEOR_TOPOLOGY', label, obj.name, 'BOUNDARY', len(boundaries), 'NONMANIFOLD', row['nonmanifold_edges'], flush=True)
    bm.free()
    evaluated.to_mesh_clear()

def fbx(path, label):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            geometry(obj, label)

after = '--after' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'RuneSword_Pommels_Editable.blend'))
for name in (['MeteorBody'] if after else ['MeteorBody', 'Octagonal impact rim', 'Meteor eight point inset', 'Small blue meteor eye', 'Original mounting neck']):
    obj = bpy.data.objects.get(name)
    if obj:
        obj.hide_set(False)
        geometry(obj, 'editable_source')
if after:
    fbx(P/'SavedUE_Meteor_LODs.fbx', 'saved_repaired_ue_lods')
else:
    fbx(SOURCE/'Interface/MeteorBody.fbx', 'interface_base')
    fbx(SOURCE/'Export/SM_RunePommel_Meteor.fbx', 'delivery_fbx')
    if (P/'CurrentUE_Meteor.fbx').exists():
        fbx(P/'CurrentUE_Meteor.fbx', 'current_ue_asset')
output = P/('geometry_after.json' if after else 'geometry_findings.json')
output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
print('METEOR_INSPECTION_SAVED', output, flush=True)
