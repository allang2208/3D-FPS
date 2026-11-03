import bpy,json,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(P.parent/'SeatInlaidC6/ThorSeats_InlaidC6.blend'),link=False) as(a,b):
    b.objects=['SM_ThunderGodHammer_head_mount_'+k for k in ('reinforced_block','ribbed_light','laminated_damper')]
rows=[]
for ob in b.objects:
    p=np.array([v.co[:] for v in ob.data.vertices])
    sections=[]
    for x in (.033,.043,.053,.059):
        for z in (.950,.959,.968,.975):
            a=p[(abs(p[:,0]-(x-.0004452141))<.002)&(abs(p[:,2]-z)<.002)]
            if len(a):sections.append(dict(x=x,z=z,y_min=float(a[:,1].min()),y_max=float(a[:,1].max())))
    rows.append(dict(name=ob.name,matrix=[list(r) for r in ob.matrix_world],materials=[m.name for m in ob.data.materials],sections=sections))
(P/'source_sections.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('SOURCE_SECTIONS_WRITTEN',flush=True)
