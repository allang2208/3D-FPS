"""Requested offline inspection of claw geometry, full arm motion and contact."""
import bpy, json, sys, math
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'CrownClawV15/Inspection'
OUT.mkdir(parents=True,exist_ok=True)
new='--new' in sys.argv or '--v16' in sys.argv
tag='v16' if '--v16' in sys.argv else 'new' if new else 'old'
base='ArmContinuityV16/Authoring/M09_ContinuousArms_V16.blend' if '--v16' in sys.argv else 'CrownClawV15/Authoring/M09_Rigged_ClawV15.blend' if new else 'SkinDeathV13/Authoring/M09_Rigged_V13.blend'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/base))
rig=bpy.data.objects['M09_Rig_V03'];scene=bpy.context.scene
source=ROOT/('CrownClawV15/Authoring/M09_CrownClaw_V15.blend' if new else 'CrownClawV11/Authoring/M09_CrownClaw_V11.blend')
with bpy.data.libraries.load(str(source)) as (src,dst):
    dst.actions=['A_M09_CrownClaw_V15' if new else 'A_M09_CrownClaw_V11']
rig.animation_data_create();rig.animation_data.action=dst.actions[0]
rig.animation_data.action_slot=dst.actions[0].slots[0]
rig.data.pose_position='POSE'
parts=['M09_Body_RootBand','M09_SmallArm_L','M09_SmallArm_R']
arrays={}
for name in parts:
    ob=bpy.data.objects[name];me=ob.data
    co=np.empty((len(me.vertices),3));me.vertices.foreach_get('co',co.ravel())
    edges=np.empty((len(me.edges),2),np.int32);me.edges.foreach_get('vertices',edges.ravel())
    m=np.array(ob.matrix_world);co=co@m[:3,:3].T+m[:3,3]
    arrays[name]=(edges,np.linalg.norm(co[edges[:,0]]-co[edges[:,1]],axis=1))
rows=[];skin=[]
for i in range(67):
    scene.frame_set(i+1);bpy.context.view_layer.update()
    row={'t':round(i/60,5)}
    for side in ('L','R'):
        names=[f'small_upperarm_{side}',f'small_forearm_{side}',f'small_hand_{side}',f'smallfinger_{side}_03_03']
        pts=[rig.matrix_world@rig.pose.bones[n].head for n in names]
        pts[-1]=rig.matrix_world@rig.pose.bones[names[-1]].tail
        row[side]=[list(p) for p in pts]
    rows.append(row)
    if i not in (0,12,21,27,33,48,66):continue
    for name in parts:
        ob=bpy.data.objects[name];eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=eo.to_mesh()
        co=np.empty((len(me.vertices),3));me.vertices.foreach_get('co',co.ravel())
        m=np.array(eo.matrix_world);co=co@m[:3,:3].T+m[:3,3];eo.to_mesh_clear()
        edges,base=arrays[name];extra=np.linalg.norm(co[edges[:,0]]-co[edges[:,1]],axis=1)-base
        item={'t':i/60,'part':name,'max_edge_extension_cm':float(extra.max()*100),'edges_extended_over_5cm':int((extra>.05).sum())}
        if i in (12,21,27):
            worst=[]
            for edge in np.argsort(extra)[-4:][::-1]:
                worst.append({'rest_cm':float(base[edge]*100),'extra_cm':float(extra[edge]*100),
                    'vertices':[{'rest':list(ob.matrix_world@ob.data.vertices[int(v)].co),
                        'weights':{ob.vertex_groups[g.group].name:round(g.weight,3) for g in ob.data.vertices[int(v)].groups if g.weight>0}}
                        for v in edges[edge]]})
            item['worst']=worst
        skin.append(item)
(OUT/(tag+'_geometry.json')).write_text(json.dumps({'motion':rows,'skin':skin},indent=2),encoding='utf8')
if '--geometry-only' in sys.argv:
    print('CLAW_GEOMETRY_SAVED',tag,flush=True)
    raise SystemExit
# Technical close-up only: own model, no new asset generation or game launch.
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=.4
scene.display.shading.color_type='OBJECT';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD'
if scene.world is None:scene.world=bpy.data.worlds.new('InspectionWorld')
scene.world.color=(.13,.15,.17)
scene.view_settings.view_transform='Standard'
scene.render.resolution_x=480;scene.render.resolution_y=480;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
for ob in scene.objects:
    if ob.type=='MESH':
        ob.color=(.43,.43,.43,1)
        if ob.name.endswith('SmallArm_L'):ob.color=(.8,.42,.20,1)
        if ob.name.endswith('SmallArm_R'):ob.color=(.2,.55,.72,1)
camdata=bpy.data.cameras.new('ClawInspection');cam=bpy.data.objects.new('ClawInspection',camdata)
scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=1.65
target=Vector((0,-.25,1.))
for view,pos in [('front',(0,-4,1.)),('side',(4,-.25,1.))]:
    cam.location=pos;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    for i in (0,12,21,27,33,48,66):
        scene.frame_set(i+1);scene.render.filepath=str(OUT/f'{tag}_{view}_{i:02d}.png')
        bpy.ops.render.render(write_still=True)
print('CLAW_INSPECTION_SAVED',tag,flush=True)
