"""Blender authoring: retain the accepted hand, topology and all skin weights.

Only the dorsal surface is relaxed (<= 0.6 mm). Grip surfaces, open boundaries,
forearms, sleeves, reference bones and animations are not reshaped or rebound.
"""
import json, math
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4'
data=json.loads((ROOT/'M4_original.json').read_text())
def point(p):return Vector((p[0],-p[1],p[2]))*.01
def ue(p):return [p.x*100,-p.y*100,p.z*100]
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
bones={n:point(b['position']) for n,b in data['bones'].items()}
frames={}
for s in ('l','r'):
    forward=(bones['middle_01_'+s]-bones['hand_'+s]).normalized()
    across=(bones['index_01_'+s]-bones['pinky_01_'+s]).normalized()
    dorsal=forward.cross(across).normalized()
    a=(bones['middle_02_'+s]-bones['middle_01_'+s]).normalized()
    bend=bones['middle_03_'+s]-bones['middle_02_'+s]
    if dorsal.dot(bend-a*bend.dot(a))>0:dorsal=-dorsal
    frames[s]=(forward,across,dorsal)

bpy.ops.wm.open_mainfile(filepath=str(PROJECT/'SourceAssets/M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend'))
original=bpy.data.objects['SK_Manny_Arms_Export']
obj=original.copy();obj.data=original.data.copy();bpy.context.collection.objects.link(obj)
obj.name='M4_OriginalShape_BareHands';obj.data.name='Manny_OriginalTopology_BareHands'
original.hide_render=True;original.hide_set(True)
names={g.index:g.name for g in obj.vertex_groups}
verts=obj.data.vertices;parent=list(range(len(verts)));neighbors=[set() for _ in verts]
def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
for e in obj.data.edges:
    a,b=e.vertices;parent[find(b)]=find(a);neighbors[a].add(b);neighbors[b].add(a)
parts={}
for v in verts:parts.setdefault(find(v.index),[]).append(v.index)
prefix=('hand_','thumb_','index_','middle_','ring_','pinky_')
handparts={k for k,ids in parts.items() if sum(sum(g.weight for g in verts[i].groups if names[g.group].startswith(prefix)) for i in ids)/len(ids)>.5}
is_hand=[find(i) in handparts for i in range(len(verts))]
# Boundaries include the seams between the separate accepted finger/hand shells.
edge_use={}
for poly in obj.data.polygons:
    ids=list(poly.vertices)
    for a,b in zip(ids,ids[1:]+ids[:1]):
        key=tuple(sorted((a,b)));edge_use[key]=edge_use.get(key,0)+1
locked={i for edge,count in edge_use.items() if count!=2 for i in edge}
for _ in range(2):locked|={j for i in list(locked) for j in neighbors[i]}
positions=[v.co.copy() for v in verts]
basis=obj.shape_key_add(name='Original_Tactical_Glove_Basis')
shape=obj.shape_key_add(name='Bare_Dorsal_Surface_0p6mm_Max')
frozen=obj.vertex_groups.new(name='AUTHOR_Grip_And_Seam_Lock')
deltas=[]
for i,v in enumerate(verts):
    p=positions[i];s='l' if p.x<0 else 'r';dorsal=frames[s][2]
    weight=0.0
    if is_hand[i] and i not in locked:
        dominant=max(v.groups,key=lambda g:g.weight)
        bone=names[dominant.group]
        if bone.startswith(('index_','middle_','ring_','pinky_','thumb_')) and '_metacarpal_' not in bone:
            raw=data['bones'][bone]['axes'][0];axis=Vector((raw[0],-raw[1],raw[2])).normalized()
            dorsal=(dorsal-axis*dorsal.dot(axis)).normalized()
        weight=smooth(.25,.75,v.normal.dot(dorsal))
        # The thumb web is also a contact area; leave its grip clearance exact.
        thumbweb=(p-bones['thumb_01_'+s]).length
        weight*=smooth(.020,.034,thumbweb)
    if weight<=0:frozen.add([i],1,'REPLACE')
    delta=Vector()
    if weight>0 and neighbors[i]:
        average=sum((positions[j] for j in neighbors[i]),Vector())/len(neighbors[i])
        # Remove only raised padding. Do not inflate hollows or narrow digits.
        inward=min(0,(average-p).dot(v.normal))
        delta=v.normal*max(-.0006,inward*.42)*weight
    shape.data[i].co=p+delta;deltas.append(delta)
shape.value=1.0
obj['AuthoringContract']='Native weights/rest pose and contact surfaces preserved; dorsal-only deltas; original topology and UV.'
obj['MaxDorsalDisplacementMM']=.6
# Retain original native provenance. Author-only lock group is not exported.
tree=KDTree(len(verts))
for i,p in enumerate(positions):tree.insert(p,i)
tree.balance()
mapped=[];newpositions=[];hand=[]
for p in data['positions']:
    pos=point(p);_,i,distance=tree.find(pos)
    if distance>.00003:raise RuntimeError('Source correspondence missing; refusing to alter the native hand')
    mapped.append(i);hand.append(is_hand[i]);newpositions.append(ue(pos+deltas[i]))
materials=[2 if sum(hand[i] for i in tri)>=2 else (0 if m==data['arm_materials'][0] else 1)
           for tri,m in zip(data['triangles'],data['triangle_materials'])]
# Texture-authoring frame data comes from the accepted native bones, not a donor.
anatomy={}
for s in ('l','r'):
    dorsal=frames[s][2];rows=[]
    for stem in ('thumb','index','middle','ring','pinky'):
        for segment in (1,2,3):
            name=f'{stem}_{segment:02}_{s}';head=bones[name]
            if segment<3:axis=(bones[f'{stem}_{segment+1:02}_{s}']-head).normalized()
            else:
                raw=data['bones'][name]['axes'][0];axis=Vector((raw[0],-raw[1],raw[2])).normalized()
                if axis.dot(head-bones[f'{stem}_02_{s}'])<0:axis=-axis
            back=(dorsal-axis*dorsal.dot(axis)).normalized();across=axis.cross(back).normalized()
            samples=[point(p)-head for p,w in zip(data['positions'],data['weights']) if w.get(name,0)>.6]
            extents=sorted(q.dot(axis) for q in samples)
            radius=sorted(abs(q.dot(across)) for q in samples)
            length=(bones[f'{stem}_{segment+1:02}_{s}']-head).length if segment<3 else max(.012,extents[int(.985*(len(extents)-1))])
            rows.append({'bone':name,'digit':stem,'segment':segment,'head':ue(head),
                'axis':ue(axis/100),'dorsal':ue(back/100),'across':ue(across/100),
                'length':length*100,'radius':radius[int(.92*(len(radius)-1))]*100})
    anatomy[s]={'wrist':ue(bones['hand_'+s]),'forward':ue(frames[s][0]/100),
                'dorsal':ue(dorsal/100),'across':ue(frames[s][1]/100),'digits':rows}
out={'source':data['source'],'source_vertex_ids':data['source_vertex_ids'],
     'source_triangle_ids':data['source_triangle_ids'],'positions':newpositions,
     'triangle_materials':materials,'hand_vertices':hand,'anatomy':anatomy,
     'geometry_policy':{'dorsal_limit_mm':.6,'contact_vertices_frozen':True,
       'original_weights_retained':True,'original_uv_retained':True,'forearm_and_sleeve_unchanged':True}}
(ROOT/'M4_bare_shape.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'M4_OriginalShape_BareHands_Editable.blend'))
print('ORIGINAL_SHAPE_BARE_M4_AUTHORED',len(newpositions),'vertices; native topology and weights retained')
