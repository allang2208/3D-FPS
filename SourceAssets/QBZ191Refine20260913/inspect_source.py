import bpy,json,zipfile,io
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent
out={}
with zipfile.ZipFile('D:/FPS3D/qbz-191-free (1).zip') as z:
 out['archive']=[{'name':i.filename,'bytes':i.file_size} for i in z.infolist()]
for name in ['QBZ19120260912/QBZ191_Editable.blend','QBZ19120260912/SurfacePolish/QBZ191_SurfacePolish.blend']:
 bpy.ops.wm.open_mainfile(filepath=str(S/name));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 info={'meshes':{},'images':{},'actions':{}}
 for ob in s.objects:
  if ob.type=='MESH':
   ob.data.calc_loop_triangles();info['meshes'][ob.name]={'vertices':len(ob.data.vertices),'triangles':len(ob.data.loop_triangles),'custom_normals':ob.data.has_custom_normals,'materials':[m.name for m in ob.data.materials]}
 for im in bpy.data.images:
  info['images'][im.name]={'size':list(im.size),'filepath':im.filepath}
 for kind,frames in {'idle':[0],'reload':[0,29,43,76,95,110,125,126],'reload_empty':[125,126,126.5,127,130,142,151,163,164],'equip_charge':[0,8,16,25,38]}.items():
  a=bpy.data.actions['QBZ191_'+kind];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];rows={}
  for f in frames:
   s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix
   rows[str(f)]={n:[list(row) for row in (root.inverted()@r.pose.bones[n].matrix)] for n in ['WPN_SOCKET_Magazine','WPN_ChargingHandle','hand_l','hand_r']}
   rows[str(f)]['root']=[list(row) for row in root]
  info['actions'][kind]=rows
 out[name]=info
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ19120260912/SourceInspect.blend'));ob=bpy.data.objects['QBZ'];out['source_components']=[]
comps=json.loads((S/'QBZ19120260912/components.json').read_text())[0]['components']
for i,c in enumerate(comps):out['source_components'].append({'id':i,'vertices':c['vertices'],'min':[round(v,6) for v in c['min']],'max':[round(v,6) for v in c['max']]})
(O/'source_diagnosis.json').write_text(json.dumps(out,indent=2));print('QBZ_SOURCE_DIAGNOSIS_READY',flush=True)
