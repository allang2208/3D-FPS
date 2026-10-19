import json, math, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

P=Path(__file__).resolve().parent;V2=P.parent/'ChixiaoGripV2';V1=P.parent/'ChixiaoDoubleHeavyV1'
env={'__file__':str(V1/'author_motion.py')}
exec(compile((V1/'author_motion.py').read_text('utf-8').split('receipt=')[0].replace("data=json.loads((P/'motion_sources.json').read_text('utf-8'))",'data={}'),'helpers','exec'),env)
A=env['A'];pose_at=env['pose_at'];rigid=env['grip_frame']
changed={'clavicle_r','upperarm_r','upperarm_twist_01_r','upperarm_twist_02_r','lowerarm_r','lowerarm_twist_01_r','lowerarm_twist_02_r'}
report={}
vf=math.tan(math.radians(75)/2);hf=vf*16/9
for variant in ('Standard','LongGrip'):
    old=json.loads((V2/variant/'editable_keys.json').read_text('utf-8'))
    new=json.loads((P/variant/'editable_keys.json').read_text('utf-8'))
    poses={};metrics={'preserved_pose_max_cm':0.,'preserved_pose_max_degrees':0.,'bone_length_max_error_cm':0.}
    for version,clip in [('old',old),('new',new)]:poses[version]=[A.pose_from_rows(s['bones']) for s in clip['samples']]
    for a,b in zip(poses['old'],poses['new']):
        for name in a.keys()-changed:
            metrics['preserved_pose_max_cm']=max(metrics['preserved_pose_max_cm'],(a[name].translation-b[name].translation).length*100)
            metrics['preserved_pose_max_degrees']=max(metrics['preserved_pose_max_degrees'],math.degrees(2*math.acos(min(1.,abs(a[name].to_quaternion().normalized().dot(b[name].to_quaternion().normalized()))))))
        for start,end in [('upperarm_r','lowerarm_r'),('lowerarm_r','hand_r')]:
            metrics['bone_length_max_error_cm']=max(metrics['bone_length_max_error_cm'],abs((a[start].translation-a[end].translation).length-(b[start].translation-b[end].translation).length)*100)
    metrics['first_cut_keys_identical']=all(a==b for a,b in zip(old['samples'],new['samples']) if a['seconds']<=.12)
    for version in poses:
        for bone in ('upperarm_r','lowerarm_r'):
            seq=poses[version]
            metrics[version+'_'+bone+'_max_60hz_step_cm']=max((seq[i][bone].translation-seq[i-4][bone].translation).length*100 for i in range(33,len(seq),4))
    for version in poses:
        for bone in ('upperarm_r','lowerarm_r'):
            seq=poses[version];i=max(range(80,len(seq),4),key=lambda i:(seq[i][bone].translation-seq[i-4][bone].translation).length)
            metrics[version+'_'+bone+'_recovery_peak']={'t':i/240,'cm':(seq[i][bone].translation-seq[i-4][bone].translation).length*100}
    bpy.ops.wm.open_mainfile(filepath=str(P/variant/'Chixiao_ShoulderV3_Editable.blend'))
    scene=bpy.context.scene;surfaces=[]
    for obj in scene.objects:
        if obj.type!='MESH' or not obj.vertex_groups:continue
        counts={}
        for face in obj.data.polygons:
            for edge in face.edge_keys:counts[edge]=counts.get(edge,0)+1
        groups={g.index:g.name for g in obj.vertex_groups}
        ids=set(i for edge,count in counts.items() if count==1 for i in edge)
        ids=[i for i in ids if sum(g.weight for g in obj.data.vertices[i].groups if groups[g.group] in changed)>.9]
        surfaces.append((obj,ids))
    exposed=[];clearances=[]
    for frame in range(29,241):
        scene.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get();points=[]
        for obj,ids in surfaces:
            evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh()
            points.extend(evaluated.matrix_world@mesh.vertices[i].co for i in ids);evaluated.to_mesh_clear()
        visible=[p for p in points if p.y>.01 and abs(p.x)<hf*p.y and abs(p.z)<vf*p.y]
        if visible:exposed.append({'t':frame/240,'vertices':len(visible)})
        if .20<=frame/240<=.75:clearances.append(-max(p.z+vf*p.y for p in points)/math.sqrt(1+vf*vf)*100)
    metrics['visible_root_frames']=exposed;metrics['min_skinned_root_clearance_cm']=min(clearances)
    report[variant]=metrics
    (P/'shoulder-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('SHOULDER_METRICS',variant,json.dumps(metrics),flush=True)
    if '--metrics-only' in sys.argv:continue
    for ob in scene.objects:
        if ob.type=='MESH':ob.color=(.54,.31,.20,1);ob.hide_render=not bool(ob.vertex_groups)
    with bpy.data.libraries.load(str(P.parent/'ChixiaoBladeV1/Chixiao_Blade_Editable.blend'),link=False) as (available,loaded):
        loaded.objects=[n for n in ('SM_Zhanmadao_Blade_chixiao_V1_LOD0','SM_Zhanmadao_Guard_V1','SM_Zhanmadao_Grip_V1','SM_Zhanmadao_Pommel_V1') if n in available.objects]
    parts=[]
    for ob in loaded.objects:
        scene.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False);ob.parent=None
        parts.append((ob,ob.matrix_world.copy()));ob.color=(.12,.13,.15,1)
    bpy.ops.object.camera_add(location=(0,0,0));cam=bpy.context.object
    cam.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler()
    cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24;cam.data.lens=24/(2*vf);cam.data.clip_start=.01;scene.camera=cam
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
    scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
    scene.display.shading.background_type='WORLD'
    if not scene.world:scene.world=bpy.data.worlds.new('ShoulderReviewWorld')
    scene.world.color=(.07,.085,.10)
    scene.render.resolution_x=1152;scene.render.resolution_y=648;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    out=P/'PoseReview';out.mkdir(exist_ok=True)
    for t in ((.30,.50,.62) if variant=='Standard' else (.30,.62)):
        scene.frame_set(round(t*240));w=pose_at(new,t);frame=rigid(w['WPN_root'])@Matrix.Translation((0,0,.045))
        for ob,local in parts:ob.matrix_world=frame@local
        scene.render.filepath=str(out/(variant+'_'+str(round(t*100))+'.png'));bpy.ops.render.render(write_still=True)
    print('SHOULDER_REVIEW',variant,json.dumps(metrics),flush=True)
(P/'shoulder-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
