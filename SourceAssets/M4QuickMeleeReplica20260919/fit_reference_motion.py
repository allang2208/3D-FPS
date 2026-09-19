"""Construct editable M4 poses from explicit stock screen anchors.

This is authoring, not a claim that an offline camera has passed game review.
The input annotations separate observed pixels from estimated 3-D quantities.
"""
import json,math
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation,Slerp
P=Path(__file__).parent
plan=json.loads((P/'reference_motion.json').read_text())
inputs=json.loads((P/'authoring_input.json').read_text())
idle=np.array(inputs['pose']['WPN_root']);camera=np.array(plan['camera']['position_author_m'])
k=math.tan(math.radians(plan['camera']['vertical_fov_degrees']/2));aspect=plan['camera']['aspect']
point=np.array(plan['stock_point_gun_local_m']);knots=plan['knots'];matrices=[]
for row in knots:
    if 'stock_uv' not in row:matrices.append(idle.copy());continue
    yaw,pitch=np.radians([row['yaw'],row['pitch']])
    forward=np.array([-math.sin(yaw)*math.cos(pitch),math.cos(yaw)*math.cos(pitch),math.sin(pitch)])
    back=-forward;left=np.cross(back,[0,0,1]);left/=np.linalg.norm(left);up=np.cross(left,back)
    rot=np.column_stack([left,back,up])@Rotation.from_euler('y',row['roll'],degrees=True).as_matrix()
    u,v=row['stock_uv'];depth=row['depth_m']
    stock=camera+np.array([(u-.5)*2*k*aspect*depth,depth,(.5-v)*2*k*depth])
    m=np.eye(4);m[:3,:3]=rot;m[:3,3]=stock-rot@point;matrices.append(m)
for i,row in enumerate(knots):
    if 'idle_blend_to' not in row:continue
    target=matrices[row['idle_blend_to']];w=row['weight'];m=idle.copy()
    m[:3,3]=(1-w)*idle[:3,3]+w*target[:3,3]
    m[:3,:3]=Slerp([0,1],Rotation.from_matrix([idle[:3,:3],target[:3,:3]]))([w]).as_matrix()[0]
    matrices[i]=m
times=[x['t'] for x in knots]
positions=PchipInterpolator(times,[m[:3,3] for m in matrices])
rotations=Slerp(times,Rotation.from_matrix([m[:3,:3] for m in matrices]))
frames=[]
for f in range(round(plan['duration_seconds']*120)+1):
    t=f/120;m=np.eye(4);m[:3,3]=positions(t);m[:3,:3]=rotations([t]).as_matrix()[0]
    delta=m@np.linalg.inv(idle)
    frames.append({'frame':f,'time':t,'weapon_delta':delta.tolist(),'root':m.tolist()})
(P/'motion_frames.json').write_text(json.dumps({'fps':120,'duration':plan['duration_seconds'],
    'contact':plan['contact_seconds'],'knots':[m.tolist() for m in matrices],'frames':frames},indent=2))
print('REFERENCE_MOTION_CONSTRUCTED',len(frames),'samples; 3-D depth remains reconstructed')
