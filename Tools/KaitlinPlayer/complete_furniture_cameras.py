"""Author eye tracks from each selected female clip and the native face bind frame."""
import json,math
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME'); W=P/'SourceAssets/KaitlinCompletion20261024/Furniture'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
catalog=read(W/'source_catalog.json');saved=read(W/'saved_assets.json')
if set(catalog['stale_roles'])-set(saved):raise RuntimeError('Finish retarget saves first.')
clips={k:v for k,v in catalog['female_before'].items() if k.startswith('Rest.')}
clips.update({k:v['asset'] for k,v in saved.items()})
native=P/'SourceAssets/KaitlinPlayer20261023/NativeGeometry'
body=read(native/'MHC_Kaitlin_Body.json');face=read(native/'SKM_MHC_Kaitlin_FaceMesh.json')
bones=body['bones'];head=next(b for b in bones if b['name']=='head')
eyes=[b['position'] for b in face['bones'] if b['name'] in ('FACIAL_L_Eye','FACIAL_R_Eye')]
if len(eyes)!=2:raise RuntimeError('Native eye landmarks unavailable')
# Native bone axes are rotation rows; dotting with each row yields head-local offsets.
offset=[sum(((eyes[0][j]+eyes[1][j])*.5-head['position'][j])*head['axes'][i][j] for j in range(3)) for i in range(3)]
chain=[];index=head['index']
while index>=0:chain.append(bones[index]['name']);index=bones[index]['parent']
chain.reverse(); tracks={}
for role,path in clips.items():
    clip=u.load_asset(path)
    if not clip:raise RuntimeError('Missing selected clip: '+role)
    duration=clip.get_play_length();steps=max(1,math.ceil(duration*30));points=[]
    for i in range(steps+1):
        poses=u.AnimationLibrary.get_bone_poses_for_time(clip,chain,duration*i/steps,False)
        world=u.Transform()
        for pose in poses:world=u.MathLibrary.compose_transforms(pose,world)
        eye=world.transform_location(u.Vector(*offset));points.append([round(eye.x,5),round(eye.y,5),round(eye.z,5)])
    tracks[role]={'duration':duration,'eyes':points,'animation':path}
(W/'camera_tracks.json').write_text(json.dumps(tracks,separators=(',',':')),encoding='utf-8')
(P/'SourceAssets/KaitlinPlayer20261023/complete_furniture_cameras_status.json').write_text(json.dumps({'remaining':0,'complete':True}))
print('FEMALE_FURNITURE_CAMERAS_SAVED',len(tracks),flush=True)
