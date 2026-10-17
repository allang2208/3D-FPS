import sys,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;UC=O.parent/'M870UrbanAnimations20261015';sys.path.insert(0,str(UC))
from read_inputs import smd
d=smd(UC/'Original/870/anims/reloadinsert.smd');r=smd(UC/'Original/870/shotgun.smd')['rows'][0]
pre='ValveBiped.Bip01_R_'
for f in (0,6,12,20,26):
 p=d['rows'][f];fore=p[pre+'Hand'].translation-p[pre+'Forearm'].translation;palm=p[pre+'Finger2'].translation-p[pre+'Hand'].translation;upper=p[pre+'Forearm'].translation-p[pre+'UpperArm'].translation
 print('UC',f,'wrist',math.degrees(fore.angle(palm)),'elbow',math.degrees(fore.angle(upper)),flush=True)
print('NAMES',[n for n in r if n.startswith(pre)],flush=True)
