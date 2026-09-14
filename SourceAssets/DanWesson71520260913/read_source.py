"""Read pivots, source geometry and existing action contracts for authoring."""
import bpy, json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(next((O/'Original').rglob('DW_model715.FBX'))))
report={'objects':[],'actions':[a.name for a in bpy.data.actions]}
for ob in bpy.data.objects:
    row={'name':ob.name,'type':ob.type,'parent':ob.parent.name if ob.parent else None,'matrix':[list(v) for v in ob.matrix_world]}
    if ob.type=='MESH':
        pts=[ob.matrix_world@v.co for v in ob.data.vertices]
        row.update(vertices=len(pts),min=[min(v[k] for v in pts) for k in range(3)],max=[max(v[k] for v in pts) for k in range(3)],materials=[m.name for m in ob.data.materials])
    if ob.type=='ARMATURE':row['bones']=[{'name':b.name,'head':list(b.head_local),'tail':list(b.tail_local)} for b in ob.data.bones]
    if ob.name=='DW_MagazineAssembly':
        adjacency={v.index:set() for v in ob.data.vertices}
        for edge in ob.data.edges:
            a,b=edge.vertices;adjacency[a].add(b);adjacency[b].add(a)
        unseen=set(adjacency);row['islands']=[]
        while unseen:
            pending=[unseen.pop()];ids=[]
            while pending:
                v=pending.pop();ids.append(v)
                for n in adjacency[v]&unseen:unseen.remove(n);pending.append(n)
            pts=[ob.matrix_world@ob.data.vertices[i].co for i in ids]
            row['islands'].append({'ids':ids,'min':[min(v[k] for v in pts) for k in range(3)],'max':[max(v[k] for v in pts) for k in range(3)]})
    report['objects'].append(row)
(O/'source-geometry.json').write_text(json.dumps(report,indent=2))
try:
    bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M1911Contact20260913/M1911_Contact_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error) or 'SK_M1911_Manny' not in bpy.data.objects:
        raise
r=bpy.data.objects['SK_M1911_Manny']
ref={'actions':[(a.name,list(a.frame_range)) for a in bpy.data.actions if a.name.startswith('M1911_Contact')], 'root':[list(v) for v in r.data.bones['WPN_root'].matrix_local], 'parts':[]}
for ob in bpy.data.collections['M1911_LOW'].objects:
    pts=[r.data.bones['WPN_root'].matrix_local.inverted()@ob.matrix_world@v.co for v in ob.data.vertices]
    ref['parts'].append({'name':ob.name,'bone':ob.get('bone'),'min':[min(v[k] for v in pts) for k in range(3)],'max':[max(v[k] for v in pts) for k in range(3)]})
a=bpy.data.actions['M1911_Contact_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0)
ref['idle']={b.name:[list(v) for v in b.matrix] for b in r.pose.bones}
(O/'reference-poses.json').write_text(json.dumps(ref,indent=2))
print('REFERENCE_READY',flush=True)
