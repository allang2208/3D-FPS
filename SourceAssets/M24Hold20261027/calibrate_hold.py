import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent
record=json.loads((O/'framing_candidate.json').read_text());frame=Matrix(record['candidate_frame'])
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_Hold_Editable.blend'),use_scripts=False)
s=bpy.context.scene;s.frame_set(0);bpy.context.view_layer.update()
convert=Matrix.Diagonal((100,-100,100,1));deps=bpy.context.evaluated_depsgraph_get()
regions={}
for name in ('M24_base','M24_bolt','M24_MainScope_Lowpoly','M24_ExtraScope_Lowpoly'):
    ob=bpy.data.objects[name];ev=ob.evaluated_get(deps);me=ev.to_mesh()
    points=[ev.matrix_world@v.co for v in me.vertices]
    if name=='M24_base':points=[v for v in points if -.05<=v.y<=.35 and v.z>=.05]
    regions[name]=[frame@convert@p for p in points];ev.to_mesh_clear()
tv=math.tan(math.radians(75/2));th=tv*16/9
needed=max(max(1-p.x,abs(p.y)/(.96*th)-p.x,abs(p.z)/(.96*tv)-p.x,0) for points in regions.values() for p in points)
offset=Vector(record['candidate_presentation_offset_cm']);offset.x+=needed
frame.translation.x+=needed
report={'definition':'ue_m24','reference':'SVD saved scoped idle; SVCh shared long-rifle camera basis',
 'source':'raw M24 donor held pose with V9 native rest and metric morphs',
 'camera':{'vertical_fov':75,'aspect':16/9,'near_clip_cm':1},
 'method':'SVD rear-sight Y/Z and common rifle axis, then minimum forward distance to keep receiver, bolt and scope controls inside 2 percent margins',
 'key_regions':{n:len(v) for n,v in regions.items()},'forward_clearance_cm':needed,
 'presentation_offset_cm':list(offset),'hip_transform':[list(v) for v in frame],
 'key_region_uv_bounds':{},'user_visual_accepted':False}
for n,points in regions.items():
    uv=[(.5+p.y/(2*(p.x+needed)*th),.5-p.z/(2*(p.x+needed)*tv)) for p in points]
    report['key_region_uv_bounds'][n]=[[min(v[i] for v in uv),max(v[i] for v in uv)] for i in range(2)]
(O/'hip-calibration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_HIP_CALIBRATED',json.dumps(report),flush=True)
