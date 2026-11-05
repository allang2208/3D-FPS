"""Authoring coordinates for placing the new-magazine contact window."""
from pathlib import Path
__file__=str(Path(__file__).parent/'common.py')
exec(compile(Path(__file__).read_text(),'native handoff setup','exec'))
grips=json.loads((TASKOUT/'grip_anchors.json').read_text())
for family in ('base','mag10'):
    for f in (29,29.4,29.6,29.8,29.9,30,30.1,30.25,30.5,30.75,31,32,34):
        fr=GripFrame(family,f,'reload',False)
        target=fr.row['WPN_Magazine']@Matrix(grips[family]['new']['mag_to_hand'])
        shift=max(0,(target.translation-fr.S).length-(fr.A+fr.B)*.964)*1000
        print('HANDOFF',family,f,'shoulder_mm',round(shift,2),'hand_offset_mm',round((target.translation-fr.H).length*1000,2),flush=True)
