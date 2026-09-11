import json,shutil
from pathlib import Path
O=Path(__file__).parent;D=O/'m4/canted';fit=json.loads((O/'canted_refit.json').read_text())
(D/'fit_final.json').write_text(json.dumps(fit,indent=2))
(D/'profile.json').write_text(json.dumps({'animation_prefix':'A_M4_Canted_','fitted_mesh':'Fitted.blend','mesh_prefix':'CG_'},indent=2))
shutil.copy2(O/'Canted_Refit.blend',D/'Fitted.blend')
shutil.copy2(O/'release_final.json',D/'release_profile.json')
