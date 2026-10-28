"""Read the production blade geometry to size an undistorted rune projection."""
import bpy, json
from pathlib import Path

P=Path(__file__).resolve().parent
SOURCE=P.parent
sources=[('Factory',SOURCE/'KukriModules20261026/Kukri_Modules_Editable.blend','SM_Kukri_Blade_Factory')]
variants=json.loads((SOURCE/'KukriBladeSurfaceV220261026/surfaces.json').read_text(encoding='utf-8'))['variants']
sources.extend((v['kind'],SOURCE/'KukriBladeSurfaceV220261026/Kukri_Blade_SurfaceV2_Editable.blend',v['object']) for v in variants)
report=[]
for kind,blend,name in sources:
    with bpy.data.libraries.load(str(blend),link=False) as (available,loaded):
        loaded.objects=[name]
    obj=loaded.objects[0]
    bpy.context.scene.collection.objects.link(obj)
    pts=[obj.matrix_world @ v.co for v in obj.data.vertices]
    sections=[]
    for z in (.11,.125,.14,.155,.17):
        near=[v for v in pts if abs(v.z-z)<.002]
        if near:sections.append({'z':z,'x':[min(v.x for v in near),max(v.x for v in near)],'y':[min(v.y for v in near),max(v.y for v in near)]})
    record={'kind':kind,'blend':str(blend),'object':name,'matrix':[list(row) for row in obj.matrix_world],
            'bounds':[[min(v[i] for v in pts),max(v[i] for v in pts)] for i in range(3)],'sections':sections}
    report.append(record)
    print('BLADE_LAYOUT '+json.dumps(record),flush=True)
    bpy.data.objects.remove(obj,do_unlink=True)
(P/'blade-layout-source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
