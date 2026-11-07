"""Save native V9 rig, corrective keys and the actual two-stock geometry."""
from pathlib import Path
exec(compile((Path(__file__).parent/'common.py').read_text(),'pose helpers','exec'))
patch=json.load(gzip.open(O/'quick_melee_patch.json.gz','rt'))
FPS=240;final={f:[compose(c,i/FPS)[0] for i in range(217)] for f,c in patch.items()}
report={'duration':.9,'contact':.25,'fps':FPS,'source':'Current saved M24 profiles, fixed shared-neck grasp, individual finger return','profiles':list(patch),'native_build_required':False}
code=(S/'M24QuickMeleeGrip20261104/author.py').read_text().split('# Native editable rig plus the current V9 skin and runtime-equivalent JC tracks.')[1]
code=code.replace('M24_QuickMelee_CurrentGrip_Editable.blend','M24_TwoStock_QuickMelee_Editable.blend')
code=code.replace('s.render.fps = 200','s.render.fps = 240').replace('(len(rows) - 1) / 200','(len(rows) - 1) / 240').replace('s.frame_end=180','s.frame_end=216')
exec(compile(code,'editable native export','exec'))
