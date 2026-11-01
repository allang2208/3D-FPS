from pathlib import Path
P=Path(__file__).resolve().parent
exec(compile((P/'author_motion.py').read_text().split('# Do not trade')[0],str(P/'author_motion.py'),'exec'))
e,ua,fa,n,qu,qf=support(s0,h0,pole0)
print('IDLE_HINGE',{'upper_roll':math.degrees(axial(idle[U].to_quaternion()@qu.inverted(),ua)),
 'lower_roll':math.degrees(axial(idle[F].to_quaternion()@qf.inverted(),fa)),
 'rest_normal':list(rn),'rest_upper_z':list(rest['upperarm_twist_02_r'].to_quaternion()@Vector((0,0,1)))},flush=True)
