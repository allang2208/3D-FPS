"""Read the actual author meshes to author shared pommel mounting profiles."""
import bpy, json, math
from pathlib import Path
P=Path(__file__).parent
SRC=P.parent
bpy.ops.wm.open_mainfile(filepath=str(SRC/'RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend'))
with bpy.data.libraries.load(str(SRC/'FrostSwordModules20260915/FrostSword_Modular_Editable.blend'),link=False) as (source,target):
    target.objects=['SM_FrostSword_Pommel_factory']
frost=target.objects[0]
profiles={}
for name,obj in [('rune',bpy.data.objects['SM_RunePommel_Meteor']),('frost',frost)]:
    points={tuple(round(c,8) for c in v.co) for v in obj.data.vertices if abs(v.co.z)<.000001}
    points=sorted(points,key=lambda p:math.atan2(p[1],p[0]))
    profiles[name]={'object':obj.name,'rim_m':points,'range_m':[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)]}
    print('MOUNT_SOURCE', name, len(points), profiles[name]['range_m'])
(P/'mount_sources.json').write_text(json.dumps(profiles,indent=2),encoding='utf-8')
