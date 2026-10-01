import bpy,json,collections
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent/'HK416Reworked20260930'
a=json.loads((S/'authoring.json').read_text());inv=Matrix(a['source_to_weapon_root']).inverted()@Matrix(a['root_matrix']).inverted()
r={}
for key in ('holographic','suppressor'):
    bpy.ops.wm.open_mainfile(filepath=str(S/f'Exports/Attachments/SM_HK416_{key}_Editable.blend'))
    ob=bpy.data.objects['SM_HK416_'+key];v=[inv@ob.matrix_world@x.co for x in ob.data.vertices]
    bounds=[[min(p[i] for p in v),max(p[i] for p in v)] for i in range(3)]
    mats={}
    for i,m in enumerate(ob.data.materials):
        pts=[v[j] for f in ob.data.polygons if f.material_index==i for j in f.vertices]
        if pts:mats[m.name]={'bounds':[[min(p[k] for p in pts),max(p[k] for p in pts)] for k in range(3)]}
    z=collections.Counter(round(p.z,6) for p in v);y=collections.Counter(round(p.y,6) for p in v)
    r[key]={'bounds':bounds,'materials':mats,'z_planes':z.most_common(22),'y_planes':y.most_common(22)}
(O/'source_measurements.json').write_text(json.dumps(r,indent=2))
print(json.dumps(r,indent=2))
