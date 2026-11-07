from pathlib import Path
import bpy,numpy as np,json
O=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
report={}
for f in (O/'Inputs').glob('*.fbx'):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(f))
    rows=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        p=np.array([ob.matrix_world@v.co for v in ob.data.vertices])
        rows.append({'object':ob.name,'bounds':[p.min(0).tolist(),p.max(0).tolist()],
          'slots':[m.name for m in ob.data.materials],'transform':[list(r) for r in ob.matrix_world]})
    report[f.stem]=rows
with bpy.data.libraries.load(str(O.parent/'M24CarbonSpineGame20261104/M24_CarbonSpine_Fitted.blend')) as (avail,load):
    load.objects=[s for s in avail.objects if s.startswith('Donor receiver | ')]
for ob in load.objects:
    p=np.array([ob.matrix_world@v.co for v in ob.data.vertices]);report[ob.name]={'bounds':[p.min(0).tolist(),p.max(0).tolist()]}
(O/'geometry_inventory.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
