import bpy,json,struct,shutil
from pathlib import Path
from mathutils import Vector
import numpy as np
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007')
for sub in ['Source','Authoring','Delivery','Textures','Logs']: (ROOT/sub).mkdir(parents=True,exist_ok=True)
src=Path('C:/Users/allan/Downloads/Meshy_AI_Faceless_Mannequin_in_1007155702_texture.glb')
shutil.copy2(src,ROOT/'Source'/src.name)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'Source'/src.name))
body=next(o for o in bpy.context.scene.objects if o.type=='MESH');body.name='Receptionist_SourceBody'
bpy.context.view_layer.objects.active=body;body.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
pts=np.array([body.matrix_world@v.co for v in body.data.vertices])
lo,hi=pts.min(0),pts.max(0)
s=1.82/(hi[2]-lo[2]);pts=(pts-np.array([(lo[0]+hi[0])/2,0,lo[2]]))*s
body.matrix_world.identity()
for v,p in zip(body.data.vertices,pts):v.co=p
for im in bpy.data.images:
 if im.type=='IMAGE' and im.size[0]>0:
  im.filepath_raw=str(ROOT/'Textures'/('Source_'+im.name+'.png'));im.file_format='PNG';im.save()
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath='D:/FPS3D/FPSGAME/Saved/NurseZombie/ANMS_ZombieFemaleWalk01Forward.fbx',use_anim=False)
donors=[o for o in set(bpy.data.objects)-before if o.type=='MESH']
rig=next(o for o in set(bpy.data.objects)-before if o.type=='ARMATURE')
rig.animation_data_clear()
for p in rig.pose.bones:p.matrix_basis.identity()
bpy.context.view_layer.update()
report={'source_vertices':len(body.data.vertices),'source_triangles':sum(len(p.vertices)-2 for p in body.data.polygons),'source_bounds':[pts.min(0).tolist(),pts.max(0).tolist()],'source_materials':[m.name for m in body.data.materials],'rig_matrix':[list(x) for x in rig.matrix_world],'bones':{b.name:{'head':list(rig.matrix_world@b.head_local),'tail':list(rig.matrix_world@b.tail_local),'parent':b.parent.name if b.parent else None} for b in rig.data.bones},'donors':[{'name':o.name,'vertices':len(o.data.vertices),'materials':[m.name for m in o.data.materials]} for o in donors],'sections':[]}
for z in np.arange(.1,1.81,.1):
 p=pts[np.abs(pts[:,2]-z)<.015]
 report['sections'].append({'z':float(z),'min':p.min(0).tolist(),'max':p.max(0).tolist()})
(ROOT/'Authoring'/'input_structure.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring'/'Inputs.blend'))
print(json.dumps({'source':report['source_bounds'],'donors':report['donors'],'rig_matrix':report['rig_matrix'],'bones':{n:x for n,x in report['bones'].items() if n in ['root','pelvis','spine_01','spine_02','spine_03','neck_01','head','clavicle_l','upperarm_l','lowerarm_l','hand_l','thigh_l','calf_l','foot_l','ball_l','index_01_l','middle_01_l','ring_01_l','pinky_01_l','thumb_01_l']},'sections':report['sections']},indent=2))
