"""Read the existing authored pose landmarks for the rear-carry layout."""
from pathlib import Path
P = Path(__file__).parent
code = (P/'author_sprint.py').read_text()
exec(compile(code.split('manifest =')[0],str(P/'author_sprint.py'),'exec'))
for variant in ('Standard','LongGrip'):
    data=json.loads((P/(variant+'_inputs.json')).read_text())
    idle=from_ue(data['clips']['Idle']['samples'][0]['world'])
    ready=idle['WPN_root']
    grips={s:ready.inverted()@idle['hand_'+s] for s in ('l','r')}
    pivot=(grips['l'].translation+grips['r'].translation)*.5
    ready_center=ready@pivot
    blade_axis=(idle['Blade_Tip'].translation-idle['Blade_Base'].translation).normalized()
    carry_rotation=Quaternion(Vector((0,1,0)),math.radians(CFG['blade_roll_degrees']))@blade_axis.rotation_difference(Vector((0,1,0)))@ready.to_quaternion()
    pose=pose_from_weapon(ready_to_carry(1.),1.,{})
    names=['clavicle_l','upperarm_l','lowerarm_l','hand_l','clavicle_r','upperarm_r','lowerarm_r','hand_r','WPN_root','Blade_Base','Blade_Tip']
    print('LAYOUT '+variant+' '+json.dumps({n:[round(v,4) for v in pose[n].translation] for n in names}),flush=True)
