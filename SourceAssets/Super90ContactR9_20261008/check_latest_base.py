from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
for f in (132,132.5,133,133.5,134,134.5,135):print('BASE_RETURN',f,collision(s['pose'](f,7,False)[0],False),flush=True)
for f in (0,75,90,114,125,133,146):
 p=s['pose'](f,7,False)[0]
 print('LENGTHS',f,{side:[100*((p[a+side].translation-p[b+side].translation).length-(s['rest'][a+side].translation-s['rest'][b+side].translation).length) for a,b in (('upperarm_','lowerarm_'),('lowerarm_','hand_'))] for side in ('l','r')},flush=True)
