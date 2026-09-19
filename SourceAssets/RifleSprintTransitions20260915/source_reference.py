"""Read current authored sprint contacts and render the existing loop as a reference."""
import bpy, json, math, sys
from bpy_extras.object_utils import world_to_camera_view
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
S=O.parent
label=sys.argv[sys.argv.index('--')+1]
out=O/label;out.mkdir(parents=True,exist_ok=True)
report={}
for weapon in ('M4','AKM','QBZ191'):
    folder=S/'M4TacticalSprint20260915' if weapon=='M4' else S/'RifleTacticalSprint20260915'/weapon
    for profile in (('Base','Drum','Angled','Vertical','Canted','Prism') if weapon=='M4' else ('Base','Angled','Vertical','Canted','Prism')):
        info=json.loads((folder/profile/'authoring.json').read_text())
        bpy.ops.wm.open_mainfile(filepath=str(folder/profile/f'{weapon}_TacticalSprint_{profile}_Editable.blend'))
        rig=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene
        def pose(kind,t):
            a=bpy.data.actions[info['clips'][kind]['action']]
            rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
            f=t*info['clips'][kind]['duration']*60
            scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
            return {b.name:b.matrix.copy() for b in rig.pose.bones}
        left=['hand_l','index_03_l','thumb_03_l','lowerarm_l','upperarm_l']
        e=pose('Enter',0);x=pose('Exit',1)
        gap=max((e[n].translation-x[n].translation).length for n in e)
        max_reverse=0.;contact=[];lower=[]
        for i in range(61):
            p=pose('Enter',i/60);q=pose('Exit',1-i/60)
            max_reverse=max(max_reverse,max((p[n].translation-q[n].translation).length for n in p))
        first=pose('Loop',0);last=pose('Loop',1)
        loopgap=max((first[n].translation-last[n].translation).length for n in first)
        for i in range(73):
            p=pose('Loop',i/72)
            contact.append(list(p['WPN_root'].inverted()@p['hand_r'].translation))
            lower.append({n:list(p[n].translation) for n in left})
        report[weapon+':'+profile]={'idle_endpoint_gap_m':gap,'reverse_path_gap_m':max_reverse,
            'loop_gap_m':loopgap,'right_contact_drift_m':max((Vector(v)-Vector(contact[0])).length for v in contact),'left_loop':lower}
        pose('Loop',.25)
        for ob in scene.objects:
            if ob.type in ('CAMERA','LIGHT'):ob.hide_render=True
        cam_data=bpy.data.cameras.new('SprintReference');cam=bpy.data.objects.new('SprintReference',cam_data);scene.collection.objects.link(cam)
        cam.location=(-.07,-.06 if weapon=='AKM' else 0,.07);cam.rotation_euler=(math.pi/2,0,0)
        cam_data.type='PERSP';cam_data.lens_unit='FOV';cam_data.angle=math.radians(112);cam_data.clip_start=.005;scene.camera=cam
        scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100
        selected=[]
        for ob in scene.objects:
            if ob.type!='MESH' or ob.hide_render:continue
            groups={g.index for g in ob.vertex_groups if g.name.endswith('_l') and g.name.startswith(('hand','thumb','index','middle','ring','pinky','lowerarm'))}
            ids=[v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if g.group in groups)>.5]
            if ids:selected.append((ob,ids))
        visible=0;vertices=0
        for i in range(25):
            pose('Loop',i/24);deps=bpy.context.evaluated_depsgraph_get()
            for ob,ids in selected:
                ev=ob.evaluated_get(deps);mesh=ev.to_mesh()
                for j in ids:
                    p=world_to_camera_view(scene,cam,ev.matrix_world@mesh.vertices[j].co)
                    visible+=int(p.z>0 and -.02<=p.x<=1.02 and -.02<=p.y<=1.02);vertices+=1
                ev.to_mesh_clear()
        report[weapon+':'+profile]['left_surface_samples']=vertices
        report[weapon+':'+profile]['left_surface_in_view']=visible
        if profile!='Base':continue
        pose('Loop',.25)
        for name,loc,power,size in [('key',(1,-1,1),180,2),('fill',(-1,0,.5),110,2)]:
            data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=size
            light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=loc
            light.rotation_euler=(Vector((0,.3,-.1))-light.location).to_track_quat('-Z','Y').to_euler()
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100
        scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
        scene.render.filepath=str(out/f'{weapon}-loop-reference.png');bpy.ops.render.render(write_still=True)
(out/'source-continuity.json').write_text(json.dumps(report,indent=2))
print('SPRINT_SOURCE_REFERENCE_COMPLETE',label)
