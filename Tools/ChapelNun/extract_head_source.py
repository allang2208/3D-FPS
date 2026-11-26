import bpy,json,numpy as np
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/ProductionR1';R.mkdir(exist_ok=True);(R/'Inputs').mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P/'SourceAssets/ChapelNun20261115/MeshyHeadR1/Source/NunHead_R1_glb.glb'))
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
me=ob.data;me.calc_loop_triangles()
p=np.array([v.co[:] for v in me.vertices])
out={'positions':p.tolist(),'triangles':[list(t.vertices) for t in me.loop_triangles],'uv':[[list(me.uv_layers.active.data[i].uv) for i in t.loops] for t in me.loop_triangles]}
(R/'Inputs/meshy_head.json').write_text(json.dumps(out,separators=(',',':')))
ref=json.loads((P/'SourceAssets/KaitlinPlayer20261023/NativeGeometry/SKM_MHC_Kaitlin_FaceMesh.json').read_text())
rp=np.array(ref['positions']);ids=sorted({i for t,m in zip(ref['triangles'],ref['triangle_materials']) if m==8 for i in t});skin=rp[ids]
print('MESHY_BOUNDS',p.min(0),p.max(0),'NATIVE_SKIN',skin.min(0),skin.max(0),flush=True)
for q in [.2,.35,.5,.6,.7,.8]:
 z=p[:,2].min()+np.ptp(p[:,2])*q;a=p[np.abs(p[:,2]-z)<.02]
 print('SLICE',q,a.min(0),a.max(0),flush=True)
for m in [2,3]:
 ids=sorted({i for t,mi in zip(ref['triangles'],ref['triangle_materials']) if mi==m for i in t})
 print('EYE',m,rp[ids].mean(0),rp[ids].min(0),rp[ids].max(0),flush=True)
