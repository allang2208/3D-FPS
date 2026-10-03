"""Extract current authoring poses and real charging-handle geometry."""
import bpy,json,ast
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sample'],type_ignores=[]),'<sample>','exec'))
live=json.loads((O/'runtime_inputs.json').read_text())['clips']
out={}
for gun,blend in [('AKM',Path(live['AKM/reference']['source']).with_suffix('.blend')),('SVD',S/'SVDThumbUp20260923/SVD_base_Editable.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(blend));r=bpy.data.objects['SK_M4_Infima']
 a=r.animation_data.action if gun=='AKM' else bpy.data.actions['A_SVD_reload_empty']
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
 poses=[]
 for f in range(516):poses.append(sample(r,a,f))
 frames=[0,240,248,256,264,268,280,290,300,310,320,330,340,344,350,360,380,400,432,515]
 row={'blend':str(blend),'action':a.name,'fps':bpy.context.scene.render.fps,'rest':{n:[list(x) for x in m] for n,m in rest.items()},'parents':parents,
      'poses':[{n:[list(x) for x in m] for n,m in p.items()} for p in poses], 'objects':[o.name for o in bpy.context.scene.objects if o.type=='MESH']}
 sample(r,a,0);pts=[]
 if gun=='AKM':
  ob=bpy.data.objects['AKM_Soviet_Native'];ids={g.index for g in ob.vertex_groups if g.name=='WPN_bolt'}
  vi=[v.index for v in ob.data.vertices if any(g.group in ids and g.weight>.9 for g in v.groups)]
 else:
  ob=bpy.data.objects['SM_SVD_ChargingHandle'];vi=range(len(ob.data.vertices))
 e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());inv=(r.matrix_world@r.pose.bones['WPN_root'].matrix).inverted()
 pts=[list(inv@e.matrix_world@e.data.vertices[i].co) for i in vi]
 row['handle_closed_root']=pts
 row['read_frames']={str(f):{n:list((poses[f]['WPN_root'].inverted()@poses[f][n]).translation) for n in ['hand_l','hand_r','WPN_bolt']} for f in frames}
 out[gun]=row
 print('CHARGE_SOURCE',gun,a.name,'handle bounds',[[min(v[i] for v in pts),max(v[i] for v in pts)] for i in range(3)],'poses',row['read_frames'],flush=True)
(O/'pose_inputs.json').write_text(json.dumps(out))
print('CHARGE_INPUTS_READY',flush=True)
