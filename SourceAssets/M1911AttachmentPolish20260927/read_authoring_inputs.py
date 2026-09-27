"""Read the editable inputs and mechanical coordinates needed for this revision."""
import bpy,json,bmesh,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent;record={}
auth=json.loads((S/'M1911ExtendedMagazine20260927/authoring.json').read_text());root=Matrix(auth['root_matrix'])
for source,name in [('M1911ExtendedMagazine20260927/M1911_ExtendedMagazine_Editable.blend','SM_M1911_ext_mag'),
                    ('M1911CompactFit20260913/M1911_CompactOptics_Editable.blend','M1911_holographic')]:
    bpy.ops.wm.open_mainfile(filepath=str(S/source));ob=bpy.data.objects[name];xf=root.inverted() if name=='SM_M1911_ext_mag' else Matrix.Identity(4)
    groups={}
    for index,mat in enumerate(ob.data.materials):
        pts=[xf@ob.data.vertices[i].co for p in ob.data.polygons if p.material_index==index for i in p.vertices]
        if pts:groups[mat.name]={'bounds':[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]],
            'faces':sum(p.material_index==index for p in ob.data.polygons)}
    record[name]={'source':source,'groups':groups,'matrix':[list(row) for row in ob.matrix_world]}
    if name=='SM_M1911_ext_mag':
        bm=bmesh.new();bm.from_mesh(ob.data)
        for v in bm.verts:v.co=xf@v.co
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bm.normal_update()
        edges=[e for e in bm.edges if e.is_manifold and max(v.co.z for v in e.verts)<-.0839 and e.calc_face_angle(0)>.35]
        record[name]['lower_hard_edges']=[{'a':list(e.verts[0].co),'b':list(e.verts[1].co),'angle':e.calc_face_angle(0)} for e in edges]
        bm.free()
(O/'authoring_inputs.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('AUTHORING_INPUTS_READY',flush=True)
