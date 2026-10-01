"""Read current V7/M4 bind frame and editable animation sources for HK416 authoring."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
file=P/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/M4_BareArmsV7.blend'
bpy.ops.wm.open_mainfile(filepath=str(file))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');root=rig.data.bones['WPN_root'].matrix_local;inv=root.inverted()
out={'source':str(file),'rig':rig.name,'root_matrix':[list(r) for r in root],'bones':{},'meshes':[],'actions':[]}
for b in rig.data.bones:
    if b.name.startswith('WPN_') or b.name in ('hand_r','hand_l','index_03_r','thumb_03_r'):
        out['bones'][b.name]={'parent':b.parent.name if b.parent else None,'head_root':list(inv@b.head_local),'tail_root':list(inv@b.tail_local),'matrix':[list(r) for r in b.matrix_local]}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    points=[inv@ob.matrix_world@v.co for v in ob.data.vertices];ob.data.calc_loop_triangles()
    out['meshes'].append({'name':ob.name,'vertices':len(points),'triangles':len(ob.data.loop_triangles),'materials':[m.name if m else None for m in ob.data.materials],
        'bounds_root':{'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)]}})
for a in bpy.data.actions:out['actions'].append({'name':a.name,'frames':list(a.frame_range)})
(O/'donor.json').write_text(json.dumps(out,indent=2))
print('DONOR',json.dumps({k:v for k,v in out.items() if k not in ('bones','root_matrix')}),flush=True)
print('BONES',json.dumps({k:v['head_root'] for k,v in out['bones'].items()}),flush=True)
