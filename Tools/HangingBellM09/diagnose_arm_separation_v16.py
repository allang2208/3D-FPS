"""Inspect actual split topology, separate from skinning or combat timing."""
import bpy,json,sys
import numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'ArmContinuityV16/Records';OUT.mkdir(parents=True,exist_ok=True)
after='--after' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(ROOT/('ArmContinuityV16/Authoring/M09_ContinuousArms_V16.blend' if after else 'SkinDeathV13/Authoring/M09_Rigged_V13.blend')))
report={}
for name in ('M09_SmallArm_L','M09_SmallArm_R','M09_Body_RootBand'):
    ob=bpy.data.objects[name];me=ob.data
    p=np.empty((len(me.vertices),3));me.vertices.foreach_get('co',p.ravel());m=np.array(ob.matrix_world);p=p@m[:3,:3].T+m[:3,3]
    me.calc_loop_triangles();f=np.empty((len(me.loop_triangles),3),np.int32);me.loop_triangles.foreach_get('vertices',f.ravel())
    if 'source_triangle_id' in me.attributes:
        polygon_sid=np.empty(len(me.polygons),np.int32);me.attributes['source_triangle_id'].data.foreach_get('value',polygon_sid)
        indices=np.empty(len(me.loop_triangles),np.int32);me.loop_triangles.foreach_get('polygon_index',indices);sid=polygon_sid[indices]
    else:sid=np.full(len(f),-16,np.int32)
    unique,weld=np.unique(np.rint(p*1e6).astype(np.int64),axis=0,return_inverse=True)
    parent=np.arange(len(unique))
    def root(v):
        while parent[v]!=v:parent[v]=parent[parent[v]];v=parent[v]
        return v
    for tri in weld[f]:
        a=root(tri[0])
        for v in tri[1:]:parent[root(v)]=a
    roots=np.array([root(v) for v in weld]);counts=np.unique(roots,return_counts=True)
    comps=[]
    for key,count in sorted(zip(*counts),key=lambda a:-a[1])[:25]:
        select=roots==key;tri_mask=select[f].all(1);q=p[select]
        comps.append({'verts':int(count),'faces':int(tri_mask.sum()),'original_faces':int((tri_mask&(sid>=0)).sum()),
            'min':q.min(0).tolist(),'max':q.max(0).tolist(),'mean':q.mean(0).tolist()})
    edges=np.concatenate([weld[f[:,[0,1]]],weld[f[:,[1,2]]],weld[f[:,[2,0]]]])
    _,ec=np.unique(np.sort(edges,axis=1),axis=0,return_counts=True)
    report[name]={'components':len(counts[0]),'largest_components':comps,'boundary_edges':int((ec==1).sum()),'nonmanifold_edges':int((ec>2).sum()),'cap_faces':int((sid<0).sum())}
    # Actual source triangulation and attributes retained for local repair.
    if after:continue
    uv=np.empty((len(me.loops),2));me.uv_layers.active.data.foreach_get('uv',uv.ravel())
    groups=[g.name for g in ob.vertex_groups];weights=np.zeros((len(p),len(groups)))
    for v in me.vertices:
        for g in v.groups:weights[v.index,g.group]=g.weight
    np.savez_compressed(OUT/(name+'.npz'),positions=p,faces=f,uv=uv.reshape(-1,3,2),source_face=sid,groups=np.array(groups),weights=weights,components=roots)
(OUT/('topology_after.json' if after else 'topology.json')).write_text(json.dumps(report,indent=2),encoding='utf8')
print('ARM_TOPOLOGY_DIAG_SAVED',flush=True)
