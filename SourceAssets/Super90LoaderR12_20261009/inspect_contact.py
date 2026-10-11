from pathlib import Path
O=Path(__file__).parent
g={'__file__':str(O/'r12_core.py')}
for part in ('r12_core.py','skin_arm.py','r12_motion.py'):
    exec(compile((O/part).read_text(),str(O/part),'exec'),g)
globals().update({k:v for k,v in g.items() if not k.startswith('__')})
ob=bpy.data.objects['Super90_bolt']
verts=[ob.matrix_world@v.co for v in ob.data.vertices]
print('MESH',ob.matrix_world, 'BBOX',[(min(v[i] for v in verts),max(v[i] for v in verts)) for i in range(3)],flush=True)
for n in ['WPN_root','WPN_bolt']:
    print(n,'REST',rest[n], 'IDLE',idle[n],flush=True)
outer=[v for v in verts if v.x>max(p.x for p in verts)-.012]
knob=sum(outer,Vector())/len(outer)
print('KNOB',tuple(knob),flush=True)
p=pose(150,7,True)[0]; mv=gun_move(150,7,True)
actual=p['WPN_bolt']@rest['WPN_bolt'].inverted()@knob
target=mv@BIND_TO_IDLE@HANDLE_OPEN_BIND
print('ACTUAL',tuple(cam(actual)),'TARGET',tuple(cam(target)),flush=True)
for b in rig.pose.bones:
    n=b.name;par=parents[n]
    b.matrix_basis=rest[n].inverted()@rest[par]@p[par].inverted()@p[n] if par else rest[n].inverted()@p[n]
bpy.context.view_layer.update()
print('BOLT_BINDING',ob.parent,ob.parent_type,ob.parent_bone,[(m.name,m.type) for m in ob.modifiers],[(v.name,v.index) for v in ob.vertex_groups],flush=True)
ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
pts=[ev.matrix_world@ev.data.vertices[v.index].co for v in ob.data.vertices if v.co.x>.02584]
print('EVALUATED',tuple(cam(sum(pts,Vector())/len(pts))),flush=True)
ob=bpy.data.objects['Super90_V7_M4_BareArmsV6']
from collections import Counter
edges=Counter(tuple(sorted(e)) for poly in ob.data.polygons for e in poly.edge_keys)
ids={i for edge,num in edges.items() if num==1 for i in edge}
caps=[]
for i in ids:
    v=ob.data.vertices[i]
    dominant=max(v.groups,key=lambda x:x.weight)
    n=ob.vertex_groups[dominant.group].name
    if n=='upperarm_l':caps.append(v.co.copy())
print('CAPCOUNT',len(caps),'CENTRE',tuple(sum(caps,Vector())/len(caps)) if caps else None,flush=True)
if caps:
    off=sum(caps,Vector())/len(caps)-rest['upperarm_l'].translation
    print('CAPOFFSET',tuple(off),'CAPCAM',tuple(cam(p['upperarm_l']@rest['upperarm_l'].inverted()@(off+rest['upperarm_l'].translation))),flush=True)
