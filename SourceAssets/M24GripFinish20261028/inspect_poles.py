from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
final=json.loads((OUT/'final_poses.json').read_text());grip={n:Matrix(m) for n,m in json.loads((OUT/'grip_pose.json').read_text()).items()};G=clips['idle'][0]['WPN_root']
axis=(grip['hand_r'].translation-grip['upperarm_r'].translation).normalized();p=grip['lowerarm_r'].translation-grip['upperarm_r'].translation;pole=(p-axis*p.dot(axis)).normalized()
print('CAMERA_POLE',list(C.to_3x3()@pole),flush=True)
for f in (0,22,23,24,25,40,41,42,43,44,45,55):
 row={n:Matrix(m) for n,m in final['fire'][f].items()};S=row['upperarm_r'].translation;H=row['hand_r'].translation;E=row['lowerarm_r'].translation
 print(f,'S',list(S),'H',list(H),'E',list(E),'pole_dot',(H-S).normalized().dot(pole),'metric',solve_frames(row,'r',0)[4:],flush=True)
