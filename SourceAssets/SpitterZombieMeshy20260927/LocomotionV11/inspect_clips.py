"""User-requested offline pose / contact / loop inspection of B, C and Run."""
import bpy,json,math,os
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
REV=os.environ.get('SPITTER_INSPECT_REV','V10');SOURCE=BASE/('Locomotion'+REV)
OUT=ROOT/('Inspect'+REV);OUT.mkdir(exist_ok=True)
author=json.loads((SOURCE/'authoring.json').read_text(encoding='utf-8'))
NAMES=['Hips','Spine','neck','Head','LeftArm','LeftForeArm','LeftHand','RightArm','RightForeArm','RightHand',
       'LeftUpLeg','LeftLeg','LeftFoot','RightUpLeg','RightLeg','RightFoot']
report={}
for role in ['Walk_B','Walk_C','Run_A']:
    entry=author['movement'][role]
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=entry['file'],use_image_search=False)
    scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
    meshes=[o for o in scene.objects if o.type=='MESH'];action=rig.animation_data.action
    first,last=action.frame_range;rate=scene.render.fps/scene.render.fps_base;n=round(last-first)
    feet={}
    for ob in meshes:
        names={g.index:g.name for g in ob.vertex_groups}
        feet[ob.name]={s:[v.index for v in ob.data.vertices if sum(g.weight for g in v.groups
            if names[g.group] in [s+'Foot',s+'ToeBase'])>.60] for s in ['Left','Right']}
    rows=[]
    for i in range(n+1):
        scene.frame_set(round(first+i));row={'t':i/rate,'bones':{},'sole':{s:1e9 for s in ['Left','Right']}}
        for name in NAMES:
            b=rig.pose.bones[name];m=rig.matrix_world@b.matrix
            row['bones'][name]=dict(p=list(m.translation),q=list(m.to_quaternion()),local_q=list(b.matrix_basis.to_quaternion()))
        deps=bpy.context.evaluated_depsgraph_get()
        for ob in meshes:
            obj=ob.evaluated_get(deps);skin=obj.to_mesh()
            for side in ['Left','Right']:
                row['sole'][side]=min(row['sole'][side],min((obj.matrix_world@skin.vertices[j].co).z for j in feet[ob.name][side]))
            obj.to_mesh_clear()
        rows.append(row)
    def angle(a,b):return math.degrees(2*math.acos(min(1.,abs(a.normalized().dot(b.normalized())))))
    from mathutils import Quaternion
    stats={}
    for name in NAMES:
        q=[Quaternion(r['bones'][name]['q']) for r in rows]
        steps=np.array([angle(a,b)*rate for a,b in zip(q,q[1:])])
        stats[name]=dict(rotation_range_deg=max(angle(q[0],b) for b in q),
            max_deg_s=float(max(steps)),p95_deg_s=float(np.percentile(steps,95)),
            seam_in_deg_s=float(steps[-1]),seam_out_deg_s=float(steps[0]),
            peak_frame=int(np.argmax(steps)))
    soles={s:dict(min_cm=min(r['sole'][s] for r in rows)*100,max_cm=max(r['sole'][s] for r in rows)*100) for s in ['Left','Right']}
    report[role]=dict(seconds=n/rate,fps=rate,speed=entry['reference_speed_cm_s'],stats=stats,soles=soles,frames=rows)
    # Actual exported mesh/skin, with active animation evaluation during render.
    scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=320;scene.render.resolution_y=384
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
    scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT';scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD'
    scene.world=bpy.data.worlds.new('InspectionWorld');scene.world.color=(.04,.04,.04)
    for ob in meshes:ob.color=(.50,.60,.51,1)
    camera=bpy.data.cameras.new('InspectionCamera');cam=bpy.data.objects.new('InspectionCamera',camera)
    scene.collection.objects.link(cam);scene.camera=cam;cam.location=(3.5,-6,2.0)
    cam.rotation_euler=(Vector((0,0,.95))-cam.location).to_track_quat('-Z','Y').to_euler()
    camera.type='ORTHO';camera.ortho_scale=2.22
    bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.004));bpy.context.object.color=(.13,.15,.17,1)
    target=OUT/role;target.mkdir(exist_ok=True)
    for i in range(round(n/rate*12)):
        frame=first+i/12*rate;scene.frame_set(math.floor(frame),subframe=frame%1)
        scene.render.filepath=str(target/f'{i:03d}.png');bpy.ops.render.render(write_still=True)
    print('SPITTER_INSPECTED',REV,role,json.dumps(dict(soles=soles,peaks={k:stats[k] for k in ['Head','LeftLeg','RightLeg']})),flush=True)
(OUT/'measurements.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SPITTER_INSPECTION_COMPLETE',REV,flush=True)
