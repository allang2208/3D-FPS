"""Repair the lower folded display skin; keep geometry, rig and body joints.

The false body-labelled crease strips share the same field as their adjoining
leaves. UV/material splits are welded only in the weight solver, not the mesh.
No cloth, runtime solver, rendered preview or gameplay test is added.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT=ROOT/'MembraneSkinV35'
MASTER=ROOT/'BodyMotionV18/Proxy/M07_Original_GillContacts_V18.blend'
PYTHON='C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe'

def smooth(t):
    t=np.clip(t,0.,1.)
    return t*t*(3.-2.*t)

def write(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def solve():
    from scipy.sparse import coo_matrix, diags
    from scipy.sparse.csgraph import connected_components,dijkstra
    from scipy.spatial import cKDTree
    data=np.load(OUT/'surface_input.npz')
    pos,old,names,labels=data['p'],data['w'],data['names'].tolist(),data['labels']
    ref=json.loads((OUT/'rig_input.json').read_text())
    _,first,weld=np.unique(np.round(pos/.001).astype(np.int32),axis=0,return_index=True,return_inverse=True)
    p=pos[first].astype(float);count=len(p);num=len(names)
    field=np.zeros((count,num));np.add.at(field,weld,old)
    field/=np.bincount(weld)[:,None]
    member=np.zeros((count,7),bool);member[weld,labels]=True
    edges=np.unique(np.sort(weld[data['e']],axis=1),axis=0)
    edges=edges[edges[:,0]!=edges[:,1]]
    length=np.linalg.norm(p[edges[:,1]]-p[edges[:,0]],axis=1)
    a,b=edges.T
    graph=coo_matrix((np.r_[length,length],(np.r_[a,b],np.r_[b,a])),shape=(count,count)).tocsr()

    # Anatomical support follows the actual head-to-child segments, not the
    # bone display tails. This keeps the accepted body/arm/leg skin protected.
    clearance=np.full(count,np.inf)
    for name,row in ref.items():
        parent=row['parent']
        if not parent or name.startswith(('gill_','root')) or parent=='root':continue
        if name.startswith(('spine_','pelvis')):radius=25.
        elif name.startswith(('neck_','head')):radius=20.
        elif name.startswith(('thigh_','calf_')):radius=16.
        elif name.startswith(('foot_','ball_')):radius=13.
        elif name.startswith(('clavicle_','upperarm_')):radius=19.
        elif name.startswith(('lowerarm_','hand_')):radius=13.
        else:radius=9.
        start=np.asarray(ref[parent]['head']);axis=np.asarray(row['head'])-start
        t=np.clip((p-start)@axis/max(float(axis@axis),1.e-10),0,1)
        clearance=np.minimum(clearance,np.linalg.norm(p-start-t[:,None]*axis,axis=1)-radius)
    membrane=member[:,1:].any(axis=1)
    # Original face labels put thin remote fold strips into the body section.
    # Grow only over the connected posterior surface outside real anatomy.
    candidate=(p[:,2]<246.)&(p[:,1]>0.)&(clearance>4.)
    region=membrane|candidate
    keep=region[a]&region[b]
    region_graph=coo_matrix((np.ones(keep.sum()*2),(np.r_[a[keep],b[keep]],np.r_[b[keep],a[keep]])),shape=(count,count)).tocsr()
    _,components=connected_components(region_graph,directed=False)
    leaf_components=np.unique(components[membrane])
    false_body=candidate&member[:,0]&np.isin(components,leaf_components)
    # Include tiny UV split islands only where they lie directly on that fold.
    near=cKDTree(p[membrane]).query(p,k=1)[0]
    false_body|=candidate&member[:,0]&(near<.5)
    true_body=member[:,0]&~false_body
    editable=(membrane|false_body)&~true_body&(p[:,2]<246.)

    # Common lower sheet driver per side: roots stay attached to the existing
    # shoulders; the hanging folds use the long leaf chain (02 / 05).
    target=np.zeros_like(field)
    for side,panel in ((1,2),(-1,5)):
        rows=np.flatnonzero(p[:,0]*side>=0)
        chain=[f'gill_{panel:02d}_{j:02d}' for j in range(3)]
        points=np.asarray([ref[n]['head'] for n in chain]+[ref[chain[-1]]['tail']])
        delta=np.diff(points,axis=0);lens=np.linalg.norm(delta,axis=1);stations=np.r_[0.,np.cumsum(lens)]
        distances=[];along=[]
        for start,axis,L,station in zip(points,delta,lens,stations):
            t=np.clip((p[rows]-start)@axis/max(float(axis@axis),1.e-10),0,1)
            distances.append(np.linalg.norm(p[rows]-start-t[:,None]*axis,axis=1))
            along.append(station+t*L)
        best=np.argmin(np.asarray(distances),axis=0)
        progress=np.asarray(along)[best,np.arange(len(rows))]
        first_blend=smooth(progress/max(stations[1],1.e-6))
        tip_blend=smooth((progress-stations[1])/max(stations[3]-stations[1],1.e-6))
        target[rows,names.index(chain[0])]=1-first_blend
        target[rows,names.index(chain[1])]=first_blend*(1-tip_blend)
        target[rows,names.index(chain[2])]=first_blend*tip_blend

    # The long chains are children of neck_02. Giving them full ownership of
    # a sheet also attached to the lower torso transfers head turns down a
    # two-metre lever. Let the ribcage carry the connected lower tissue and
    # retain only 15% leaf follow-through; never anchor it to thighs or hands.
    target*=.15
    target[:,names.index('spine_03')]+=.85

    # Only real body attachments remain anchors. Removed body-labelled
    # crease strips must not become new anchors in this distance solve.
    boundary_edges=edges[true_body[a]^true_body[b]]
    seeds=np.unique(boundary_edges[true_body[boundary_edges]])
    distance,_,origins=dijkstra(graph,directed=False,indices=seeds,min_only=True,return_predecessors=True)
    root_blend=smooth(distance/36.)
    anchored=field.copy();valid=origins>=0;anchored[valid]=field[origins[valid]]
    common=anchored*(1-root_blend[:,None])+target*root_blend[:,None]
    lower=smooth((246.-p[:,2])/42.)
    result=field.copy()
    result[editable]=field[editable]*(1-lower[editable,None])+common[editable]*lower[editable,None]
    # Diffuse only the repaired surface, holding true body and upper roots.
    # A length-weighted field avoids a material/UV boundary becoming a hinge.
    conductance=1./np.maximum(length,.1)
    adjacency=coo_matrix((np.r_[conductance,conductance],(np.r_[a,b],np.r_[b,a])),shape=(count,count)).tocsr()
    average=diags(1./np.maximum(np.asarray(adjacency.sum(axis=1)).ravel(),1.e-10))@adjacency
    seed_field=result.copy()
    for _ in range(70):
        relaxed=average@result
        result[editable]=.15*seed_field[editable]+.85*relaxed[editable]
    result=np.maximum(result,0.)
    ids=np.argsort(-result,axis=1,kind='stable')[:,:8]
    value=np.take_along_axis(result,ids,axis=1)
    value/=np.maximum(value.sum(axis=1,keepdims=True),1.e-10)
    packed=np.zeros_like(result);np.put_along_axis(packed,ids,value,axis=1)
    repaired=old.copy()
    selected=editable[weld]
    repaired[selected]=packed[weld[selected]]
    # True body rows stay byte-for-byte; coincident membrane copies adopt
    # the protected body row instead of moving the body to fit the membrane.
    for node in np.flatnonzero(true_body&membrane):
        copies=np.flatnonzero(weld==node)
        body_copy=copies[labels[copies]==0][0]
        repaired[copies[labels[copies]!=0]]=old[body_copy]
    changed=np.sum(np.abs(repaired-old),axis=1)>1.e-7
    np.savez_compressed(OUT/'skin_solution.npz',weights=repaired,changed=changed,offsets=data['offsets'])
    write('skin_solution_record.json',dict(changed_vertices=int(changed.sum()),
        changed_body_section_fold_vertices=int((changed&(labels==0)).sum()),
        changed_leaf_vertices={str(i):int((changed&(labels==i)).sum()) for i in range(1,7)},
        false_body_fold_welds=int(false_body.sum()),root_transition_surface_cm=36.,upper_transition_cm=[204.,246.],
        method='Common same-side lower membrane field, actual-surface attachment distance, protected real body skin, solver-only welded seams',
        lower_driver_chains=['gill_02','gill_05'],thorax_support_bone='spine_03',thorax_support_fraction=.85,maximum_influences=8,
        visible_geometry_modified=False,reference_pose_modified=False,runtime_tested=False,rendered=False))
    print('M07_V35_SKIN_FIELD_AUTHORED '+str(int(changed.sum())),flush=True)

def author():
    import bpy
    from mathutils import Matrix
    sys.path.insert(0,str(Path(__file__).parent))
    import author_original_surfaces_v08 as surfaces
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    rig.animation_data_clear();rig.data.pose_position='REST'
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    names=[b.name for b in rig.data.bones]
    display=[bpy.data.objects['M07_OriginalBody_Display']]+[bpy.data.objects[f'M07_OriginalGill_{i:02d}_Display'] for i in range(1,7)]
    positions=[];weights=[];edges=[];labels=[];offsets=[0]
    for label,obj in enumerate(display):
        p=np.asarray([v.co[:] for v in obj.data.vertices],np.float32)
        w=np.zeros((len(p),len(names)),np.float32)
        groups={g.index:names.index(g.name) for g in obj.vertex_groups if g.name in names}
        for v in obj.data.vertices:
            for g in v.groups:
                if g.group in groups:w[v.index,groups[g.group]]=g.weight
        positions.append(p);weights.append(w);labels.append(np.full(len(p),label))
        edges.append(np.asarray([list(e.vertices) for e in obj.data.edges])+offsets[-1]);offsets.append(offsets[-1]+len(p))
    np.savez_compressed(OUT/'surface_input.npz',p=np.concatenate(positions),w=np.concatenate(weights),e=np.concatenate(edges),
        labels=np.concatenate(labels),offsets=offsets,names=np.asarray(names))
    write('rig_input.json',{b.name:dict(head=list(b.head_local),tail=list(b.tail_local),parent=b.parent.name if b.parent else None) for b in rig.data.bones})
    subprocess.run([PYTHON,str(Path(__file__).resolve()),'--solve'],check=True)
    solution=np.load(OUT/'skin_solution.npz')
    for label,obj in enumerate(display):
        start,end=offsets[label:label+2]
        changed=np.flatnonzero(solution['changed'][start:end])
        groups={g.name:g for g in obj.vertex_groups}
        for group in groups.values():group.remove(changed.tolist())
        rows=solution['weights'][start:end]
        for v in changed:
            for i in np.flatnonzero(rows[v]>0):groups[names[i]].add([int(v)],float(rows[v,i]),'REPLACE')
        obj['membrane_skin_revision']='V35 common lower sheet, original visible surface and protected anatomy'
    fbx=OUT/'SK_M07_Display_MembraneSkinV35.fbx'
    blend=OUT/'M07_MembraneSkinV35.blend'
    surfaces.export(fbx,rig,display)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
    record=json.loads((OUT/'skin_solution_record.json').read_text())
    record.update(revision='MembraneSkinV35',source=str(blend),display_fbx=str(fbx),original_master=str(MASTER),
        bone_count=len(names),display_vertices=sum(len(o.data.vertices) for o in display),
        display_triangles=sum(len(o.data.polygons) for o in display),source_saved=True,fbx_exported=True,
        uv_modified=False,material_slots_modified=False,new_runtime_solver=False,particle_cloth=False,ue_saved=False,user_review_pending=True)
    write('membrane_skin_manifest_v35.json',record)
    print('M07_V35_SOURCE_AND_FBX_SAVED '+str(fbx),flush=True)

if __name__=='__main__':
    if '--solve' in sys.argv:solve()
    else:author()
