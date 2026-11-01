from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'author_sprint.py').read_text().split('# Fit one continuous')[0],'sprint_carry_setup','exec'))
for side in ('l','r'):
 print('IDLE',side,{n:[round(x,2) for x in C@idle[n+'_'+side].translation] for n in ('upperarm','lowerarm','hand')})
for offset in ((2,8,-7),(-5,8,-12),(-8,6,-14),(-10,6,-18),(-5,4,-18)):
 CarryOffset=Vector(offset);result={}
 for side in ('l','r'):
  S=idle['upperarm_'+side].translation;E=idle['lowerarm_'+side].translation;H=idle['hand_'+side].translation;length=(E-S).length+(H-E).length
  result[side]=max((target_transform(p)@H-S).length/length for p in np.linspace(0,1,61))
 print('CARRY_FIT',offset,result,flush=True)
