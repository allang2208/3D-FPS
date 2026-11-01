exec(open(__file__.replace('read_frames.py','diagnose.py'),encoding='utf-8').read().split('out={}')[0])
for role,f in [('aim',0),('sprint_loop',7),('fire',28)]:
 pose(role,f)
 for side in ('l','r'):
  print(role,side,[(n,[round(x,2) for x in C@r.pose.bones[n+'_'+side].matrix.translation]) for n in ('upperarm','lowerarm','hand')],flush=True)
 if role=='fire':
  bone=r.pose.bones['WPN_BoltHandle'];bolt=bpy.data.objects['M24_bolt'];me=bolt.data
  print('BOLT_SOURCE',[[min(v.co[i] for v in me.vertices),max(v.co[i] for v in me.vertices)] for i in range(3)],flush=True)
  print('BOLT_REST', [list(x) for x in rest['WPN_BoltHandle']],flush=True)
  print('RIGHT_HAND', [list(x) for x in bone.matrix.inverted()@r.pose.bones['hand_r'].matrix],flush=True)
  print('DIGITS',[(n,round(math.degrees((rest[r.data.bones[n].parent.name].inverted()@rest[n]).to_quaternion().rotation_difference((r.pose.bones[r.data.bones[n].parent.name].matrix.inverted()@r.pose.bones[n].matrix).to_quaternion()).angle),1)) for n in rest if n.endswith('_r') and '_03_' in n],flush=True)
