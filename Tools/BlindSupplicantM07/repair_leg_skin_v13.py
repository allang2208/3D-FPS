"""Localized M07 V13 leg field repair and V12 source diagnosis.

The immutable Meshy body, original UVs, V11 hand field and 83-bone reference
stay intact. Both UV duplicates and reduced-surface vertices receive a real
same-body field, rather than interpolated integer source IDs. No UE or render.
"""
from pathlib import Path
import argparse
import json
import math
import sys

import numpy as np

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'RecoveryV13Legs'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def smooth(x):
    x = np.clip(x, 0., 1.)
    return x*x*(3.-2.*x)


def sparse(indices, values, count):
    field = np.zeros((len(indices), count), np.float32)
    rows = np.broadcast_to(np.arange(len(indices))[:, None], indices.shape)
    np.add.at(field, (rows, indices), values)
    return field


def pack(field):
    indices = np.argpartition(field, -8, axis=1)[:, -8:]
    values = np.take_along_axis(field, indices, axis=1)
    order = np.argsort(-values, axis=1, kind='stable')
    indices = np.take_along_axis(indices, order, axis=1).astype(np.int16)
    values = np.take_along_axis(values, order, axis=1)
    values /= np.maximum(values.sum(axis=1, keepdims=True), 1.e-12)
    return indices, values.astype(np.float32)


def edge_stats(field, edges, length):
    delta = np.abs(field[edges[:, 0]]-field[edges[:, 1]]).sum(axis=1)
    short = length < 1.
    return {'edges':int(len(edges)), 'short_edges':int(short.sum()),
            'short_edges_weight_l1_over_1':int((short & (delta > 1.)).sum()),
            'short_edges_weight_l1_over_0_5':int((short & (delta > .5)).sum()),
            'max_short_edge_l1':float(delta[short].max(initial=0.)),
            'max_l1_per_cm':float((delta/np.maximum(length, .001)).max(initial=0.))}


def mesh_dump(obj, names):
    """Numerical only, actual saved source weights and reduced IDs."""
    p = np.empty((len(obj.data.vertices), 3), np.float32)
    obj.data.vertices.foreach_get('co', p.ravel())
    selected = p[:, 2] < 151.
    ids = np.flatnonzero(selected)
    remap = np.full(len(p), -1, np.int32); remap[ids] = np.arange(len(ids))
    faces = np.asarray([list(f.vertices) for f in obj.data.polygons], np.int32)
    faces = faces[selected[faces].all(axis=1)]
    edges = np.empty((len(obj.data.edges), 2), np.int32)
    obj.data.edges.foreach_get('vertices', edges.ravel())
    edges = edges[selected[edges].all(axis=1)]
    field = np.zeros((len(ids), len(names)), np.float32)
    lookup = {n:i for i,n in enumerate(names)}
    group = {g.index:lookup[g.name] for g in obj.vertex_groups if g.name in lookup}
    for i in ids:
        for g in obj.data.vertices[i].groups:
            if g.group in group: field[remap[i], group[g.group]] = g.weight
    sid = np.asarray([a.value for a in obj.data.attributes['source_vertex_id'].data], np.int32)
    packed, values = pack(field)
    np.savez_compressed(OUT/(obj.name+'_legs_diagnosis.npz'), positions_cm=p[ids],
        mesh_vertex_ids=ids, source_vertex_ids=sid[ids], faces=remap[faces],
        edges=remap[edges], bone_names=np.asarray(names), bone_indices=packed, bone_weights=values)
    e = remap[edges]; length = np.linalg.norm(p[edges[:,0]]-p[edges[:,1]], axis=1)
    return edge_stats(field, e, length)


