"""Read the accepted magazine's authoring geometry in the weapon root frame."""
import bpy, json
from pathlib import Path
import numpy as np
O = Path(__file__).parent
source = O.parent / 'M1911RearRain20260913/M1911_RearFinish_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig = bpy.data.objects['SK_M1911_Manny']
rig.data.pose_position = 'REST'
bpy.context.view_layer.update()
root = rig.matrix_world @ rig.data.bones['WPN_root'].matrix_local
record = {'source':str(source), 'objects':{}, 'bones':{}}
for name in ['M1911_MagazineShell','M1911_MagazineFloorplate','M1911_MagazineFollower']:
    ob = bpy.data.objects[name]
    xf = root.inverted() @ ob.matrix_world
    v = np.array([xf @ p.co for p in ob.data.vertices])
    record['objects'][name] = {'bounds':[v.min(axis=0).tolist(),v.max(axis=0).tolist()],
        'bone':ob.get('bone'), 'groups':[g.name for g in ob.vertex_groups],
        'materials':[m.name for m in ob.data.materials],
        'uv_layers':[x.name for x in ob.data.uv_layers],
        'matrix':[list(r) for r in ob.matrix_world],
        'vertices':len(v), 'faces':len(ob.data.polygons),
        'z_slices':[{'z':float(h),'bounds':[v[(v[:,2]>=h)&(v[:,2]<h+.008)].min(axis=0).tolist(),v[(v[:,2]>=h)&(v[:,2]<h+.008)].max(axis=0).tolist()]} for h in np.arange(v[:,2].min(),v[:,2].max(),.008) if len(v[(v[:,2]>=h)&(v[:,2]<h+.008)])]}
    np.savez_compressed(O/(name+'.npz'), vertices=v,
        faces=np.array([list(p.vertices) for p in ob.data.polygons]),
        uvs=np.array([list(p.uv) for p in ob.data.uv_layers.active.data]))
for n in ['WPN_root','WPN_SOCKET_Magazine','WPN_Follower']:
    b=rig.data.bones[n]
    record['bones'][n]={'parent':b.parent.name if b.parent else None,'matrix':[list(r) for r in b.matrix_local]}
(O/'source_geometry.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('M1911_MAG_SOURCE '+json.dumps(record),flush=True)
