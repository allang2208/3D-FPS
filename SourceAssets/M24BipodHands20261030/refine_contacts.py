"""Bounded actual-skin fit against both bipod legs and mounting bracket."""
from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('metrics=[];')[0],'setup','exec'))
digits=('thumb','index','middle','ring','pinky')
groups={g.index:g.name for g in skin.vertex_groups}
P0=np.array([v.co[:] for v in skin.data.shape_keys.key_blocks[0].data])
shapes={k.name:np.array([v.co[:] for v in k.data])-P0 for k in skin.data.shape_keys.key_blocks[1:]}
selections={};weights={}
for d in digits:
    ids=[v.index for v in skin.data.vertices if sum(g.weight for g in v.groups if groups[g.group].startswith(d+'_'))>.7]
    selections[d]=np.array(ids[::2]);weights[d]={}
    for k,i in enumerate(selections[d]):
        for g in skin.data.vertices[int(i)].groups:
            weights[d].setdefault(groups[g.group],np.zeros(len(selections[d])))[k]=g.weight
rest_inv={n:m.inverted() for n,m in rest.items()}
controls=[];report=[]
times=[0.,.035]+[i/1000 for i in range(40,111,5)]+[i/100 for i in range(12,39,2)]+[.405,.44,.48]
previous_offsets={}
for t in times:
    row=sample_pose(t);set_pose(row,t);original=clone(row)
    locals={n:row[parents[n]].inverted()@m if parents[n] else m for n,m in row.items()}
    delta=sum((shapes[k.name]*k.value for k in skin.data.shape_keys.key_blocks[1:] if k.value),np.zeros_like(P0))
    P=P0+delta;deps=bpy.context.evaluated_depsgraph_get();vertices=[];faces=[]
    for ob in parts:
        ev=ob.evaluated_get(deps);me=ev.to_mesh();offset=len(vertices)
        vertices.extend(ev.matrix_world@v.co for v in me.vertices);faces.extend(tuple(offset+i for i in p.vertices) for p in me.polygons);ev.to_mesh_clear()
    tree=BVHTree.FromPolygons(vertices,faces)
    changes={};scores={}
    for d in digits:
        selected=selections[d];points=P[selected];joints=[f'{d}_{j:02d}_l' for j in (1,2,3)]
        original_e=[(local_rest[n].inverted()@locals[n]).to_euler() for n in joints]
        vals=[e.copy() for e in original_e]
        def posed(vs):
            rr=dict(row)
            for n,e in zip(joints,vs):
                loc=locals[n];q=local_rest[n].to_quaternion()@e.to_quaternion()
                rr[n]=rr[parents[n]]@Matrix.LocRotScale(loc.translation,q,loc.to_scale())
            return rr
        def cost(vs):
            rr=posed(vs);X=np.zeros_like(points)
            for n,w in weights[d].items():
                M=np.array(rr[n]@rest_inv[n]);X+=(points@M[:3,:3].T+M[:3,3])*w[:,None]
            penalties=[]
            for p in X:
                hit=tree.find_nearest(Vector(p))
                if hit[0] is None or hit[3]>.018:continue
                signed=hit[3] if (Vector(p)-hit[0]).dot(hit[1])>=0 else -hit[3]
                penalties.append(max(0.,.0007-signed)**2)
            prior=sum((Vector(a)-Vector(b)).length_squared for a,b in zip(vs,original_e))
            offsets=[Vector(a)-Vector(b) for a,b in zip(vs,original_e)]
            temporal=sum((a-b).length_squared for a,b in zip(offsets,previous_offsets[d])) if d in previous_offsets else 0.
            return sum(penalties)*8e5+prior*.3+temporal*.15
        before=cost(vals)
        if .035<t<.405:
            for step in (6,3,1.5,.75):
                for _ in range(5):
                    changed=False
                    for j in range(3):
                        # No axial digit roll: MCP adduction and joint flexion only.
                        for dim in ((1,2) if j==0 else (2,)):
                            opts=[vals]
                            for sign in (-1,1):
                                vv=[e.copy() for e in vals];limit=math.radians(18 if dim==2 else 12)
                                vv[j][dim]=max(original_e[j][dim]-limit,min(original_e[j][dim]+limit,vv[j][dim]+math.radians(step)*sign));opts.append(vv)
                            best=min(opts,key=cost)
                            if cost(best)<cost(vals)-1e-8:vals=best;changed=True
                    if not changed:break
        rr=posed(vals)
        for n in joints:changes[n]=(rr[parents[n]].inverted()@rr[n]).to_quaternion()
        scores[d]=[round(before,3),round(cost(vals),3)]
        previous_offsets[d]=[Vector(a)-Vector(b) for a,b in zip(vals,original_e)]
    controls.append((t,changes));report.append({'time':t,'costs':scores})
    print('CONTACT_FIT',t,scores,flush=True)
for family,clip in data['clips'].items():
    # data here is the original 200 Hz author source, never a compressed resample.
    for i,values in enumerate(clip['frames']):
        t=i/rate;k=min(len(controls)-2,max(0,bisect.bisect_right(times,t)-1));a,b=controls[k:k+2]
        w=max(0.,min(1.,(t-a[0])/(b[0]-a[0])))
        for n,q0 in a[1].items():
            q=q0.slerp(b[1][n],w);local=(K@q.to_matrix().to_4x4()@K).to_quaternion();j=names.index(n)
            values[j][3:7]=[local.x,local.y,local.z,local.w]
with gzip.open(O/'authored.json.gz','wt') as f:json.dump(data,f)
(O/'Review/contact_fit.json').write_text(json.dumps(report,indent=2))
# Rebuild editable actions from exactly the amended payload.
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_Bipod_Hands_Editable.blend'),use_scripts=False)
r=bpy.data.objects['M24_V9_Rig']
for family in ('base','mag10'):
    action=bpy.data.actions['A_M24_Bipod_'+family+'_HandElbow30'];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    for i,values in enumerate(data['clips'][family]['frames']):
        for n in controls[0][1]:
            p,q,sc=unpack(values[names.index(n)]);local=K@Matrix.LocRotScale(p,q,sc)@K
            r.pose.bones[n].rotation_quaternion=(local_rest[n].inverted()@local).to_quaternion();r.pose.bones[n].keyframe_insert('rotation_quaternion',frame=i)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_Bipod_Hands_Editable.blend'))
print('CONTACT_REFINED',flush=True)
