"""Remove only the four named protrusions, preserving the baked atlas and UVs."""
import bpy, bmesh, json, shutil
from pathlib import Path
from mathutils import Matrix

O = Path(__file__).resolve().parents[1]
R = O / 'Revisions/RemoveTowerRibs20260920'
R.mkdir(parents=True, exist_ok=True)
frames = json.loads((O/'Reference/author_frames.json').read_text())
bpy.context.preferences.filepaths.save_version = 0

def bounds(points):
    return tuple(min(p[i] for p in points) for i in range(3)) + tuple(max(p[i] for p in points) for i in range(3))

def remove_components(obj, targets):
    mesh = obj.data
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].append(b); adjacency[b].append(a)
    pending = set(range(len(mesh.vertices)))
    removed = set(); matches = []
    while pending:
        seed = pending.pop(); component = {seed}; stack = [seed]
        while stack:
            for other in adjacency[stack.pop()]:
                if other in pending:
                    pending.remove(other); component.add(other); stack.append(other)
        component_bounds = bounds([obj.matrix_world @ mesh.vertices[i].co for i in component])
        for index, target in enumerate(targets):
            if max(abs(a-b) for a,b in zip(component_bounds, target)) < 1e-6:
                removed.update(component); matches.append(index); break
    if sorted(matches) != [0,1,2,3]:
        raise RuntimeError('Could not uniquely select four rib components on ' + obj.name + ': ' + str(matches))
    # BMesh retains UVs and face materials. Carry exact corner normals through
    # deletion using an integer corner attribute, then restore them explicitly.
    normals = [tuple(n.vector) for n in mesh.corner_normals]
    tag = mesh.attributes.new('_rib_fix_original_corner', 'INT', 'CORNER')
    for i, item in enumerate(tag.data): item.value = i
    before = len(mesh.vertices)
    bm = bmesh.new(); bm.from_mesh(mesh); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in sorted(removed)], context='VERTS')
    bm.to_mesh(mesh); bm.free(); mesh.update()
    ids = [item.value for item in mesh.attributes['_rib_fix_original_corner'].data]
    mesh.normals_split_custom_set([normals[i] for i in ids])
    mesh.attributes.remove(mesh.attributes['_rib_fix_original_corner'])
    mesh.calc_loop_triangles()
    return {'removed_components': 4, 'removed_vertices': before-len(mesh.vertices), 'triangles': len(mesh.loop_triangles)}

report = {'operation':'remove four tower ribs only', 'game_tested':False, 'guns':{}}
for gun in ['M4','AKM','QBZ191']:
    folder = O/gun; backup = R/'Before'/gun; backup.mkdir(parents=True, exist_ok=True)
    for name in ['Drum_Construction.blend','Drum_Editable.blend','Drum_Integrated.blend','authoring_receipt.json']:
        if not (backup/name).exists(): shutil.copy2(folder/name, backup/name)
    export = O/'Export'/('SM_'+gun+'_LargeDrum_Upgrade.fbx')
    if not (backup/export.name).exists(): shutil.copy2(export, backup/export.name)
    # The untouched construction backup supplies exact component bounds on reruns.
    bpy.ops.wm.open_mainfile(filepath=str(backup/'Drum_Construction.blend'))
    ribs = sorted([o for o in bpy.context.scene.objects if o.name.startswith('Tower external longitudinal rib')], key=lambda o:o.name)
    if len(ribs) != 4: raise RuntimeError('Expected four named ribs for ' + gun)
    targets = [bounds([o.matrix_world @ v.co for v in o.data.vertices]) for o in ribs]
    for obj in ribs: bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Drum_Construction.blend'))
    bpy.ops.wm.open_mainfile(filepath=str(backup/'Drum_Editable.blend'))
    high = bpy.data.objects['Drum_SurfaceMaster']
    low = bpy.data.objects['SM_'+gun+'_LargeDrum_Upgrade']
    changes = {'high':remove_components(high, targets), 'low':remove_components(low, targets)}
    bpy.ops.object.select_all(action='DESELECT'); low.hide_set(False); low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Drum_Editable.blend'))
    low.data.transform(Matrix(frames[gun]['canonical_to_source']))
    bpy.ops.export_scene.fbx(filepath=str(export), use_selection=True, object_types={'MESH'}, axis_forward='-Y', axis_up='Z', bake_anim=False, mesh_smooth_type='FACE', use_tspace=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Drum_Integrated.blend'))
    receipt = json.loads((folder/'authoring_receipt.json').read_text())
    receipt.update({'source_triangles':changes['high']['triangles'], 'export_triangles':changes['low']['triangles'], 'revision':'RemoveTowerRibs20260920', 'revision_note':'Four tower ribs removed; remaining UVs, textures and corner normals retained'})
    (folder/'authoring_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    report['guns'][gun] = changes
    (R/'model_edit_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('TOWER_RIBS_REMOVED',gun,json.dumps(changes),flush=True)
print('TOWER_RIB_EDIT_COMPLETE',flush=True)
