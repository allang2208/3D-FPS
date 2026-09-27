"""Editable V14 source: translate the accepted V13 right arm/contact 4 cm right.

No grip refitting, wrist rotation, bone scaling or change to the parked left arm.
Runtime applies the same offset in StaffCastMotion::PresentationOffset, then
transports the complete V13 arm to that contact in StaffArmsMeshComponent.
"""
import json
from pathlib import Path
import numpy as np

P=Path(__file__).resolve().parent
source=P.parent/'ArmSupportV13'
data=json.loads((source/'full-pose.json').read_text())
offset=np.array([0.,4.,0.])
rest={n:np.array(m) for n,m in data['rest'].items()}
for clips in data['poses'].values():
    for clip in clips:
        contact=np.array(clip['contact']);contact[:3,3]+=offset;clip['contact']=contact.tolist()
        world={n:m.copy() for n,m in rest.items()}
        for n,m in clip['component'].items():
            world[n]=np.array(m)
            if n.endswith('_r'):world[n][:3,3]+=offset
            clip['component'][n]=world[n].tolist()
        for n in data['order']:
            clip['local'][n]=(np.linalg.inv(world[data['parent'][n]])@world[n]).tolist()
data.update(revision=14,presentation_offset_camera_cm=offset.tolist(),
            previous_source=str(source/'full-pose.json'),
            runtime='V13 complete local poses plus shared 4 cm camera-right contact translation',
            rendered=False,runtime_tested=False)
(P/'full-pose.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
script=(source/'save_editable.py').read_text().replace('V13','V14').replace("'revision':13","'revision':14")
# The executable base table stays V13. V14 is its contact-space presentation.
script=script.replace('StaffAuthoredPoseV14.h','StaffAuthoredPoseV13.h + StaffCastMotion::PresentationOffset')
(P/'save_editable.py').write_text(script,encoding='utf-8')
print('STAFF_V14_RIGHT_CARRY_SOURCE_SAVED: camera Y +4 cm')
