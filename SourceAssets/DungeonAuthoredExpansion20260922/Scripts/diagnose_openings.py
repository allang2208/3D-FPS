import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/AuthoredSpace_Connections.blend'))
report=[]
for name,begin,end in [
('SM_Sample_ServiceDoor_Open',(24,13,2),(24,15,2)),
('SM_Sample_EndLanding_Open',(24,13,2),(24,15,2)),
('SM_Sample_EndLanding_Tiles_Open',(24,13,2),(24,15,2)),
('SM_Sample_EntryEnd_Open',(-1,2,1),(1,2,1)),
('SM_Sample_EntryEnd_Tiles_Open',(-1,2,1),(1,2,1))]:
    o=bpy.data.objects[name]
    start=Vector(begin);direction=Vector(end)-start
    hit=o.ray_cast(start,direction.normalized(),distance=direction.length)
    vs=[o.matrix_world@v.co for v in o.data.vertices]
    report.append(dict(name=name,verts=len(vs),faces=len(o.data.polygons),bounds=[[min(v[i] for v in vs) for i in range(3)],[max(v[i] for v in vs) for i in range(3)]],blocked=hit[0],hit=list(hit[1])))
(ROOT/'Receipts/opening-geometry-current.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('OPENING_GEOMETRY',json.dumps(report))
