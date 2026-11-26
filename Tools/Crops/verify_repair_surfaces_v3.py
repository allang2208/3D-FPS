"""Compare topology, UVs and positions of derived LODs to untouched V3 sources."""
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils.kdtree import KDTree

ROOT=Path(__file__).resolve().parents[2]/'SourceAssets/CropsV3_20261022'
audit=json.loads((ROOT/'Receipts/fbx-engine-audit.json').read_text())


def surfaces(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH');m=obj.data
    m.calc_loop_triangles();uv=m.uv_layers.active.data;result={}
    for tri in m.loop_triangles:
        corners=[]
        for vertex,loop in zip(tri.vertices,tri.loops):
            position=obj.matrix_world@m.vertices[vertex].co
            corners.append([*position,*uv[loop].uv])
        result.setdefault(m.materials[tri.material_index].name,[]).append(corners)
    return result


report=[]
for row in audit['meshes']:
    if row['read_path'].startswith('Source'):continue
    old=surfaces(ROOT/'Source/Models'/row['file'])
    new=surfaces(ROOT/row['read_path'])
    assert set(old)==set(new),row['file']
    delta=0.
    for material in old:
        a=np.array(old[material]);b=np.array(new[material])
        assert a.shape==b.shape,(row['file'],material)
        tree=KDTree(len(b));centers=b[:,:,:3].mean(axis=1)
        for index,center in enumerate(centers):tree.insert(center,index)
        tree.balance();used=set()
        for triangle in a:
            center=triangle[:,:3].mean(axis=0);found=False
            for _,index,_ in tree.find_range(center,1e-6):
                if index in used:continue
                for shift in range(3):
                    current=float(np.max(np.abs(triangle-np.roll(b[index],shift,axis=0))))
                    if current<1e-6:
                        delta=max(delta,current);used.add(index);found=True;break
                if found:break
            assert found,(row['file'],material,triangle.tolist())
    report.append({'file':row['file'],'read_path':row['read_path'],'positions_uv_and_triangle_topology_preserved':True,
                   'max_numeric_delta':delta})
(ROOT/'Receipts/repair-surfaces-verification.json').write_text(json.dumps(report,indent=2))
print('CROPS_REPAIR_SURFACES_PRESERVED',len(report))
