"""Split the already-authored potion props for drinking. No replacement modeling."""
import bpy, json
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).parent
(OUT / 'Export').mkdir(exist_ok=True)
manifest = {}
for family, height in [('hp_potion', .18), ('mp_potion', .185)]:
    source = ROOT / 'SourceAssets/Consumables5080_20260910' / (family + '_editable.blend')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    bottom, top = min(v.z for v in pts), max(v.z for v in pts)
    scale = height / (top - bottom)
    groups = {'shell': [], 'liquid': [], 'stopper': []}
    for o in objs:
        name = o.name.lower()
        # The authored silver stopper collar is capped geometry and belongs to
        # the removable stopper. Leaving it on the shell would seal the mouth.
        part = 'liquid' if 'liquid' in name else 'stopper' if 'stopper' in name else 'shell'
        matrix = Matrix.Scale(scale, 4) @ Matrix.Translation((0, 0, -bottom)) @ o.matrix_world
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
        o.data.transform(matrix)
        groups[part].append(o)
    for part, group in groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        for o in group: o.select_set(True)
        bpy.context.view_layer.objects.active = group[0]
        bpy.ops.object.join()
        o = bpy.context.object
        o.name = 'SM_' + family + '_' + part
        collision = None
        if part != 'liquid':
            # Explicit low-cost convex collision imports in a commandlet without
            # StaticMeshEditorSubsystem (which requires an interactive editor).
            corners = [Vector(c) for c in o.bound_box]
            low = Vector(tuple(min(c[i] for c in corners) for i in range(3)))
            high = Vector(tuple(max(c[i] for c in corners) for i in range(3)))
            bpy.ops.mesh.primitive_cube_add(size=1, location=(low+high)*.5)
            collision = bpy.context.object
            collision.name = 'UCX_' + o.name + '_00'
            collision.dimensions = high-low
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            collision.hide_render = True
            o.select_set(True)
        # All parts share the original bottle-bottom pivot and world dimensions.
        path = OUT / 'Export' / (o.name + '.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH'},
                                 add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE', axis_forward='-Y', axis_up='Z')
        manifest[o.name] = {'family': family, 'part': part, 'file': str(path),
                            'materials': [m.name for m in o.data.materials], 'height_cm': height * 100,
                            'source': str(source)}
        if collision: bpy.data.objects.remove(collision, do_unlink=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / (family + '_DrinkParts.blend')))
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('POTION_PARTS_EXPORTED', flush=True)
