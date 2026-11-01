from pathlib import Path
exec(compile((Path(__file__).parent/'diagnose.py').read_text().split("\nif __name__=='__main__':")[0],'setup','exec'))
def align_shoulder(row,degrees=12.):
    if abs(degrees)<1e-7:return clone(row)
    out=clone(row);u,l,h='upperarm_l','lowerarm_l','hand_l'
    S,E,H=[row[n].translation for n in (u,l,h)]
    normal=(E-S).cross(H-E).normalized();turn=Quaternion(normal,math.radians(degrees))
    moved=Matrix.LocRotScale(E+turn@(S-E),turn@row[u].to_quaternion(),row[u].to_scale())
    for n in names:
        if under(n,u) and not under(n,l):out[n]=moved@row[u].inverted()@row[n]
    # Restore the native shoulder-to-humerus relation at the existing upper-arm
    # pose. The elbow, forearm, wrist and all digits stay at their accepted pose.
    out['clavicle_l']=out['upperarm_l']@rest['upperarm_l'].inverted()@rest['clavicle_l']
    return out

def upper_view(row,path):
    set_pose(row);r.matrix_world=Matrix.Identity(4);target=(row['upperarm_l'].translation+row['lowerarm_l'].translation)/2
    cam.location=target+Vector((-.45,-.22,.18));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.46
    advanced.matrix_world=row['WPN_root']@rest['WPN_root'].inverted()@advanced_rest
    s.render.filepath=str(path);bpy.ops.render.render(write_still=True)

if __name__=='__main__':
    folder=O/'Candidate';folder.mkdir(exist_ok=True);result={}
    for p,phase in ((0,0),(.15,0),(.3,0),(.5,0),(1,0),(1,.5)):
        row=runtime(p,phase);fixed=align_shoulder(row,12*ease(p/.65));key=f'{p}_{phase}'
        view(fixed,folder/(key+'_fps.png'));upper_view(fixed,folder/(key+'_outer.png'))
        oldlocal=row['clavicle_l'].inverted()@row['upperarm_l'];newlocal=fixed['clavicle_l'].inverted()@fixed['upperarm_l']
        result[key]={'clavicle_shift_cm':(row['clavicle_l'].translation-fixed['clavicle_l'].translation).length*100,'old_shoulder_frame_deg':math.degrees(oldlocal.to_quaternion().rotation_difference(local_rest['upperarm_l'].to_quaternion()).angle),'new_shoulder_frame_deg':math.degrees(newlocal.to_quaternion().rotation_difference(local_rest['upperarm_l'].to_quaternion()).angle)}
    (O/'candidate.json').write_text(json.dumps(result,indent=2));print('SHOULDER_CANDIDATE',json.dumps(result),flush=True)
