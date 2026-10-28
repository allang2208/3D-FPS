import bpy,json
from pathlib import Path
P=Path(__file__).parent
S=P.parent.parent
report={}
for family,path,names in [('hunter',S/'BowSingleLensOptics20260927/Bow_SingleLensOptics.blend',['SM_Bow_Clearfield2x','SM_Bow_Farwatch4x']),('woodsteel',P.parent/'WoodSteelLongbow_Editable.blend',['SM_WoodSteelLongbow_Optic2x','SM_WoodSteelLongbow_Optic4x'])]:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    for name in names:
        obj=bpy.data.objects[name];me=obj.data;rows=[]
        for mi,mat in enumerate(me.materials):
            if 'Glass' not in mat.name:continue
            fs=[f for f in me.polygons if f.material_index==mi]
            loops=[i for f in fs for i in f.loop_indices]
            vertices=[me.vertices[me.loops[i].vertex_index].co for i in loops]
            layers=[]
            for uv in me.uv_layers:
                coords=[uv.data[i].uv for i in loops]
                layers.append({'name':uv.name,'min':[min(v[k] for v in coords) for k in (0,1)],'max':[max(v[k] for v in coords) for k in (0,1)],'sample':[[list(vertices[i]),list(coords[i])] for i in range(min(8,len(coords)))]})
            rows.append({'material':mat.name,'faces':len(fs),'normals':[list(f.normal) for f in fs[:2]],'bounds':[[min(v[k] for v in vertices),max(v[k] for v in vertices)] for k in range(3)],'layers':layers})
        report[family+'/'+name]=rows
(P/'optic-uv-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('OPTIC_UV_DIAGNOSIS_SAVED')
