"""Read current SVD glove, joint frames and magazine dimensions for grip authoring."""
import bpy, json, ast
from pathlib import Path
O=Path(__file__).parent;S=O.parent
t=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='sample'],type_ignores=[]),'<sample>','exec'))
src=S/'SVDMagazineSeat20260923/SVD_base_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(src));r=bpy.data.objects['SK_M4_Infima']
p=sample(r,bpy.data.actions['A_SVD_reload'],220)
skin=bpy.data.objects['SK_Manny_Arms_Export'];rest={b.name:b.matrix_local.copy() for b in r.data.bones}
names=['hand_l']+[b.name for b in r.data.bones if b.name.endswith('_l') and b.name.startswith(('thumb','index','middle','ring','pinky'))]
gn={g.index:g.name for g in skin.vertex_groups};indices=[];vertices=[];weights=[];labels=[]
for v in skin.data.vertices:
 w={gn[g.group]:g.weight for g in v.groups if g.weight>1e-6}
 if sum(w.get(n,0) for n in names)<.985:continue
 indices.append(v.index);vertices.append(list(r.matrix_world.inverted()@skin.matrix_world@v.co))
 weights.append({n:x for n,x in w.items() if n in names});labels.append(max(w,key=w.get))
ids=set(indices);lookup={i:j for j,i in enumerate(indices)}
faces=[[lookup[i] for i in f.vertices] for f in skin.data.polygons if all(i in ids for i in f.vertices)]
parents={n:r.data.bones[n].parent.name for n in names}
basis={n:[list(row) for row in ((rest[parents[n]].inverted()@rest[n]).inverted()@p[parents[n]].inverted()@p[n])] for n in names[1:]}
vs=[];fs=[]
# Include the finished outer shell, not the old pre-detail geometry or the bore.
ob=bpy.data.objects['SM_SVD_Magazine'];xf=(r.matrix_world@rest['WPN_SOCKET_Magazine']).inverted()@ob.matrix_world
vs=[list(xf@v.co) for v in ob.data.vertices];fs=[list(f.vertices) for f in ob.data.polygons]
d={'source':str(src),'names':names,'parents':parents,'rest':{n:[list(row) for row in rest[n]] for n in names},
 'vertices':vertices,'indices':indices,'weights':weights,'labels':labels,'faces':faces,'basis':basis,
 'hand_in_mag':[list(row) for row in (p['WPN_SOCKET_Magazine'].inverted()@p['hand_l'])],
 'magazine':{'vertices':vs,'faces':fs}}
(O/'inputs.json').write_text(json.dumps(d))
print('SVD_CURRENT_GRASP_INPUT',len(vertices),len(faces),len(vs),len(fs),flush=True)
print('SVD_CURRENT_MAGAZINE_SIZE_MM',[round((max(v[i] for v in vs)-min(v[i] for v in vs))*1000,3) for i in range(3)],flush=True)
