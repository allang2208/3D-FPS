"""User-requested geometry cross-check of the exported V6 source, without rendering."""
import json, sys
from pathlib import Path
import bpy, bmesh
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'Config/room.json').read_text(encoding='utf-8'))
sys.path.insert(0,str(ROOT.parents[1]/'SourceAssets/DungeonRoomShells20260922/Scripts'))
from corridor_surfaces import clip

def mesh_arrays(name):
    mesh=bpy.data.objects[name].data
    vertices=np.empty(len(mesh.vertices)*3,dtype=np.float32)
    mesh.vertices.foreach_get('co',vertices)
    indices=np.empty(len(mesh.loops),dtype=np.int32)
    mesh.loops.foreach_get('vertex_index',indices)
    return vertices.reshape(-1,3)[indices.reshape(-1,3)]

tiles=mesh_arrays('SM_Ward_Tiles')
tmin,tmax=tiles.min(axis=1),tiles.max(axis=1)
windows=[]
for room in CFG['rooms']:
    x=room['window_x']; y=4.5 if room['id'].startswith('N') else -4.5
    left,right,bottom,top=x-1.776,x+1.776,1.48,2.96
    mask=(tmax[:,0]>left)&(tmin[:,0]<right)&(tmax[:,2]>bottom)&(tmin[:,2]<top)&(tmin[:,1]>y-.35)&(tmax[:,1]<y+.35)
    overlaps=0
    for triangle in tiles[mask]:
        polygon=[tuple(p) for p in triangle]
        for axis,bound,greater in ((0,left,True),(0,right,False),(2,bottom,True),(2,top,False)):
            polygon=clip(polygon,axis,bound,greater)
        if len(polygon)<3:continue
        p=np.array(polygon)
        # 3D area also catches thin ceramic side faces on a jamb.
        area=sum(np.linalg.norm(np.cross(p[i]-p[0],p[i+1]-p[0]))*.5 for i in range(1,len(p)-1))
        if area>1.e-8:overlaps+=1
    windows.append(dict(room=room['id'],ceramic_faces_in_frame_envelope=overlaps))

services=mesh_arrays('SM_Ward_HeadwallServices')
smin,smax=services.min(axis=1),services.max(axis=1)
doors=[]
for room in CFG['rooms']:
    if 'rear_door_x' not in room:continue
    x=room['rear_door_x'];y=room['y'][1]
    mask=(smax[:,0]>x-1.6)&(smin[:,0]<x+1.6)&(smax[:,1]>y-.5)&(smin[:,1]<y+.3)&(smax[:,2]>0)&(smin[:,2]<3)
    doors.append(dict(room=room['id'],equipment_faces_in_rear_door=int(mask.sum())))

topology={}
for name in ('SM_Ward_Frames','SM_Ward_WindowGaskets'):
    bm=bmesh.new();bm.from_mesh(bpy.data.objects[name].data)
    topology[name]=dict(non_manifold_edges=sum(not e.is_manifold for e in bm.edges),triangles=len(bm.faces))
    bm.free()
report=dict(scope='requested rear-door clearance and window-frame geometry only',source='Authored/WardFixV6.blend',
    windows=windows,rear_doors=doors,topology=topology,gameplay_tested=False,rendered=False)
report['passed']=all(w['ceramic_faces_in_frame_envelope']==0 for w in windows) and all(d['equipment_faces_in_rear_door']==0 for d in doors) and all(t['non_manifold_edges']==0 for t in topology.values())
(ROOT/'Receipts/geometry-v6.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('WARD_REQUESTED_GEOMETRY_REVIEW',json.dumps(report),flush=True)
if not report['passed']:raise RuntimeError('Reported geometry still intersects; see geometry-v6.json')
