"""Read-only full timeline checks for the current author and saved UE poses."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent/'Diagnostics';P=O.parents[2]
author=P/'SourceAssets/Super90Speedloader20261007/author_speedloader.py';s={'__file__':str(author)}
exec(compile(author.read_text().split('def local_rows(')[0],str(author),'exec'),s)
out={'clips':[],'saved_comparison':{},'prefix_max_cm':0.}
bones=['hand_l','hand_r','lowerarm_l','lowerarm_r','upperarm_l','upperarm_r','WPN_root']
for family in ('base','vertical','canted','prism','angled'):
 for empty in (False,True):
    longest=[s['pose'](f,7,empty,family)[0] for f in range(s['duration'](7,empty)+1)]
    for count in range(1,8):
        frames=longest if count==7 else [s['pose'](f,count,empty,family)[0] for f in range(s['duration'](count,empty)+1)]
        maximum={n:{'cm':0.,'frame':0} for n in bones};max_spin={n:{'degrees':0.,'frame':0} for n in bones}
        length_error=0.;prefix=0.
        for f,p in enumerate(frames):
            if f<=s['last_frame'](count):
                for n in bones:prefix=max(prefix,100*(p[n].translation-longest[f][n].translation).length)
            if f:
                for n in bones:
                    jump=100*(p[n].translation-frames[f-1][n].translation).length
                    if jump>maximum[n]['cm']:maximum[n]={'cm':jump,'frame':f}
                    angle=p[n].to_quaternion().rotation_difference(frames[f-1][n].to_quaternion()).angle
                    deg=math.degrees(min(angle,2*math.pi-angle))
                    if deg>max_spin[n]['degrees']:max_spin[n]={'degrees':deg,'frame':f}
            for side in ('l','r'):
                for a,b in [('upperarm_','lowerarm_'),('lowerarm_','hand_')]:
                    native=(s['idle'][a+side].translation-s['idle'][b+side].translation).length
                    length_error=max(length_error,abs((p[a+side].translation-p[b+side].translation).length-native)*100)
        out['prefix_max_cm']=max(out['prefix_max_cm'],prefix)
        out['clips'].append({'family':family,'empty':empty,'count':count,'max_step':maximum,'max_rotation_step':max_spin,'bone_length_error_cm':length_error,'prefix_cm':prefix})
        begin=s['last_frame'](count)+(49 if empty else 2)
        out['clips'][-1]['return_elbow_step_cm']=max(100*(frames[k]['lowerarm_l'].translation-frames[k-1]['lowerarm_l'].translation).length for k in range(begin,len(frames)))
 print('CHECKED_FAMILY',family,flush=True)

(O/'source_motion.json').write_text(json.dumps(out,indent=2))
print('SOURCE_MOTION_CHECKED',len(out['clips']),flush=True)