def diagnose():
    import bpy
    from mathutils import Vector
    sys.path.insert(0, str(Path(__file__).parent))
    import author_motion_v04 as motion
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'RunningV12/M07_Original_Running_V12.blend'))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    names = list(rest)
    report = {'scope':'User-reported V12 knee misalignment, source-only local diagnosis',
              'runtime_tested':False, 'rendered':False, 'reference':{}, 'clips':{}, 'weights':{}}
    for side in ('l','r'):
        a,b,c = [rest[n+'_'+side].translation for n in ('thigh','calf','foot')]
        axis = (c-a).normalized(); pole = b-a-axis*(b-a).dot(axis)
        report['reference'][side] = {'hip_cm':list(a), 'knee_cm':list(b), 'ankle_cm':list(c),
            'lengths_cm':[(b-a).length,(c-b).length], 'reference_knee_pole':list(pole.normalized()),
            'reference_knee_pole_vs_forced_forward_deg':math.degrees(pole.angle(Vector((0,-1,0))))}
    manifest = json.loads((ROOT/'RunningV12/motion_manifest_v12.json').read_text(encoding='utf-8'))
    rig.data.pose_position = 'POSE'
    for role, entry in manifest['clips'].items():
        motion.activate(rig, bpy.data.actions[entry['action']])
        frames=[]; previous={}; max_pole=max_twist=max_loc=max_length_error=0.
        for frame in range(1, entry['frames']+1):
            bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
            pelvis = rig.pose.bones['pelvis'].matrix.to_quaternion()@rest['pelvis'].to_quaternion().inverted()
            record={'frame':frame,'legs':{}}
            for side in ('l','r'):
                matrices=[rig.pose.bones[n+'_'+side].matrix.copy() for n in ('thigh','calf','foot','ball')]
                a,b,c,d=[m.translation for m in matrices]
                u,v=(b-a).normalized(),(c-b).normalized(); normal=u.cross(v).normalized()
                local = pelvis.inverted()@normal
                if side in previous:max_pole=max(max_pole,math.degrees(local.angle(previous[side])))
                previous[side]=local
                twists={}
                for n,vec,m in zip(('thigh','calf'),(u,v),matrices):
                    nxt='calf' if n=='thigh' else 'foot'
                    ref=(rest[nxt+'_'+side].translation-rest[n+'_'+side].translation).normalized()
                    swing=ref.rotation_difference(vec)
                    delta=m.to_quaternion()@rest[n+'_'+side].to_quaternion().inverted()
                    residual=swing.inverted()@delta
                    theta=math.degrees(2*math.acos(min(1.,abs(residual.normalized().w))))
                    twists[n]=theta;max_twist=max(max_twist,theta)
                    p=rig.pose.bones[n+'_'+side];max_loc=max(max_loc,p.location.length)
                ref_lengths=report['reference'][side]['lengths_cm']
                max_length_error=max(max_length_error,abs((b-a).length-ref_lengths[0]),abs((c-b).length-ref_lengths[1]))
                record['legs'][side]={'hip_cm':list(a),'knee_cm':list(b),'ankle_cm':list(c),'ball_cm':list(d),
                    'bend_degrees':math.degrees(u.angle(v)),'axial_residual_degrees':twists}
            frames.append(record)
        report['clips'][role]={'max_pole_step_pelvis_deg':max_pole,'max_extra_axial_rotation_deg':max_twist,
            'max_child_translation_cm':max_loc,'max_segment_length_error_cm':max_length_error,'frames':frames}
    for n in ('M07_OriginalBody_High','M07_OriginalBody_Display'):
        report['weights'][n]=mesh_dump(bpy.data.objects[n],names)
    write_json(OUT/'v12_leg_source_diagnosis.json',report)
    print('M07_V13_LEG_DIAGNOSIS '+json.dumps({k:v for k,v in report.items() if k not in ('clips',)}),flush=True)
    for role,entry in report['clips'].items():
        print(role+' '+json.dumps({k:v for k,v in entry.items() if k!='frames'}),flush=True)


