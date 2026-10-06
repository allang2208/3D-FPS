"""Read shared model seating surfaces in their authoring units; no rendering."""
import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent
sources=json.loads((O.parent/'WeaponAttachmentFinish20260913/authoring.json').read_text())
records={}
for key in ('holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','eoth_holographic'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    f=O/'Sources'/(key+'.fbx')
    if not f.exists():
        f=O.parent/'EOTHReticle20261001/Exports/SM_Common_eoth_holographic.fbx' if key=='eoth_holographic' else Path(sources['M4/'+key]['file'])
    bpy.ops.import_scene.fbx(filepath=str(f))
    points=np.array([o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH' for v in o.data.vertices])
    # These models are authored in metres with a common z=0 rail crown.
    low=points[points[:,2]<points[:,2].min()+.0004]
    seats=[]
    for o in bpy.data.objects:
        if o.type!='MESH':continue
        for poly in o.data.polygons:
            ps=np.array([o.matrix_world@o.data.vertices[i].co for i in poly.vertices])
            if np.ptp(ps[:,2])<.00002 and ps[:,2].mean()<.004:
                seats.append(dict(z=float(ps[:,2].mean()),min=ps.min(0).tolist(),max=ps.max(0).tolist(),area=poly.area))
    records[key]=dict(source_fbx=str(f),bounds_m=[points.min(0).tolist(),points.max(0).tolist()],foot_m=[low.min(0).tolist(),low.max(0).tolist()],seat_faces=seats)
    print(key,'bounds',points.min(0).round(5).tolist(),points.max(0).round(5).tolist(),'foot',low.min(0).round(5).tolist(),low.max(0).round(5).tolist(),flush=True)
(O/'interfaces.json').write_text(json.dumps(records,indent=2))
