"""Read authored fist geometry for surface fitting and contact placement."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/FistSlamV14')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/M66_fist_slam_v14.blend'))
rig=bpy.data.objects['M66_Rig'];scene=bpy.context.scene;scene.frame_set(96);bpy.context.view_layer.update()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};origin=rest['Bone_037'].translation
f=(rest['Bone_073'].translation-origin).normalized();r=rest['Bone_065'].translation-rest['Bone_061'].translation;r=(r-f*r.dot(f)).normalized();d=f.cross(r)
to_source=rest['Bone_037']@rig.pose.bones['Bone_037'].matrix.inverted()
rows={}
for digit,root in {'thumb':57,'index':65,'middle':73,'ring':69,'pinky':61}.items():
    points=[to_source@rig.pose.bones[f'Bone_{i:03d}'].head-origin for i in range(root,root-4,-1)]
    points.append(to_source@rig.pose.bones[f'Bone_{root-3:03d}'].tail-origin)
    rows[digit]=[[round(p.dot(v),3) for v in (f,r,d)] for p in points]
data=json.loads((ROOT/'Records/fist_contact_definition.json').read_text());centres=np.array(data['reference_points_source_m'])
print('FIST_PALM_COORDS '+json.dumps(rows))
print('COVER_BOUNDS '+json.dumps({'min':centres.min(0).tolist(),'max':centres.max(0).tolist()}))
feet=(rest['Bone_010'].translation+rest['Bone_015'].translation)*.5;reach=[]
for frame in range(89,104):
    scene.frame_set(frame);bpy.context.view_layer.update();transform=rig.pose.bones['Bone_037'].matrix@rest['Bone_037'].inverted()
    for point in data['reference_points_source_m']:
        p=transform@Vector(point);reach.append([(-p.y+feet.y)*100,(-p.x+feet.x)*100,p.z*100])
points=np.array(reach);radius=data['radius_cm'];capsule=np.column_stack((np.full(len(points),270),np.zeros(len(points)),np.clip(points[:,2],42,148)))
print('CONTACT_PLACEMENT '+json.dumps({'min_cm':points.min(0).tolist(),'max_cm':points.max(0).tolist(),'stance270_nearest_axis_cm':float(np.linalg.norm(points-capsule,axis=1).min()),'fist_radius_cm':radius}))
