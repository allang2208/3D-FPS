"""Create the isolated R3 source from R2's unchanged donor and native materials."""
import json
from pathlib import Path
from arm_refinement import ArmRefinedShape
from leg_proportions import LegProportions
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117')
OLD=BASE/'R2_LongLegs';OUT=BASE/'R3_ArmsRefined'
OUT.mkdir(exist_ok=True);(OUT/'ArmReview').mkdir(exist_ok=True);(OUT/'AnatomyReview').mkdir(exist_ok=True)
for name in ['body_source.json','head_source.json','material_inputs.json','source_receipt.json','neck_seam.json']:
    (OUT/name).write_bytes((OLD/name).read_bytes())
body=json.loads((OUT/'body_source.json').read_text())
shape=ArmRefinedShape(body['bones'],seam_segments=json.loads((OUT/'neck_seam.json').read_text()))
legs=LegProportions(body['bones'])
positions=[legs.deform(p,shape.deform(p,w)) for p,w in zip(body['positions'],body['weights'])]
(OUT/'strong_positions.json').write_text(json.dumps(positions,separators=(',',':')))
body['positions']=positions;body['head_z_cm']=4.5
body['bones']=json.loads((OLD/'AnatomyReview/derived_saved_mesh.json').read_text())['bones']
(OUT/'ArmReview/authored_candidate.json').write_text(json.dumps(body,separators=(',',':')))
(OUT/'ArmReview/before_R2.json').write_bytes((OLD/'AnatomyReview/derived_saved_mesh.json').read_bytes())
print('JASON_R3_ARM_REVISION_PREPARED')
