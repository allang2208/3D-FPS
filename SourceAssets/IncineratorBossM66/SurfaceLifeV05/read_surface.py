"""Read the existing skin/UV anatomy for the requested mouth repair and eye rig."""
import bpy,json
import numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/SurfaceLifeV05')
(ROOT/'Records').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'MeshyRigV01/Authoring/M66_back_completed_v01.blend'))
mesh=bpy.data.objects['M66_Body'];rig=bpy.data.objects['M66_Rig']
factor=json.loads((ROOT.parent/'MeshyRigV01/Records/rig_completion.json').read_text())['uniform_scale']
pos=np.array([v.co[:] for v in mesh.data.vertices])/factor
names=[g.name for g in mesh.vertex_groups]
weights=np.zeros((len(pos),len(names)),dtype=np.float32)
for v in mesh.data.vertices:
    for g in v.groups:weights[v.index,g.group]=g.weight
_,inverse=np.unique(np.rint(pos/1e-6).astype(np.int64),axis=0,return_inverse=True)
groups={}
for i,k in enumerate(inverse):groups.setdefault(int(k),[]).append(i)
seams=[]
for ids in groups.values():
    if len(ids)<2:continue
    diff=float(np.max(np.sum(np.abs(weights[ids]-weights[ids[0]]),axis=1)))
    if diff>.001:seams.append({'xyz':pos[ids[0]].tolist(),'vertices':ids,'weight_l1':diff})
seams.sort(key=lambda row:-row['weight_l1'])
jaw=(pos[:,0]>-.20)&(pos[:,0]<.12)&(pos[:,1]<-.12)&(pos[:,2]>.55)&(pos[:,2]<1.12)
summary=weights[jaw].sum(axis=0)
jaw_bones=sorted([(names[i],round(float(w),2)) for i,w in enumerate(summary) if w>1],key=lambda row:-row[1])
# Pixel centres measured from the existing BaseColor atlas, not a new texture.
eye_seeds=[(1229,1418,15),(1206,1451,17),(1237,1452,17),(1178,1499,21),
           (1234,1500,21),(1231,1548,21),(1236,1595,22)]
uv=np.array([l.uv[:] for l in mesh.data.uv_layers.active.data]);loop_vertices=np.array([l.vertex_index for l in mesh.data.loops])
pixels=np.column_stack((uv[:,0]*2048,(1-uv[:,1])*2048));eyes=[]
for number,(x,y,radius) in enumerate(eye_seeds):
    distance=np.linalg.norm((pixels-[x,y])/radius,axis=1)
    ids=np.unique(loop_vertices[distance<.85]);points=pos[ids]
    solution=np.linalg.lstsq(np.column_stack((2*points,np.ones(len(points)))),np.sum(points*points,axis=1),rcond=None)[0]
    centre=solution[:3];r=float(np.sqrt(max(0,solution[3]+centre@centre)))
    eyes.append({'index':number+1,'uv_pixel':[x,y,radius],'vertices':len(ids),'bounds':[points.min(axis=0).tolist(),points.max(axis=0).tolist()],
                 'sphere_center_source':centre.tolist(),'sphere_radius_source':r})
report={'seam_groups_with_different_weights':len(seams),'seam_vertices':sum(len(s['vertices']) for s in seams),
        'worst_seams':seams[:40],'front_mouth_vertices':int(jaw.sum()),'front_mouth_weight_totals':jaw_bones,'eyes':eyes}
(ROOT/'Records/source_surface.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_SURFACE_SOURCE '+json.dumps({k:report[k] for k in ('seam_groups_with_different_weights','seam_vertices','front_mouth_vertices','front_mouth_weight_totals','eyes')}))
