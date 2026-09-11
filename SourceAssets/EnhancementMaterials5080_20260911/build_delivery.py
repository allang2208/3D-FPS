import bpy,json,shutil
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent;D=P/'Delivery';D.mkdir(exist_ok=True)
audit=[]
for asset,height in [('enhancement_stone',.14),('magic_dust',.16)]:
    bpy.ops.wm.read_factory_settings(use_empty=True);source=P/(asset+'_lod0_candidate.glb');bpy.ops.import_scene.gltf(filepath=str(source))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)));origin=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));scale=height/(hi.z-lo.z)
    for o in objects:
        matrix=o.matrix_world.copy()
        for v in o.data.vertices:v.co=(matrix@v.co-origin)*scale
        o.matrix_world=Matrix.Identity(4)
    points=[v.co for o in objects for v in o.data.vertices]
    assert abs(min(v.z for v in points))<1e-6 and abs(max(v.z for v in points)-height)<1e-6
    for o in objects:o.data.calc_loop_triangles()
    audit.append({'item_id':asset,'source':source.name,'height_m':height,'origin':'bottom center','triangles':sum(len(o.data.loop_triangles) for o in objects),'materials':[m.name for o in objects for m in o.data.materials],'images':[{'name':i.name,'size':list(i.size)} for i in bpy.data.images if i.type=='IMAGE']})
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(D/(asset+'_editable.blend')))
    bpy.ops.export_scene.gltf(filepath=str(D/(asset+'.glb')),export_format='GLB')
    shutil.copy2(P/(asset+'_three_views.png'),D/(asset+'_three_views.png'))
(D/'asset_audit.json').write_text(json.dumps(audit,indent=2))
print(json.dumps(audit),flush=True)
