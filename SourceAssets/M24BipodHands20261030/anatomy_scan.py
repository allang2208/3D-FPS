from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('metrics=[];')[0],'setup','exec'))
def twist(q,axis):
    if q.w<0:q=-q
    return math.degrees(2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w))
result=[]
initial=sample_pose(0)
initial_upper=initial['lowerarm_l'].translation-initial['upperarm_l'].translation
for t in [i/400 for i in range(193)]:
    row=sample_pose(t);u,l,h='upperarm_l','lowerarm_l','hand_l'
    U=row[l].translation-row[u].translation;L=row[h].translation-row[l].translation;normal=U.cross(L).normalized()
    uq,lq,hq=[row[n].to_quaternion() for n in (u,l,h)]
    axis=rest[l].to_quaternion().inverted()@(rest[h].translation-rest[l].translation).normalized()
    hrel=rest[l].to_quaternion().inverted()@rest[h].to_quaternion()
    erel=rest[u].to_quaternion().inverted()@rest[l].to_quaternion()
    swing=initial_upper.normalized().rotation_difference(U.normalized())
    upper_roll=twist(swing.inverted()@uq@initial[u].to_quaternion().inverted(),initial_upper.normalized())
    reference_normal=(rest[l].translation-rest[u].translation).cross(rest[h].translation-rest[l].translation).normalized()
    helper_axis=rest['upperarm_twist_02_l'].to_quaternion().inverted()@reference_normal
    metrics={'t':t,'elbow_flex':angle(U,L),'elbow_axial':twist((uq@erel).inverted()@lq,axis),
      'forearm_roll':twist(lq.inverted()@hq@hrel.inverted(),axis),
      'upperarm_roll_from_idle':upper_roll,'wrist_axis_bend':angle(L,row['middle_01_l'].translation-row[h].translation),
      'native_hinge_error':angle(row['upperarm_twist_02_l'].to_quaternion()@helper_axis,normal),
      'helper_z_to_hinge':angle(row['upperarm_twist_02_l'].to_quaternion()@Vector((0,0,1)),normal),
      'shoulder_cm':list(row[u].translation*100),'elbow_cm':list(row[l].translation*100),'wrist_cm':list(row[h].translation*100)}
    result.append(metrics)
print('REFERENCE',{'rest_hinge_to_helper_z':angle(rest['upperarm_twist_02_l'].to_quaternion()@Vector((0,0,1)),(rest[l].translation-rest[u].translation).cross(rest[h].translation-rest[l].translation)),
      'hand_long_local':list(rest[h].to_quaternion().inverted()@(rest['middle_01_l'].translation-rest[h].translation).normalized())},flush=True)
summary={k:[min(x[k] for x in result),max(x[k] for x in result)] for k in ('elbow_flex','elbow_axial','forearm_roll','upperarm_roll_from_idle','wrist_axis_bend','native_hinge_error')}
print('ANATOMY',json.dumps(summary),flush=True)
(O/'Review'/('anatomy_'+label+'.json')).write_text(json.dumps({'summary':summary,'samples':result},indent=2))
