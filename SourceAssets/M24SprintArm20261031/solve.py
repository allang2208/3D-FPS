from pathlib import Path
exec(compile((Path(__file__).parent/'diagnose.py').read_text().split("\nif __name__=='__main__':")[0],'sprint_setup','exec'))
def signed_twist(q,axis):
    if q.w<0:q=-q
    return 2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
def bend_plane(row,degrees):
    if abs(degrees)<1e-6:return clone(row)
    u,l,h='upperarm_l','lowerarm_l','hand_l';S,E,H=[row[n].translation for n in (u,l,h)]
    axis=(H-S).normalized();along=axis*(E-S).dot(axis);turn=Quaternion(axis,math.radians(degrees));newE=S+along+turn@(E-S-along)
    # Transport the complete elbow hinge frame, not two independent shortest
    # swing rotations; otherwise the hinge/skin rolls away from its bend plane.
    uq=turn@row[u].to_quaternion();lq=turn@row[l].to_quaternion()
    Um=Matrix.LocRotScale(S,uq,row[u].to_scale());Lm=Matrix.LocRotScale(newE,lq,row[l].to_scale());out=clone(row)
    for n in names:
        if under(n,h):continue
        if under(n,l):out[n]=Lm@row[l].inverted()@row[n]
        elif under(n,u):out[n]=Um@row[u].inverted()@row[n]
    ax=rest[l].to_quaternion().inverted()@(rest[h].translation-rest[l].translation).normalized()
    ref=(rest[l].to_quaternion().inverted()@rest[h].to_quaternion()).inverted()
    oldroll=signed_twist(row[l].to_quaternion().inverted()@row[h].to_quaternion()@ref,ax)
    roll=signed_twist(lq.inverted()@row[h].to_quaternion()@ref,ax)
    delta=(roll-oldroll+math.pi)%(2*math.pi)-math.pi
    for j,share in ((1,1.),(2,.5)):
        n=f'lowerarm_twist_{j:02d}_l';loc=row[l].inverted()@row[n]
        out[n]=Lm@Matrix.LocRotScale(loc.translation,Quaternion(ax,delta*share)@loc.to_quaternion(),loc.to_scale())
    return out
if __name__=='__main__':
    folder=O/'Candidates';folder.mkdir(exist_ok=True);row=runtime(1,0);out={}
    for degrees in (-45,-30,-15,0,15,30,45):
        candidate=bend_plane(row,degrees);out[str(degrees)]=detailed(candidate);view(candidate,folder/(str(degrees)+'.png'))
    (O/'candidates.json').write_text(json.dumps(out,indent=2));print('SPRINT_CANDIDATES',json.dumps({k:{'wrist':v['wrist_axis_bend'],'elbow_camera':v['camera_cm']['lowerarm_l'],'twist':v['twist_degrees']} for k,v in out.items()}),flush=True)
