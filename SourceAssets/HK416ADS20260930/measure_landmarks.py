import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'Sight_Diagnosis.blend'))
ob=bpy.data.objects['ironsight_low'];m=ob.data
verts=[v.co.copy() for v in m.vertices]
rear_faces=[list(f.vertices) for f in m.polygons if all(verts[i].y<0 for i in f.vertices)]
rear_bvh=BVHTree.FromPolygons(verts,rear_faces)
rows=[]
for iz in range(201):
    z=.0360+iz*.00001
    clear=[]
    for ix in range(-80,81):
        x=ix*.00001
        p,n,i,d=rear_bvh.ray_cast(Vector((x,-.05,z)),Vector((0,1,0)),.05)
        if p is None:clear.append(x)
    # Interior aperture only: both outer sides must remain solid.
    if clear and min(clear)>-.0008 and max(clear)<.0008 and abs(sum(clear)/len(clear))<.00002:
        rows.append({'z':z,'min_x':min(clear),'max_x':max(clear),'width':max(clear)-min(clear)})
best=max(rows,key=lambda r:r['width'])
band=[r for r in rows if r['width']>=best['width']-.00001]
rear=Vector((0,-.02455,sum(r['z'] for r in band)/len(band)))
frontpoints=[v for v in verts if v.y>.06 and abs(v.x)<.00008]
top=max(v.z for v in frontpoints);tip=[v for v in frontpoints if abs(v.z-top)<.000001]
front=Vector((0,sum(v.y for v in tip)/len(tip),top))
report={'rear_source_m':list(rear),'front_source_m':list(front),'aperture_rows':rows,'tip_vertices':[list(v) for v in tip]}
(O/'landmarks.json').write_text(json.dumps(report,indent=2));print('LANDMARKS',json.dumps({k:v for k,v in report.items() if k!='aperture_rows'}),flush=True)
scene=bpy.context.scene;cam=scene.camera;cam.data.type='PERSP'
axis=(front-rear).normalized();cam.location=rear-axis*.12/4;cam.rotation_euler=axis.to_track_quat('-Z','Y').to_euler()
auth=json.loads((O.parent/'HK416Reworked20260930/authoring.json').read_text())
for obj in scene.objects:
    if obj.type=='MESH':obj.hide_render=auth['source_parts'].get(obj.name,{}).get('role')!='body'
scene.render.filepath=str(O/'ads_calibrated_candidate.png');bpy.ops.render.render(write_still=True)
for obj in scene.objects:
    if obj.type=='MESH':obj.hide_render=obj!=ob
cam.data.type='ORTHO';cam.data.ortho_scale=.01;cam.location=(0,.04,.034);cam.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(O/'front_elevation.png');bpy.ops.render.render(write_still=True)