def prepare_weights():
    from scipy.sparse import coo_matrix, diags
    source = np.load(ROOT/'Authoring/source_mesh.npz')
    raw=source['positions'].astype(np.float64); faces=source['indices'].reshape(-1,3)
    regions=np.load(ROOT/'RecoveryOriginalV06/regions/source_regions_original_v06.npz')
    base=dict(np.load(ROOT/'RecoveryHandsV11/weights/original_arm_hand_skin_weights_v11.npz'))
    names=base['bone_names'].tolist();lookup={n:i for i,n in enumerate(names)}
    guides=json.loads((ROOT/'RecoveryOriginalV08/rig_motion/original_rig_guides.json').read_text(encoding='utf-8'))
    scale=310./np.ptp(raw[:,1]);points=np.c_[raw[:,0],-raw[:,2],raw[:,1]-raw[:,1].min()]*scale
    _,first,welded=np.unique(regions['source_welded_vertex_ids'],return_index=True,return_inverse=True)
    p=points[first];body_faces=welded[faces[regions['face_labels']==0]]
    body=np.zeros(len(first),bool);body[np.unique(body_faces)]=True
    gill=np.zeros(len(first),bool);gill[np.unique(welded[faces[regions['face_labels']!=0]])]=True
    edges=np.concatenate([body_faces[:,[0,1]],body_faces[:,[1,2]],body_faces[:,[2,0]]]);edges.sort(axis=1)
    edges=np.unique(edges,axis=0);edges=edges[edges[:,0]!=edges[:,1]]
    lengths=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1)
    changed=np.zeros(len(first),bool);details=[];all_ids=[];all_indices=[];all_values=[]
    for side,sign in (('l',1.),('r',-1.)):
        selected=body&~gill&(p[:,0]*sign>.2)&(p[:,2]<132.)
        selected&=(np.abs(p[:,0])<43.)&(p[:,1]>-38.)&(p[:,1]<49.)
        ids=np.flatnonzero(selected);q=p[ids]
        field=sparse(base['bone_indices'][first[ids]],base['bone_weights'][first[ids]],len(names))
        before=field.copy();anatomical=np.zeros_like(field)
        hip,knee,ankle,ball=[np.asarray(guides['bone_heads_cm'][n+'_'+side]) for n in ('thigh','calf','foot','ball')]
        # A monotonic anatomical chart cannot switch to a different segment
        # at the nearest-distance Voronoi boundary behind a bent knee.
        hip_mix=smooth((hip[2]+7.-q[:,2])/21.)
        knee_mix=smooth((knee[2]+10.-q[:,2])/20.)
        ankle_mix=smooth((ankle[2]+6.-q[:,2])/12.)
        ball_mix=smooth((-q[:,1]-.012*scale)/(.078*scale))
        anatomical[:,lookup['pelvis']]=1.-hip_mix
        anatomical[:,lookup['thigh_'+side]]=hip_mix*(1.-knee_mix)
        anatomical[:,lookup['calf_'+side]]=hip_mix*knee_mix*(1.-ankle_mix)
        foot_total=hip_mix*knee_mix*ankle_mix
        # Toe fan/plantar support stays on foot/ball; no calf nearest-shaft jump.
        toe_region=smooth((16.-q[:,2])/9.)*ball_mix
        anatomical[:,lookup['foot_'+side]]=foot_total*(1.-toe_region)
        anatomical[:,lookup['ball_'+side]]=foot_total*toe_region
        alpha=smooth((132.-q[:,2])/19.)
        alpha*=smooth((43.-np.abs(q[:,0]))/7.)*smooth((q[:,1]+38.)/8.)*smooth((49.-q[:,1])/9.)
        field=field*(1.-alpha[:,None])+anatomical*alpha[:,None]
        field/=np.maximum(field.sum(axis=1,keepdims=True),1.e-12)
        remap=np.full(len(p),-1,np.int32);remap[ids]=np.arange(len(ids));ee=remap[edges]
        use=(ee>=0).all(axis=1);ee=ee[use];el=lengths[use]
        conductance=1./(el*el+.25)
        adjacent=coo_matrix((np.r_[conductance,conductance],(np.r_[ee[:,0],ee[:,1]],np.r_[ee[:,1],ee[:,0]])),shape=(len(ids),len(ids))).tocsr()
        degree=np.asarray(adjacent.sum(axis=1)).ravel();average=diags(1./np.maximum(degree,1.e-12))@adjacent
        anchor=field.copy();diffused=field.copy()
        for _ in range(8):
            diffused=.2*anchor+.8*(average@diffused);diffused[degree==0.]=anchor[degree==0.]
        # Only hip continuity needs graph diffusion; lower shafts retain the
        # smooth anatomical field, rather than flattening their joint bands.
        hip_band=smooth((q[:,2]-109.)/6.)*smooth((132.-q[:,2])/6.)
        field=field*(1.-hip_band[:,None])+diffused*hip_band[:,None]
        packed,values=pack(field);field=sparse(packed,values,len(names))
        all_ids.append(ids);all_indices.append(packed);all_values.append(values);changed[ids]=True
        actual_leg=(q[:,2]<114.)&(np.abs(q[:,0])<36.)&(q[:,1]>-30.)&(q[:,1]<40.)
        actual_edges=actual_leg[ee].all(axis=1)
        details.append({'side':side,'welded_vertices':len(ids),'before':edge_stats(before,ee,el),'after':edge_stats(field,ee,el),
            'actual_leg_before':edge_stats(before,ee[actual_edges],el[actual_edges]),
            'actual_leg_after':edge_stats(field,ee[actual_edges],el[actual_edges]),
            'joint_blend_width_cm':{'knee':20.,'ankle':12.,'hip':21.}})
    new_i=base['bone_indices'].copy();new_w=base['bone_weights'].copy()
    ids=np.concatenate(all_ids);mapping=np.full(len(first),-1,np.int32);mapping[ids]=np.arange(len(ids))
    rows=np.flatnonzero(changed[welded]);index=np.concatenate(all_indices);values=np.concatenate(all_values)
    new_i[rows]=index[mapping[welded[rows]]];new_w[rows]=values[mapping[welded[rows]]]
    base['bone_indices']=new_i;base['bone_weights']=new_w;base['repaired_leg_source_vertex_ids']=rows.astype(np.int32)
    path=OUT/'original_continuous_leg_weights_v13.npz';np.savez_compressed(path,**base)
    write_json(OUT/'leg_skin_delivery_v13.json',{'revision':'OriginalV13Legs','weights':str(path),
        'base':'OriginalV11 original-arm-hand field; only original body leg rows changed','bone_names':names,
        'modified_source_vertices':len(rows),'modified_welded_vertices':int(changed.sum()),'sides':details,
        'original_uv_and_geometry_changed':False,'bone_reference_changed':False,'gill_vertices_modified':int((changed&gill).sum()),
        'display_transfer':'Apply the NPZ to High exact source IDs, then call apply_to_master() for body-only barycentric leg projection',
        'runtime_tested':False,'rendered':False,'user_accepted':False})
    print('M07_V13_CONTINUOUS_LEG_WEIGHTS_SAVED '+str(path),flush=True)


