"""Offline pose/skin diagnosis requested for the infected-dog run."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedDogMeshy20260924')
OUT=ROOT/'RunBloodDiagnosis'
OUT.mkdir(parents=True,exist_ok=True)
candidate='--candidate' in sys.argv
prefix='godot_natural' if candidate else 'godot_fit'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/('GodotRunNaturalV3/InfectedDog_GodotRunNaturalV3.blend' if candidate else 'GodotRunFitV2/InfectedDog_GodotRunFitV2.blend')))
scene=bpy.context.scene
rig=next(o for o in scene.objects if o.type=='ARMATURE')
meshes=[o for o in scene.objects if o.type=='MESH']
report={'rig_transform':[list(r) for r in rig.matrix_world],'rest':{},'frames':[],'weight_regions':{}}
for b in rig.data.bones:
    report['rest'][b.name]={'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None}
for obj in meshes:
    counters={'vertices':len(obj.data.vertices),'cross_leg':0,'front_rear':0,'max_influences':0}
    for v in obj.data.vertices:
        groups=[(obj.vertex_groups[g.group].name,g.weight) for g in v.groups if g.weight>.001]
        counters['max_influences']=max(counters['max_influences'],len(groups))
        if any(n.endswith('.L') and w>.1 for n,w in groups) and any(n.endswith('.R') and w>.1 for n,w in groups):counters['cross_leg']+=1
        if any(n.startswith(('upperarm','forearm','carpus','front_toes')) and w>.1 for n,w in groups) and any(n.startswith(('thigh','calf','hock','hindfoot','rear_toes')) and w>.1 for n,w in groups):counters['front_rear']+=1
    report['weight_regions'][obj.name]=counters
for frame in range(scene.frame_start,scene.frame_end+1):
    scene.frame_set(frame)
    row={'frame':frame,'bones':{n:list(b.matrix.translation) for n,b in rig.pose.bones.items()}}
    report['frames'].append(row)
(OUT/('blender_'+prefix+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=700;scene.render.resolution_y=430;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
scene.display.shading.light='STUDIO';scene.display.shading.color_type='SINGLE'
scene.display.shading.single_color=(.38,.58,.27)
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.background_type='WORLD'
if scene.world is None:scene.world=bpy.data.worlds.new('DiagnosisWorld')
scene.world.color=(.14,.14,.14)
bpy.ops.object.camera_add(location=(3,-.06,1.0));cam=bpy.context.object
cam.rotation_euler=(Vector((0,0,.52))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=1.9;scene.camera=cam
for frame in ((1,9,18,26) if candidate else (1,7,14,20)):
    scene.frame_set(frame);scene.render.filepath=str(OUT/f'{prefix}_{frame:02}.png')
    bpy.ops.render.render(write_still=True)
print('RUN_DIAGNOSIS_WRITTEN',str(OUT),flush=True)
