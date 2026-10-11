"""Rejected hypothesis: segment transport differs only by float noise.
This diagnostic does not author the production bind surface; use fair_bind_surface.py.
"""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[1]
g=json.loads((O/'geometry.json').read_text());rest={n:Matrix(m) for n,m in g['rest'].items()}
with bpy.data.libraries.load(str(P/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/M4_BareArmsV7.blend'),link=False) as (available,loaded):loaded.objects=list(available.objects)
rig=next(o for o in loaded.objects if o and o.type=='ARMATURE');oldrest={b.name:b.matrix_local.copy() for b in rig.data.bones}
def mapped(n):
    if n.startswith('upperarm_twist'):return 'upperarm_'+n[-1]
    if n in ('lowerarm_l','lowerarm_r'):return 'lowerarm_aux_'+n[-1]
    return n if n in rest else 'lowerarm_'+n[-1] if n.startswith('lowerarm_twist') else n
def frame(data,n):
    side=n[-1];p=data[n].translation
    nxt=('lowerarm_'+side if n.startswith('upperarm') else 'hand_'+side if n.startswith('lowerarm') else 'middle_01_'+side if n.startswith('hand_') else None)
    if '_metacarpal_' in n:nxt=n.split('_')[0]+'_01_'+side
    elif any(n.startswith(d+'_') for d in ('thumb','index','middle','ring','pinky')):
        bits=n.split('_');k=int(bits[1]);nxt=bits[0]+'_%02d_'%(k+1)+side if k<3 else None
    if nxt and nxt in data:x=data[nxt].translation-p
    elif n.endswith(('_l','_r')) and '_03_' in n:x=p-data[n.replace('_03_','_02_')].translation
    else:x=data[n].to_3x3().col[0].normalized()*.025
    width=data['index_01_'+side].translation-data['pinky_01_'+side].translation
    forward=data['middle_01_'+side].translation-data['hand_'+side].translation
    z=forward.cross(width).normalized();length=max(x.length,.005);x.normalize();y=z.cross(x).normalized();z=x.cross(y).normalized()
    m=Matrix((x,y,z)).transposed().to_4x4();m.translation=p;return m,length,width.length
def warp(source,target):
    a,la,wa=frame(oldrest,source);b,lb,wb=frame(rest,target)
    radial=wb/max(wa,1e-6);return b@Matrix.Diagonal((lb/la,radial,radial,1))@a.inverted()
old={};new={}
for n in oldrest:
    target=mapped(n)
    if target not in rest or not n.endswith(('_l','_r')):continue
    source='upperarm_'+n[-1] if n.startswith('upperarm_twist') else n
    old[n]=warp(source,target)
    # The original transport stretches each helper's remaining distance to
    # the wrist independently, collapsing rings near the elbow even at bind.
    new[n]=warp('lowerarm_l','lowerarm_l') if n.startswith('lowerarm') and n.endswith('_l') else old[n]
mesh=next(o for o in loaded.objects if o and o.type=='MESH' and len(o.data.vertices)==len(g['meshes']['Super90_V7_M4_BareArmsV6']['positions']))
groups={v.index:v.name for v in mesh.vertex_groups};original=g['meshes']['Super90_V7_M4_BareArmsV6']['positions'];edited=[];errors=[]
for v in mesh.data.vertices:
    inf=[(a.weight,groups[a.group]) for a in v.groups if groups[a.group] in old];total=sum(w for w,n in inf)
    a=sum((old[n]@v.co*w for w,n in inf),Vector())/total
    b=sum((new[n]@v.co*w for w,n in inf),Vector())/total
    errors.append((a-Vector(original[v.index])).length)
    if (b-a).length>1e-7:edited.append(dict(index=v.index,before=original[v.index],after=list(Vector(original[v.index])+b-a)))
print('RECONSTRUCTION',max(errors), 'edited',max(errors[e['index']] for e in edited), 'worst',sorted(range(len(errors)),key=lambda i:errors[i])[-6:],flush=True)
if max(errors[e['index']] for e in edited)>.0001:raise RuntimeError('Source bind differs; preserve it: '+str(max(errors)))
report=dict(reason='Whole-segment left forearm transport replaces incompatible fractional-helper geometry warps',
            edited_vertices=len(edited),source_reconstruction_max_m=max(errors),edits=edited,runtime_tested=False)
(O/'bind_transport_diagnostic.json').write_text(json.dumps(report,separators=(',',':')))
print('SUPER90_R23_BIND_REPAIR',len(edited),'vertices, source error',max(errors),flush=True)
