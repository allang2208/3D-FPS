import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;S=O.parent;O.mkdir(exist_ok=True)
report={}
for revision,filename,names in [('F37','FitFinish37/LMG201_FitFinish37_Editable.blend',['Receiver','TopCover_FitFinish37']),('S32','Surface32/LMG201_S32_Editable.blend',['Receiver','TopCover']),('R36','Repair36/LMG201_R36_Lid.blend',['TopCover'])]:
 bpy.ops.wm.open_mainfile(filepath=str(S/filename),use_scripts=False)
 rig=bpy.data.objects['SK_M4_Infima'];root=rig.data.bones['WPN_root'].matrix_local
 for name in names:
  ob=bpy.data.objects.get(name)
  if not ob:continue
  xf=root.inverted()@ob.matrix_world;v=np.array([(xf@q.co)[:] for q in ob.data.vertices]);me=ob.data;me.calc_loop_triangles();f=np.array([t.vertices[:] for t in me.loop_triangles]);mid=np.array([me.polygons[t.polygon_index].material_index for t in me.loop_triangles]);ed=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);length=np.linalg.norm(v[ed[:,0]]-v[ed[:,1]],axis=1);far=np.flatnonzero((np.abs(v[:,0])>.09)|(v[:,1]<-.28)|(v[:,1]>.03)|(v[:,2]>.16)|(v[:,2]<-.09))
  report[revision+'_'+name]={'bounds':[v.min(0).tolist(),v.max(0).tolist()],'far_vertices':[{'id':int(i),'p':v[i].tolist()} for i in far[:30]],'far_count':len(far),'max_edge':float(length.max()),'slots':[m.name for m in me.materials]}
  np.savez_compressed(O/(revision+'_'+name+'.npz'),v=v,f=f,mid=mid)
(O/'diagnosis.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
