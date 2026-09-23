"""Derive support contacts from the existing separated leg soles, no render."""
import bpy, json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Bipod26/PKM_Bipod_Editable.blend'),use_scripts=False)
out={}
for name in ['LegA','LegB']:
    obs=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('PKM26_'+name+'_')]
    pts=[v.co for ob in obs for v in ob.data.vertices]
    bottom=min(v.z for v in pts)
    sole=[v for v in pts if v.z<=bottom+.00015]
    contact=Vector([(min(v[k] for v in sole)+max(v[k] for v in sole))*.5 for k in range(3)])
    out[name]=[contact.x*100,-contact.y*100,contact.z*100]
(O/'contacts.json').write_text(json.dumps(out,indent=2))
lines=['// Measured by BipodDeploy28/read_contacts.py from the Bipod26 soles.', '#pragma once', '#include "CoreMinimal.h"', 'namespace PKMBipodContacts', '{']
for key,v in out.items():lines.append('inline const FVector '+key+'('+','.join(f'{x:.9f}' for x in v)+');')
lines.append('}\n')
(R.parents[1]/'Source/FPSGAME/Weapons/PKMBipodContacts.h').write_text('\n'.join(lines))
print('PKM28_CONTACTS',json.dumps(out),flush=True)
