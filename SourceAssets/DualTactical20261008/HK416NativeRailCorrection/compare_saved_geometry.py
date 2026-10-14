"""Compare saved UE geometry and material regions with the reviewed assemblies."""
import bpy,json,re
from pathlib import Path
from mathutils import Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;m=json.loads((O/'manifest.json').read_text());saved=json.loads((O/'saved-readback.json').read_text())
frames=json.loads((O/'frames.json').read_text());G=Matrix(frames['asset_to_gun']);flip=Matrix(frames['runtime_opposite_blender']);report={}
def clean(s):return re.sub(r'[._]\d{3}$','',s)
def tree(vertices,faces):return BVHTree.FromPolygons(vertices,faces)
def deviation(a,af,b,bf):
    ta=tree(a,af);tb=tree(b,bf)
    return max(max(tb.find_nearest(a[i])[3] for f in af for i in f),max(ta.find_nearest(b[i])[3] for f in bf for i in f))*1000
for key,e in m.items():
    bpy.ops.wm.open_mainfile(filepath=str(O/'Editable'/(key+'.blend')))
    ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    a=[v.co.copy() for v in ob.data.vertices];af=[list(f.vertices) for f in ob.data.polygons];ag={}
    for f in ob.data.polygons:ag.setdefault(e['materials'][ob.data.materials[f.material_index].name],[]).append(list(f.vertices))
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=saved[key]['fbx'])
    b=[];bf=[];bg={};paths={clean(p.rsplit('/',1)[-1].split('.')[0]):p for p in e['materials'].values()}
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        base=len(b);t=G@(flip if e['side']==2 else Matrix.Identity(4))@ob.matrix_world
        b.extend(t@v.co for v in ob.data.vertices)
        for f in ob.data.polygons:
            face=[base+i for i in f.vertices];bf.append(face);name=clean(ob.data.materials[f.material_index].name)
            if name not in paths:raise RuntimeError('Unexpected saved region '+key+' '+name)
            bg.setdefault(paths[name],[]).append(face)
    if set(ag)!=set(bg):raise RuntimeError('Material regions missing '+key)
    regions={p:deviation(a,ag[p],b,bg[p]) for p in ag};worst=deviation(a,af,b,bf)
    report[key]={'maximum_surface_difference_mm':worst,'material_region_difference_mm':regions,'saved_triangles':len(bf),'passed':max([worst]+list(regions.values()))<.025}
    print('HK416_SAVED_SURFACE',key,round(worst,6),flush=True)
(O/'saved-geometry-report.json').write_text(json.dumps(report,indent=2))
if any(not e['passed'] for e in report.values()):raise RuntimeError('Saved geometry or material regions differ')
