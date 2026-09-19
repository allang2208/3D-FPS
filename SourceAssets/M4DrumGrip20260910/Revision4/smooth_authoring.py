from pathlib import Path
p=Path(__file__).with_name('build_drop_reload.py')
s=p.with_suffix('.py.pre_smoothing').read_text()
s=s.replace('poses=[];rows=[]',"poses=[];rows=[];pole_angles={side:[] for side in ['l','r']}")
start=s.index(' for k,src in enumerate(raw):');end=s.index(" a.name='BeforeDrop_'",start)
block=s[start:end]
block=' for phase in [0,1]:\n'+''.join(' '+line+'\n' for line in block.splitlines())
key='pole=old.lerp(ip.lerp(anatomical,.12).normalized(),w).normalized();along='
repl='''pole=old.lerp(ip.lerp(anatomical,.12).normalized(),w).normalized()
    if phase==0:
     angle=math.atan2(axis.dot(anatomical.cross(pole)),anatomical.dot(pole))
     if pole_angles[side]:
      previous=pole_angles[side][-1];angle=previous+(angle-previous+math.pi)%(2*math.pi)-math.pi
     pole_angles[side].append(angle)
    else:pole=Quaternion(axis,pole_angles[side][k])@anatomical
    along='''
assert key in block
block=block.replace(key,repl)
block=block.replace("  poses.append({b.name:b.matrix_basis.copy() for b in r.pose.bones});rows.append(row)","  if phase:poses.append({b.name:b.matrix_basis.copy() for b in r.pose.bones});rows.append(row)")
block+='''  if phase==0:
   for side,values in pole_angles.items():
    # Smooth the unwrapped elbow-plane angle, preserving joint axes and hand contact.
    weights=[math.exp(-.5*(j/12)**2) for j in range(-36,37)];den=sum(weights)
    pole_angles[side]=[sum(weights[j+36]*values[max(0,min(len(values)-1,i+j))] for j in range(-36,37))/den for i in range(len(values))]
'''
p.write_text(s[:start]+block+s[end:])
