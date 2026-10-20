"""Requested grip/wrist/skin and unchanged-motion checks on actual Gunplay."""
from diagnose_grip import O,R6,s,measure,camera_for_frame
import sys,json,numpy as np
from scipy.spatial.transform import Rotation as R
mode=sys.argv[1] if len(sys.argv)>1 else 'candidate'
capture=json.loads((O/f'native-{mode}.json').read_text());prior=json.loads((R6/'native-saved-glove.json').read_text())
T=s.bare.T;edges=np.sort(np.vstack([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]),axis=1);edges,count=np.unique(edges,axis=0,return_counts=True)
v=s.bare.first[np.unique(edges[count==1])];bn=[s.names[j] for j in s.bare.weights.argmax(1)]
cut=np.array([j for j in v if bn[j].endswith('_r') and bn[j].startswith(('upperarm','clavicle'))])
fixed=[j for j,n in enumerate(s.names) if n.endswith('_l') or n.startswith('WPN_')]
fingers=[j for j,n in enumerate(s.names) if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))]
results={};summary={}
for family,old in zip(capture['families'],prior['families']):
    order=[family['names'].index(n) for n in s.names];idle=s.matrices(np.array(family['frames'][0]['bones'])[order]);camera=s.matrices([family['view_to_camera']])[0]
    rows=[];root_bad=[];immutable=0.;fixed_position=0.;fixed_angle=0.;entry_delta=0.;joint=0.;digit=0.;handfolds=0
    for r,previous in zip(family['frames'],old['frames']):
        p=s.matrices(np.array(r['bones'])[order]);q=s.matrices(np.array(previous['bones'])[order]);m=measure(p,idle)
        rows.append({'frame':r['frame'],'alpha':r['action_alpha'],**m})
        if 0<r['frame']<5:entry_delta=max(entry_delta,float(np.linalg.norm(p[s.ids['WPN_root'],:3,3]-q[s.ids['WPN_root'],:3,3])))
        immutable=max(immutable,float(abs(p[fixed]-q[fixed]).max()))
        fixed_position=max(fixed_position,float(np.linalg.norm(p[fixed,:3,3]-q[fixed,:3,3],axis=1).max()))
        pr=p[fixed,:3,:3];qr=q[fixed,:3,:3]
        pr=pr/np.linalg.norm(pr,axis=1)[:,None,:];qr=qr/np.linalg.norm(qr,axis=1)[:,None,:]
        fixed_angle=max(fixed_angle,float(np.degrees((R.from_matrix(pr)*R.from_matrix(qr).inv()).magnitude()).max()))
        joint=max(joint,max(s.offsets(p).values()))
        for j in fingers:digit=max(digit,float(abs(s.relative(p[s.parents[j]],p[j])-s.relative(q[s.parents[j]],q[j])).max()))
        surface=s.bare.evaluate(p,r['morphs']);handfolds=max(handfolds,s.bare.folds(surface));view=camera_for_frame(camera,r['frame'])
        cv=surface[cut]@view[:3,:3].T+view[:3,3];tv=np.tan(np.radians(37.5));th=tv*2.65
        visible=(cv[:,0]>1)&(abs(cv[:,1])<cv[:,0]*th)&(abs(cv[:,2])<cv[:,0]*tv)
        if visible.any():root_bad.append([r['frame'],int(visible.sum())])
    full=[r for r in rows if r['alpha']>.9999]
    summary[family['family']]={'max_full_action_grip_offset_cm':max(r['grip_offset_cm'] for r in full),
        'max_blended_grip_offset_cm':max(r['grip_offset_cm'] for r in rows),'max_full_action_grip_rotation_degrees':max(r['grip_rotation_degrees'] for r in full),
        'max_wrist_axis_bend_degrees':max(r['wrist_axis_bend_degrees'] for r in rows),'max_native_joint_offset_cm':joint,
        'max_left_weapon_matrix_error_all_frames':immutable,'entry_root_difference_cm':entry_delta,
        'max_left_weapon_position_error_cm':fixed_position,'max_left_weapon_rotation_error_degrees':fixed_angle,
        'max_finger_local_matrix_error':digit,'hand_normal_disagreement_count':handfolds,'root_cut_visible':root_bad}
    results[family['family']]=rows
passed=all(v['max_native_joint_offset_cm']<.01 and v['max_left_weapon_position_error_cm']<.003
    and v['max_left_weapon_rotation_error_degrees']<.01
    and v['entry_root_difference_cm']<.003 and v['max_blended_grip_offset_cm']<.01
    and v['max_full_action_grip_rotation_degrees']<.1 and v['max_wrist_axis_bend_degrees']<35
    and not v['root_cut_visible'] for v in summary.values())
(O/f'grip-runtime-{mode}.json').write_text(json.dumps({'passed':passed,'summary':summary,'families':results,'interactive_game_tested':False},indent=2))
print(json.dumps({'passed':passed,'summary':summary},indent=2),flush=True)
if not passed:raise SystemExit(1)
