from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
p=s['pose'](0,7,False)[0];initial={n:m.copy() for n,m in p.items()};out=[]
for axis_index in range(3):
 for degrees in range(-36,37,3):
    pose={n:m.copy() for n,m in initial.items()};root='thumb_01_l';q=pose[root].to_quaternion();axis=q@Vector(tuple(1. if i==axis_index else 0. for i in range(3)))
    origin=pose[root].translation;turn=Matrix.Translation(origin)@Matrix.Rotation(math.radians(degrees),4,axis)@Matrix.Translation(-origin)
    for n in ('thumb_01_l','thumb_02_l','thumb_03_l'):pose[n]=turn@pose[n]
    col=collision(pose,False,sides=('left',))['left']['gun']['count'];out.append((col,abs(degrees),axis_index,degrees,pose))
out.sort(key=lambda row:(row[0],row[1]));best=out[0];print('THUMB',best[:4],flush=True)
a=json.loads((O/'hand_fit.json').read_text());p=best[4]
for n in ('thumb_01_l','thumb_02_l','thumb_03_l'):a['idle_left_finger_local'][n]=[list(r) for r in p[s['parents'][n]].inverted()@p[n]]
(O/'hand_fit.json').write_text(json.dumps(a,indent=2))
rows=[]
for dx in (0.,.025,.05,.075):
 for dz in (-.05,-.075,-.10):
  for pole in (15,30,45,60):
    base={n:m.copy() for n,m in s['uncorrected_idles']['base'].items()};source={n:m.copy() for n,m in base.items()}
    for n in source:
     if n.endswith('_r'):source[n].translation+=s['right']*dx+s['up']*dz
    s['arm'](base,source,Matrix(a['right_hand_in_idle']),'r',pole_rotation=pole)
    for n in s['finger_names']['r']:base[n]=base[s['parents'][n]]@Matrix(a['right_finger_local'][n])
    col=collision(base,False,sides=('right',))['right']['gun']['count'];rows.append((col,dx*dx+dz*dz,pole,dx,dz))
rows.sort();print('RIGHT_SUPPORT',rows[:8],flush=True)
a=json.loads((O/'support_fit.json').read_text());a['idle_right_pole']=rows[0][2];a['idle_right_offset']=[rows[0][3],0.,rows[0][4]];(O/'support_fit.json').write_text(json.dumps(a,indent=2))
