import bpy,bmesh,json
from pathlib import Path
import numpy as np
O=Path(__file__).parent;SRC=O.parent.parent/'SVCHSketchfab20261017'
bpy.ops.wm.open_mainfile(filepath=str(SRC/'Authoring/SVCH_Viewmodel.blend'))
hold=json.loads((SRC/'Authoring/hold_frame.json').read_text());HR=np.array(hold['R']);HT=np.array(hold['t_cm'])
islands=json.loads((SRC/'audit/measurements.json').read_text())['scene_inventory']['islands']
def native(v):
    g=(np.array((v.co.x*100,-v.co.y*100,v.co.z*100))-HT)@HR
    return np.array((g[0]+18.7444,g[2],g[1]+1.5268))
report={}
for ob in bpy.data.objects:
    if ob.type!='MESH' or not ob.name.startswith('SM_SVCH_'):continue
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    remain=set(bm.verts)
    while remain:
        seed=remain.pop();group={seed};stack=[seed]
        while stack:
            for edge in stack.pop().link_edges:
                for v in edge.verts:
                    if v in remain:remain.remove(v);group.add(v);stack.append(v)
        vv=list(group);points=np.array([native(v) for v in vv]);lo,hi=points.min(0),points.max(0)
        item=min(islands,key=lambda d:np.linalg.norm(lo-d['bbox_native_units']['min'])+np.linalg.norm(hi-d['bbox_native_units']['max']))
        error=np.linalg.norm(lo-item['bbox_native_units']['min'])+np.linalg.norm(hi-item['bbox_native_units']['max'])
        if item['id'] in (5,6,7,8,9,10,11,12,13,14,21,23,38,39,43,40,134,135,136):
            ids={v:i for i,v in enumerate(vv)}
            report[str(item['id'])]={'name':item['part'],'object':ob.name,'match_error_cm':float(error),
                'vertices':points.tolist(),'faces':[[ids[v] for v in f.verts] for f in {f for v in vv for f in v.link_faces}]}
    bm.free()
(O/'mechanism_geometry.json').write_text(json.dumps(report,indent=1))
print('SVCH_MECHANISMS',json.dumps({k:{'name':v['name'],'vertices':len(v['vertices']),'match_error':v['match_error_cm']} for k,v in report.items()}))
