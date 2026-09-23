"""Seat the carry-grip fasteners and make them follow the existing hinge."""
import bpy, json, sys
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent; R=O.parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(R/'Motion21/PKM_HingedOutlet_Editable.blend'),use_scripts=False)
rig=bpy.data.objects['PKM_Manny_Rig'];rig.data.pose_position='REST'
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
gun=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local@fit
wood=bpy.data.objects['PKM_Part_136']
points=[gun.inverted()@wood.matrix_world@v.co for v in wood.data.vertices]
wood_bvh=BVHTree.FromPolygons(points,[list(p.vertices) for p in wood.data.polygons])
source=json.loads((O/'handle_geometry.json').read_text())
report={'source':'Motion21/PKM_HingedOutlet_Editable.blend','parts':[],
        'hinge':'PKM_CarryHandle','animations_changed':False,'game_tested':False}
for name in ['PKM_Part_080','PKM_Part_081']:
    ob=bpy.data.objects[name];frame=gun.inverted()@ob.matrix_world
    pts=[frame@v.co for v in ob.data.vertices]
    islands=source[name]['islands']
    caps=[sum((pts[i] for i in c['indices']),Vector())/c['count'] for c in islands if c['count']==32]
    center=(caps[0]+caps[1])*.5
    axis=(caps[1]-caps[0]).normalized()
    old=[(p-center).dot(axis) for p in pts];a,b=min(old),max(old)
    origin=center-axis*.065;hits=[]
    for _ in range(24):
        hit,normal,index,distance=wood_bvh.ray_cast(origin,axis,.15)
        if hit is None:break
        hits.append((hit-center).dot(axis));origin=hit+axis*.000025
    if len(hits)<2:raise RuntimeError('Cannot seat fastener on wood: '+name)
    # Retain the original through-fastener, with a small head beyond either
    # wooden panel. Shaft, cap UVs and material identity remain intact.
    low,high=min(hits)-.00045,max(hits)+.00045
    inv=frame.inverted()
    for vertex,p,t in zip(ob.data.vertices,pts,old):
        radial=p-center-axis*t
        shifted=low+(t-a)/(b-a)*(high-low)
        vertex.co=inv@(center+axis*shifted+radial*.84)
    old_groups=[g.name for g in ob.vertex_groups]
    ob.vertex_groups.clear()
    ob.vertex_groups.new(name='PKM_CarryHandle').add(list(range(len(ob.data.vertices))),1.,'REPLACE')
    ob['mechanical_bone']='PKM_CarryHandle';ob['carry_handle_part']='seated_grip_fastener'
    ob['handle_revision']='HandleFinish27'
    ob.data.update()
    report['parts'].append({'name':name,'previous_groups':old_groups,'new_group':'PKM_CarryHandle',
        'shaft_length_before_mm':(b-a)*1000,'shaft_length_after_mm':(high-low)*1000,
        'cap_projection_mm':.45,'diameter_scale':.84,'wood_hits_mm':[v*1000 for v in hits]})
    print('PKM27_FASTENER',json.dumps(report['parts'][-1]),flush=True)
rig.data.pose_position='POSE';bpy.context.view_layer.update()
export=O/'Exports';export.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'Belt08'))
from mesh_export import export_mesh
export_mesh(rig,export/'SK_PKM_Manny_Modular.fbx')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_HandleFinish_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2))
print('PKM27_HANDLE_EXPORTED',flush=True)
