"""Scoped source-pose diagnosis of the reported near-body left sleeve clipping."""
from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'r20_core.py').read_text(encoding='utf-8'),str(O/'r20_core.py'),'exec'))
cloth=json.loads((S/'BenelliM4Super9020261006/EquipmentAuthored/Super90_ue_chainmail_shirt.json').read_text(encoding='utf-8'))
positions=np.asarray(cloth['positions']); weights=cloth['weights']; triangles=np.asarray(cloth['triangles'])
left=np.asarray([i for i,w in enumerate(weights) if sum(v for n,v in w.items() if n.endswith('_l'))>.9])
proximal=np.asarray([i for i in left if weights[i].get('upperarm_l',0)>.5])
adj=Counter(tuple(sorted(e)) for tri in triangles for e in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])))
edge={i for e,num in adj.items() if num==1 for i in e}
cap_ids=np.asarray([i for i in proximal if i in edge])
native_rest={n:mat(native['rest'][n]) for n in names}
native_inv={n:m.inverted() for n,m in native_rest.items()}
groups={}
for n in names:
    ids=np.asarray([int(i) for i in left if weights[i].get(n,0)>.00001])
    if len(ids):
        v=np.column_stack((positions[ids],np.ones(len(ids))))
        groups[n]=(ids, np.asarray([weights[i][n] for i in ids]),(np.asarray(native_inv[n])@v.T).T)
def cloth_points(p):
    out=np.zeros((len(positions),3))
    for n,(ids,w,local) in groups.items():
        transform=cam_matrix@np.asarray(p[n]@K[n])
        points=(transform@local.T).T[:,:3]
        out[ids]+=points*w[:,None]
    return out
FOV=112.; ASPECT=1276/837
TH=math.tan(math.radians(FOV/2)); TV=TH/ASPECT
def measures(points,ids):
    v=points[ids];x,y,z=v.T
    mask=(x>1)&(abs(y)<x*TH)&(abs(z)<x*TV)
    visible=v[mask]
    return {'visible':int(mask.sum()),'min_depth_cm':float(visible[:,0].min()) if len(visible) else None,
        'max_height':float((visible[:,2]/visible[:,0]/TV).max()) if len(visible) else None}
rows=[];poses={}
for branch,end in (('normal',144),('empty',180),('cycle',66)):
    name='A_Super90_loader_'+(branch if branch=='cycle' else branch+'_7')
    action=bpy.data.actions[name];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    poses[branch]=[]
    for f in range(end+1):
        scene.frame_set(f);bpy.context.view_layer.update()
        base={b.name:b.matrix.copy() for b in rig.pose.bones};poses[branch].append(base)
        for fam in ('base',*families):
            p=base if fam=='base' else adapt_profile(base,inputs[fam][name],f)
            pts=cloth_points(p)
            rows.append(dict(branch=branch,family=fam,frame=f,upper=measures(pts,proximal),cap=measures(pts,cap_ids),
                joints={n:list((cm@p[n].translation)) for n in ('upperarm_l','lowerarm_l','hand_l')}))
(O/'diagnosis.json').write_text(json.dumps({'camera':{'horizontal_fov':FOV,'aspect':ASPECT},'cap_vertices':len(cap_ids),'rows':rows},indent=2),encoding='utf-8')
for branch in poses:
    chosen=[r for r in rows if r['branch']==branch and r['family']=='base']
    worst=sorted(chosen,key=lambda r:(-(r['cap']['visible']),r['upper']['min_depth_cm'] or 100))[:3]
    print('R20_DIAG',json.dumps(worst),flush=True)
# Preserve the frame data for repair authoring without any source-pose resampling.
(O/'source_poses.json').write_text(json.dumps({b:[{n:[list(r) for r in m] for n,m in p.items()} for p in ps] for b,ps in poses.items()},separators=(',',':')),encoding='utf-8')
