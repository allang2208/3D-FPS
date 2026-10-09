"""Locate the reported sprint bend in saved motion and the actual sleeve binding."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
author=O.parent/'Super90TacticalSprint20261007/author_sprint.py'
s={'__file__':str(author)}
exec(compile(author.read_text().split('profiles={f:')[0],str(author),'exec'),s)
rest=s['rest'];names=s['names'];parents=s['parents'];I=Matrix.Identity(4)
current=json.loads((O/'current.json').read_text())
report={'motion':[]}
def deform(row,family):
    world={};tracks={}
    if family!='base':
        entry=next(e for e in current['profiles'][family] if e['base']==current['clips']['enter']['asset'])
        for t in entry['tracks']:
            ts=t['times'];i=min(range(len(ts)),key=lambda i:abs(ts[i]-row['time']))
            tracks[t['bone']]=t['values'][i*10:i*10+10]
    for n in names:
        local=s['uemat'](row['local'][n])
        if n in tracks:
            v=tracks[n];p,q,z=local.decompose()
            local=Matrix.LocRotScale(p+Vector(v[:3]),Quaternion((v[6],*v[3:6]))@q,z+Vector(v[7:10]))
        world[n]=world.get(parents[n],I)@local
    return {n:s['evaluation_to_author']@s['Ci']@world[n]@s['Ki'][n] for n in names}
for row in current['clips']['enter']['rows']:
    for family in ('base','vertical','angled','canted','prism'):
        actual=deform(row,family);expected=s['pose'](row['time']/.3,None,family)
        errors={n:100*(actual[n].translation-expected[n].translation).length for n in names}
        angles={n:math.degrees(2*math.acos(min(1.,abs(actual[n].to_quaternion().rotation_difference(expected[n].to_quaternion()).w)))) for n in names}
        shoulder,elbow,wrist=[actual[n].translation for n in ('upperarm_l','lowerarm_l','hand_l')]
        report['motion'].append({'family':family,'mode':row['mode'],'time':row['time'],
            'position_error_max_cm':max(errors.values()),'position_error_bone':max(errors,key=errors.get),
            'rotation_error_max_deg':max(angles.values()),'rotation_error_bone':max(angles,key=angles.get),
            'left':{n:{'p':list(actual[n].translation),'q':list(actual[n].to_quaternion()),'err_cm':errors[n],'err_deg':angles[n]} for n in ('upperarm_l','lowerarm_l','lowerarm_aux_l','hand_l')},
            'elbow_bend':math.degrees((elbow-shoulder).angle(wrist-elbow))})
# Fit the camera exactly as RifleHipFraming does: its M4 ruler and Super90 gun-up axis.
f=current['framing']
def frame(key,up):
    d=f[key];r=s['uemat'](d['WPN_root']);a=(Vector(d['WPN_FrontSight'][:3])-Vector(d['WPN_RearSight'][:3])).normalized()
    z=r.to_quaternion()@Vector(up);y=z.cross(a).normalized();z=a.cross(y).normalized()
    return Matrix((a,y,z)).transposed().to_quaternion()
base_rot=Quaternion(Vector((0,0,1)),math.pi/2)
rotation=base_rot@frame('M4',(0,0,1))@frame('Super90',(0,-1,0)).inverted()
target=Vector((6,7,-7))+base_rot@Vector(f['M4']['hand_r'][:3])
location=target-rotation@Vector(f['Super90']['hand_r'][:3])
report['framing']={'location_cm':list(location),'rotation':list(rotation),'M4_hand':f['M4']['hand_r']}
def cam(p):return location+rotation@Vector((p.x*100,-p.y*100,p.z*100))
report['camera_joints']={family:{n:list(cam(s['pose'](1.,None,family)[n].translation)) for n in ('upperarm_l','lowerarm_l','hand_l')} for family in s['idles']}
cloth=json.loads((O.parent/'BenelliM4Super9020261006/EquipmentAuthored/Super90_ue_chainmail_shirt.json').read_text())
points=[Vector((v[0]/100,-v[1]/100,v[2]/100)) for v in cloth['positions']]
for family in ('base','vertical'):
    p=s['pose'](1.,None,family);transforms={n:p[n]@rest[n].inverted() for n in names}
    samples=[]
    for i,(v,w) in enumerate(zip(points,cloth['weights'])):
        if sum(x for n,x in w.items() if n.endswith('_l'))<.95:continue
        x=sum((transforms[n]@v*z for n,z in w.items()),Vector());c=cam(x)
        if c.x>1 and abs(c.y/c.x)<1.4 and -.65<c.z/c.x<.5:
            samples.append({'index':i,'camera':list(c),'weights':w,'rest':list(v),'pose':list(x)})
    samples.sort(key=lambda r:r['camera'][2]/r['camera'][0],reverse=True)
    report.setdefault('visible_sleeve',{})[family]={'count':len(samples),'top':samples[:8]}
(O/'deformation_trace.json').write_text(json.dumps(report,indent=2))
print('MOTION_ERRORS',json.dumps({mode:max(x['position_error_max_cm'] for x in report['motion'] if x['mode']==mode) for mode in ('SOURCE','COMPRESSED')}),flush=True)
print('CAMERA_JOINTS',json.dumps(report['camera_joints']),flush=True)
print('VISIBLE_SLEEVE',json.dumps(report['visible_sleeve']),flush=True)
