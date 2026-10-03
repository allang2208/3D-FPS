"""Read the actual authored interfaces in the seated magazine coordinate frame.

This is input preparation for the requested repair, not a runtime acceptance test.
No render, animation edit or UE asset write is performed.
"""
import json
from pathlib import Path
import bpy
from mathutils import Matrix

O = Path(__file__).resolve().parent
S = O.parent
ACC = S / 'A762Meshy20260920/Accessories05'
bpy.ops.wm.open_mainfile(filepath=str(ACC / 'A762_AccessoryReady_Editable.blend'), use_scripts=False)
r = bpy.data.objects['SK_M4_Infima']
r.animation_data.action = bpy.data.actions['A_A762_idle']
r.animation_data.action_slot = r.animation_data.action.slots[0]
r.data.pose_position = 'POSE'
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
mag = r.pose.bones['WPN_SOCKET_Magazine'].matrix.copy()
root = r.pose.bones['WPN_root'].matrix.copy()
report = {'frame': 'seated WPN_SOCKET_Magazine local; metres', 'objects': {}}
report['root_to_mag'] = [list(row) for row in mag.inverted() @ root]
for ob in bpy.context.scene.objects:
    if ob.type != 'MESH' or not (ob.name.startswith('A762_R02_Magazine_') or ob.name in (
            'A762_Receiver', 'A762_R02_Receiver_MagwellCollar')):
        continue
    bone = 'WPN_SOCKET_Magazine' if ob.name.startswith('A762_R02_Magazine_') else 'WPN_root'
    xf = mag.inverted() @ r.pose.bones[bone].matrix @ r.data.bones[bone].matrix_local.inverted()
    pts = [xf @ v.co for v in ob.data.vertices]
    entry = {'bone': bone, 'vertices': len(pts), 'materials': [m.name for m in ob.data.materials],
             'min_mm': [round(min(p[i] for p in pts)*1000, 3) for i in range(3)],
             'max_mm': [round(max(p[i] for p in pts)*1000, 3) for i in range(3)]}
    if ob.name in ('A762_R02_Magazine_CompleteShell', 'A762_R02_Receiver_MagwellCollar'):
        entry['vertices_m'] = [list(p) for p in pts]
        entry['faces'] = [list(p.vertices) for p in ob.data.polygons]
    report['objects'][ob.name] = entry
(O / 'interface_inputs.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
for name, entry in report['objects'].items():
    if any(k in name for k in ('CompleteShell','Collar','FeedLip','Catch','Receiver')):
        print(name, {k:v for k,v in entry.items() if k not in ('vertices_m','faces')}, flush=True)
bpy.ops.wm.open_mainfile(filepath=str(S / 'A762DrumNeck20260925/SM_A762_drum.blend'), use_scripts=False)
for ob in bpy.context.scene.objects:
    if ob.type != 'MESH':
        continue
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    print('CURRENT_DRUM', ob.name, len(pts), [m.name for m in ob.data.materials],
          [round(min(p[i] for p in pts)*1000,3) for i in range(3)],
          [round(max(p[i] for p in pts)*1000,3) for i in range(3)], flush=True)
    import bmesh
    for cut in (.024, .030, .045):
        bm = bmesh.new(); bm.from_mesh(ob.data)
        bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                              plane_co=(0,0,cut), plane_no=(0,0,1), dist=1e-8,
                              clear_outer=True, clear_inner=False)
        todo = {e for e in bm.edges if e.is_boundary and all(abs(v.co.z-cut)<1e-6 for v in e.verts)}
        loops=[]
        while todo:
            first=todo.pop(); edges={first}; verts=set(first.verts); queue=list(first.verts)
            while queue:
                v=queue.pop()
                for e in v.link_edges:
                    if e in todo:
                        todo.remove(e); edges.add(e)
                        w=e.other_vert(v)
                        if w not in verts: verts.add(w); queue.append(w)
            loops.append({'verts':len(verts),'edges':len(edges),'bbox_mm':[
                [round(min(v.co[i] for v in verts)*1000,3) for i in range(3)],
                [round(max(v.co[i] for v in verts)*1000,3) for i in range(3)]]})
        print('CUT',cut,loops,flush=True);bm.free()
