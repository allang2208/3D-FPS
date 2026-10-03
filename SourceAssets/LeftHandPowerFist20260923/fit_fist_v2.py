"""Produce a tighter pose with real glove-surface constraints, no rendering.

Search only small changes around the accepted closed-fist profile. The source
mesh, skin weights, knuckle positions and all bone lengths stay unchanged.
"""
import bpy,json,itertools,sys,copy,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from finger_pose import closed_locals

bpy.ops.wm.open_mainfile(filepath=str(P/'LeftHand_PowerFist_Editable.blend'))
rig=bpy.data.objects['SK_M4_Infima']; mesh=bpy.data.objects['SK_Manny_Arms_Export']
scene=bpy.context.scene;action=bpy.data.actions['A_LeftHand_PowerFist']
rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
scene.frame_set(120);bpy.context.view_layer.update()
base={b.name:b.matrix.copy() for b in rig.pose.bones}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
rig.animation_data_clear()
for b in rig.pose.bones:
    m=base[parents[b.name]].inverted()@base[b.name] if parents[b.name] else base[b.name]
    b.matrix_basis=local[b.name].inverted()@m
digits=['index','middle','ring','pinky','thumb'];groups={g.index:g.name for g in mesh.vertex_groups}
mesh.data.calc_loop_triangles()
regions={d:set() for d in digits+['palm']}; tips={d:[] for d in digits}
for v in mesh.data.vertices:
    for d in digits:
        weight=sum(g.weight for g in v.groups if groups[g.group] in [d+'_01_l',d+'_02_l',d+'_03_l'])
        if weight>.85:regions[d].add(v.index)
        if sum(g.weight for g in v.groups if groups[g.group]==d+'_03_l')>.85:tips[d].append(v.index)
    if sum(g.weight for g in v.groups if groups[g.group]=='hand_l' or ('metacarpal' in groups[g.group] and groups[g.group].endswith('_l')))>.75:regions['palm'].add(v.index)
faces={d:[tuple(t.vertices) for t in mesh.data.loop_triangles if all(i in ids for i in t.vertices)] for d,ids in regions.items()}
reference=json.loads((P.parents[1]/'SourceAssets/RuneSword20260913/FistBraceGuardV20/pose_config.json').read_text())['fist']
for digit in reference.values():
    if not isinstance(digit['spread'],list):digit['spread']=[digit['spread']]*3
print('REGION_COUNTS', {d:(len(regions[d]),len(faces[d]),len(tips.get(d,[]))) for d in regions},flush=True)

def apply(profile):
    goal=closed_locals(rest,parents,profile);pose={n:m.copy() for n,m in base.items()}
    for n,q in goal.items():
        parent=parents[n];m=local[n].copy();m=Matrix.LocRotScale(m.translation,q,m.to_scale())
        pose[n]=pose[parent]@m
        rig.pose.bones[n].matrix_basis=local[n].inverted()@m
    bpy.context.view_layer.update()
    e=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
    vertices=[e.matrix_world@v.co for v in m.vertices];e.to_mesh_clear()
    trees={d:BVHTree.FromPolygons(vertices,f,all_triangles=True) for d,f in faces.items()}
    crossings={a+'-'+b:len(trees[a].overlap(trees[b])) for a,b in itertools.combinations(trees,2)}
    # Distance between physically disjoint surfaces: small positive clearance.
    gaps={};penetration=0.
    for d in digits:
        palm_dist=[]
        for i in tips[d]:
            near,normal,_,distance=trees['palm'].find_nearest(vertices[i])
            if near is None:continue
            signed=(vertices[i]-near).dot(normal)
            if signed<-.00025 and distance<.012:penetration+=(-signed-.00025)**2
            palm_dist.append(distance)
        palm_dist.sort();gaps[d]=palm_dist[max(0,int(len(palm_dist)*.1)-1)]*1000 if palm_dist else 20.
    hit=sum(crossings.values())
    # The contact objective tightens four fingers; thumb follows its outside
    # sweep with crossing constraints, never seeks the middle of the palm.
    pose_change=sum((a-b)**2 for d in digits for ch in ('flex','spread') for a,b in zip(profile[d][ch],reference[d][ch]))
    score=hit*10000+penetration*1e9+sum((gaps[d]-2.)**2 for d in digits[:4])+.03*pose_change
    return score,{'crossing_pairs':{k:v for k,v in crossings.items() if v},'tip_palm_gap_mm':gaps,'penetration_cost':penetration,'score':score}

best=copy.deepcopy(reference);score,baseline=apply(best);history=[]
print('FIST_SOURCE_SURFACES',json.dumps(baseline),flush=True)
# MCP tightens first; keep PIP/DIP increments modest. Search a bounded local
# neighborhood rather than solving each tip independently into an odd pose.
for step in (3.,1.5,.75):
    for repeat in range(5):
        changed=False
        for d in digits:
            for channel in range(6):
                for direction in (1.,-1.):
                    candidate=copy.deepcopy(best)
                    if channel<3:
                        # Cumulative flex means an MCP adjustment affects all
                        # descendants; a PIP change affects PIP and DIP only.
                        for k in range(channel,3):candidate[d]['flex'][k]+=step*direction
                        bound=10 if d!='thumb' else 6
                        if any(abs(a-b)>bound for a,b in zip(candidate[d]['flex'],reference[d]['flex'])):continue
                    else:
                        # Separate knuckle spacing from distal contact; one
                        # shared angle otherwise drags the little finger in.
                        for k in range(channel-3,3):candidate[d]['spread'][k]+=step*direction
                        if any(abs(a-b)>10 for a,b in zip(candidate[d]['spread'],reference[d]['spread'])):continue
                    value,metric=apply(candidate)
                    if value<score-.001:
                        best,score=candidate,value;history.append({'digit':d,'channel':channel,'step':step*direction,'score':score});changed=True
        if not changed:break
    print('FIST_FIT_STAGE',step,score,flush=True)
_,final=apply(best)
(P/'fist_profile_v2.json').write_text(json.dumps(best,indent=2),encoding='utf-8')
(P/'fist_fit_v2.json').write_text(json.dumps({'purpose':'surface-constrained authoring, not runtime acceptance','source':reference,'baseline':baseline,'result':final,'profile':best,'accepted_steps':history},indent=2),encoding='utf-8')
print('FIST_PROFILE_AUTHORED',json.dumps(final),flush=True)