def apply_to_master(rig=None):
    """Root assembler calls this after loading the V11 model/83-bone reference."""
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    sys.path.insert(0,str(Path(__file__).parent))
    import author_hands_arms_v11 as arm
    import author_original_surfaces_v08 as surfaces
    weights=np.load(OUT/'original_continuous_leg_weights_v13.npz');names=weights['bone_names'].tolist()
    high=bpy.data.objects['M07_OriginalBody_High'];display=bpy.data.objects['M07_OriginalBody_Display']
    hp,hf=arm.mesh_arrays(high);source_ids=np.asarray([a.value for a in high.data.attributes['source_vertex_id'].data],np.int32)
    old=arm.sparse_field(high,names);new=old.copy();selected=hp[:,2]<132.
    new[selected]=sparse(weights['bone_indices'][source_ids[selected]],weights['bone_weights'][source_ids[selected]],len(names))
    ii,ww=pack(new);surfaces.assign(high,names,ii,ww)
    field=arm.sparse_field(display,names);p,_=arm.mesh_arrays(display);target=np.flatnonzero(p[:,2]<132.)
    tree=BVHTree.FromPolygons(hp.tolist(),hf.tolist(),all_triangles=True)
    bary=np.zeros((len(p),3),np.float32);face_ids=np.full(len(p),-1,np.int32);max_distance=0.
    for i in target:
        hit,normal,face,distance=tree.find_nearest(Vector(p[i]));max_distance=max(max_distance,float(distance))
        a,b,c=hp[hf[face]];ab,ac,q=b-a,c-a,np.asarray(hit)-a
        aa,bb,cc=float(ab@ab),float(ab@ac),float(ac@ac);den=aa*cc-bb*bb
        if abs(den)<1.e-12:w=np.asarray([1.,0.,0.])
        else:
            v=(cc*float(q@ab)-bb*float(q@ac))/den;z=(aa*float(q@ac)-bb*float(q@ab))/den
            w=np.maximum([1.-v-z,v,z],0.);w/=max(w.sum(),1.e-12)
        field[i]=(new[hf[face]]*w[:,None]).sum(axis=0);bary[i]=w;face_ids[i]=face
    # Actual coincident reduced seam copies must share a field, regardless of
    # their different original integer IDs or UV islands.
    _,first,inverse=np.unique(np.rint(p/.0003).astype(np.int64),axis=0,return_index=True,return_inverse=True)
    field[target]=field[first[inverse[target]]]
    ii,ww=pack(field);surfaces.assign(display,names,ii,ww)
    for name,type_,value in [('leg_weight_source_high_triangle','INT',face_ids),('leg_weight_source_barycentric','FLOAT_VECTOR',bary)]:
        if name in display.data.attributes:display.data.attributes.remove(display.data.attributes[name])
        attribute=display.data.attributes.new(name=name,type=type_,domain='POINT')
        attribute.data.foreach_set('value' if type_=='INT' else 'vector',value.ravel())
    display['leg_weight_transfer_revision']='OriginalV13 actual original body high triangle barycentric leg field, not interpolated source_vertex_id'
    return {'original_high_leg_vertices':int(selected.sum()),'display_leg_vertices_reprojected':len(target),
            'max_same_body_surface_distance_cm':max_distance,'geometry_changed':False,'uv_changed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['diagnose','weights'],default='weights')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    OUT.mkdir(parents=True,exist_ok=True)
    diagnose() if args.mode=='diagnose' else prepare_weights()
