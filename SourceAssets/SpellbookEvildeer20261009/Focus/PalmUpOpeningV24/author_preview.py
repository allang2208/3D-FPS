"""Append finger release and two-sided opening to the accepted V23 take.

The accepted 0-.90 s arm/book samples are copied verbatim. During opening
the book object stays at the captured grip frame; covers unfold on their
own hinges, with a small spine tilt into the original 25-degree page plane.
No runtime sources or accepted V23 files are written.
"""
import json, math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

OUT=Path(__file__).resolve().parent; P=OUT.parent; ROOT=P.parents[2]
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def ease(a,b,t):
    u=float(np.clip((t-a)/(b-a),0,1)); return u*u*u*(u*(6*u-15)+10)
def mix_rotation(a,b,t):
    return Slerp([0,1],R.from_matrix([a,b]))([t]).as_matrix()[0]

accepted=read(P/'PalmUpPreviewV23/candidate.json')
landing=read(P/'VideoRecovery20261010/landing-baseline-v9.json')
native=read(ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json')['bones']
names=accepted['arm_order']; byindex={b['index']:n for n,b in native.items()}
parent={n:byindex.get(b['parent']) for n,b in native.items()}
events={'turn_end':.90,'hand_open_start':.95,'hand_open_end':1.25,
        'detach':.95,'hand_lower_start':1.14,'hand_lower_end':1.62,
        'open_start':1.28,'open_end':1.94,'duration':2.70}
turn_index=round(events['turn_end']*60)
held=accepted['poses'][turn_index]
held_local={n:np.array(m) for n,m in held['local'].items()}
held_world={n:np.array(m) for n,m in held['component'].items()}
outer_parent=held_world['clavicle_l']@np.linalg.inv(held_local['clavicle_l'])
palm_index=min(range(len(landing['times'])),key=lambda i:abs(landing['times'][i]*landing['seconds']['total']-.76))
open_local={n:np.array(m) for n,m in landing['poses'][palm_index]['local'].items()}
captured_book=np.array(accepted['book_frames'][turn_index])
reference_reading=np.array(accepted['target_reading_book_camera'])
# A spine is an unoriented line. Preserve the already accepted top/bottom
# direction rather than turning the released book another 180 degrees.
# This retains the old page plane, tilt and position, with the accepted spine
# direction and the illustrated cover opening continuously away from the hand.
reading=reference_reading.copy()
reading[:3,:3]=reading[:3,:3]@R.from_euler('z',180,degrees=True).as_matrix()
closed_target=reading[:3,:3]@R.from_euler('y',-90,degrees=True).as_matrix()
spine_alignment=captured_book[:3,:3].T@closed_target

def pose(i,age):
    if i<=turn_index: return accepted['poses'][i]
    unclench=ease(events['hand_open_start'],events['hand_open_end'],age)
    drop=np.array([0.,0.,-10.])*ease(events['hand_lower_start'],events['hand_lower_end'],age)
    world={}
    for n in names:
        if n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l'):
            world[n]=held_world[n].copy(); world[n][:3,3]+=drop
        else:
            local=held_local[n].copy()
            if n.startswith(('thumb_','index_','middle_','ring_','pinky_')):
                local[:3,:3]=mix_rotation(local[:3,:3],open_local[n][:3,:3],unclench)
            world[n]=world[parent[n]]@local
    return {'local':{n:(np.linalg.inv(world[parent[n]] if parent[n] in world else outer_parent)@world[n]).tolist() for n in names},
            'component':{n:world[n].tolist() for n in names}}

times=[i/60 for i in range(round(events['duration']*60)+1)]
poses=[pose(i,t) for i,t in enumerate(times)]
frames=[]; alignments=[]; hinge=[]
for i,t in enumerate(times):
    frames.append(accepted['book_frames'][i] if i<=turn_index else captured_book.tolist())
    u=ease(events['open_start'],events['open_end'],t)
    m=np.eye(4); m[:3,:3]=mix_rotation(np.eye(3),spine_alignment,u)
    alignments.append(m.tolist()); hinge.append(u)
data={'revision':'V24 accepted V23 turn followed by release and two-sided opening',
      'fps':60,'times':times,'arm_order':names,'poses':poses,'book_frames':frames,
      'book_root_alignment':alignments,'opening_alpha':hinge,'events':events,
      'accepted_turn_source':'../PalmUpPreviewV23/candidate.json',
      'book_in_hand':accepted['book_in_hand'],'wrist_in_forearm':accepted['wrist_in_forearm'],
      'lowerarm_roll_degrees':180,'spine_tilt_adjustment_degrees':float(np.degrees(R.from_matrix(spine_alignment).magnitude())),
      'reference_reading_frame':reference_reading.tolist(),'opening_reading_frame':reading.tolist(),
      'reading_position_and_plane_preserved':True,'spine_direction':'preserve accepted V23 direction',
      'runtime_integrated':False,'contract':'verbatim V23 turn; fingers open afterward; frozen release frame; two cover hinges'}
(OUT/'candidate.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print(json.dumps({'output':str(OUT/'candidate.json'),'frames':len(times),'events':events}))
