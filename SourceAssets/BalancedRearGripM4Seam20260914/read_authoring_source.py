"""Read source surfaces needed to author a receiver-to-grip bridge. No render or test."""
import bpy,json,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
src=P.parent/'RearGripFinish20260913/M4/balanced/ForwardFit/Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(src))
grip=bpy.data.objects['SM_BalancedRearGrip'];report={'source':str(src),'grip':{},'receiver':[]}
def bounds(p):return {'min':p.min(axis=0).tolist(),'max':p.max(axis=0).tolist()}
for i,mat in enumerate(grip.data.materials):
    ids=set(v for f in grip.data.polygons if f.material_index==i for v in f.vertices)
    p=np.array([tuple(grip.matrix_world@grip.data.vertices[j].co) for j in ids]);rows=[]
    for z in np.arange(-.03,.055,.003):
        s=p[(p[:,2]>=z)&(p[:,2]<z+.003)]
        if len(s):rows.append({'z0':round(float(z),4),'count':len(s),**bounds(s)})
    report['grip'][mat.name]={'count':len(p),**bounds(p),'z_sections':rows}
assembly=P.parent/'PhantomRearGripSeamFit20260913/M4_Assembly_Editable.blend'
with bpy.data.libraries.load(str(assembly),link=False) as (a,b):
    b.objects=[n for n in a.objects if n.startswith('Receiver_') or n=='FactoryMountReference']
for ob in b.objects:
    bpy.context.collection.objects.link(ob)
    if ob.type!='MESH':continue
    p=np.array([tuple(ob.matrix_world@v.co) for v in ob.data.vertices])
    report['receiver'].append({'name':ob.name,**bounds(p)})
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Seam_Authoring_Source.blend'))
(P/'source_surfaces.json').write_text(json.dumps(report,indent=2))
print('M4_SEAM_SOURCE_LOADED',flush=True)
