"""User-requested staff-only closure, UV, grip and exported FBX checks."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Staff_SolidCrystal_V19.blend'))
entries=json.loads((ROOT/'Export/meshes.json').read_text())
report={'source':{},'fbx':{},'grip_max_surface_delta_cm':{}}
def inspect(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    # Do not weld independently closed contact surfaces / intersecting rune pieces.
    # FBX imports here retain the original indexed topology.
    result={'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
        'degenerate_faces':sum(f.calc_area()<1e-8 for f in bm.faces),'signed_volume_cm3':bm.calc_volume(signed=True)}
    bm.free()
    obj.data.calc_loop_triangles();uv=obj.data.uv_layers.active;bad=0
    for tri in obj.data.loop_triangles:
        a,b,c=[uv.data[i].uv for i in tri.loops];ab=b-a;ac=c-a
        if abs(ab.x*ac.y-ab.y*ac.x)<1e-11:bad+=1
    result['degenerate_uv_triangles']=bad
    return result
for entry in entries:report['source'][entry['name']]=inspect(bpy.data.objects[entry['name']])
names=['SM_Staff_grip_lining_'+s for s in ('false','alloy_grip','pine_grip','sandalwood_grip')]
new={name:bpy.data.objects[name] for name in names}
with bpy.data.libraries.load(str(ROOT.parent/'apprentice_staff_modular.blend'),link=False) as (src,dst):dst.objects=list(names)
for name,old in zip(names,dst.objects):
    tree=KDTree(len(old.data.vertices))
    for i,v in enumerate(old.data.vertices):tree.insert(v.co,i)
    tree.balance()
    report['grip_max_surface_delta_cm'][name]=max(tree.find(v.co)[2] for v in new[name].data.vertices if 22.001<v.co.z<41.999)
# Import the actual exports into an empty scene, not just authoring objects.
bpy.ops.wm.read_factory_settings(use_empty=True)
for entry in entries:
    bpy.ops.import_scene.fbx(filepath=entry['fbx'])
    objects=[o for o in bpy.context.selected_objects if o.type=='MESH']
    if len(objects)!=1:raise RuntimeError('Expected one exported part '+entry['name'])
    report['fbx'][entry['name']]=inspect(objects[0])
    for obj in objects:bpy.data.objects.remove(obj,do_unlink=True)
report['failures']=[stage+':'+name for stage in ('source','fbx') for name,row in report[stage].items()
    if row['boundary_edges'] or row['nonmanifold_edges'] or row['degenerate_faces'] or row['signed_volume_cm3']<=0 or row['degenerate_uv_triangles']]
report['passed']=not report['failures'] and max(report['grip_max_surface_delta_cm'].values())<.001
(ROOT/'geometry_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['passed'],'failures':report['failures'],'grip_delta_cm':report['grip_max_surface_delta_cm']}))
