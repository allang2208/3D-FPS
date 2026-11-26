import sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/RangerCrouchFit'))
import fit
inputs=fit.read(fit.R/'inputs.json');pants=fit.canonical(fit.read(P/'SourceAssets/TrouserFit20261018/Jason_LeatherPants.json'))
frames=[(k+'@'+str(i),s['bones']) for k,v in inputs['clips'].items() for i,s in enumerate(v['samples']) if (k=='Crouch.Walk.Bwd_Right' and i==2) or (k=='Crouch.Idle' and i==0)]
surface=fit.surfaces(pants,frames);d=fit.read(fit.R/'Authored/ue_field_sweater/Jason.json')
fit.write(fit.R/'residual.json',fit.gaps(d,surface))
print('RESIDUAL_SAVED',flush=True)
