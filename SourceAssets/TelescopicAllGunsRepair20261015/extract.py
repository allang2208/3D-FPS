import bpy,numpy as np,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];X=O/'Working';X.mkdir(exist_ok=True)
D=json.loads((P/'SourceAssets/TelescopicAllGunsAudit20261015/capture.json').read_text())
slots={'M4':[0,1,2],'AKM':[0,1,2],'QBZ191':[0,1,2],'HK416':[0,1,2],'A762':[1,2,3],'PKM':[1,2,3],'SVD':[0,1,2],'LMG201':[1,2,3],'Super90':[0,1,2]}
def data(ob):
 me=ob.data
 return {'positions':np.asarray([tuple(ob.matrix_world@v.co) for v in me.vertices]),'triangles':np.asarray([list(f.vertices) for f in me.polygons],dtype=np.int32),'mids':np.asarray([f.material_index for f in me.polygons],dtype=np.int32),'normals':np.asarray([tuple(n.vector) for n in me.corner_normals]).reshape(-1,3,3),'uv0':np.asarray([tuple(v.uv) for v in me.uv_layers[0].data]).reshape(-1,3,2)}
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/StockRefresh20260914/TacticalTelescopic/TacticalStock_Game_Body.blend'))
np.savez_compressed(X/'original.npz',**data(bpy.data.objects['TacticalStock_Game_Body']))
for key,body in slots.items():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(P/'SourceAssets/TelescopicStockSurface20261014/Inputs'/(key+'.fbx')))
 ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');d=data(ob);d['body_slots']=np.array(body);np.savez_compressed(X/(key+'.npz'),**d)
 print('BASELINE_EXTRACTED',key,len(d['triangles']),flush=True)
(O/'inputs.json').write_text(json.dumps({'assets':{k:D['assets'][k] for k in slots},'body_slots':slots,'accepted_m16_sha256':D['assets']['M16']['sha256'],'shared_normal_sha256':D['textures']['/Game/Weapons/TacticalTelescopicStock20260914/Textures/T_TacticalStock_Normal_Game.T_TacticalStock_Normal_Game']['sha256']},indent=2),encoding='utf-8')
