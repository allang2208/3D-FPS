"""Finalize adapter triangles and manufacture the three actual-model UI icons."""
import bpy,json,math,shutil
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;I=O/'Icons';I.mkdir(exist_ok=True)
D=O.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'
records={}
for host,definition in [('AKM','ue_akm'),('A762','ue_a762'),('PKM','ue_pkm_lowpoly')]:
    bpy.ops.wm.open_mainfile(filepath=str(O/('PSO1_'+host+'_Editable.blend')))
    scene=bpy.context.scene;parts=[o for o in scene.objects if o.type=='MESH' and not o.hide_render]
    bpy.ops.object.select_all(action='DESELECT')
    for ob in parts:
        ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
        if any('Adapter' in m.name for m in ob.data.materials if m):
            mod=ob.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
        ob.matrix_world=Matrix.Identity(4)
    bpy.context.view_layer.objects.active=parts[0]
    bpy.ops.export_scene.fbx(filepath=str(O/'Exports'/('SM_PSO1_'+host+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    for ob in parts:ob.matrix_world=Matrix.Rotation(-math.pi/2,4,'Z')
    bpy.ops.wm.save_as_mainfile(filepath=str(O/('PSO1_'+host+'_Editable.blend')))
    # Icon frame is canonical +X forward, viewed from +Y: target end appears left.
    for ob in parts:ob.matrix_world=Matrix.Identity(4)
    points=[ob.matrix_world@v.co for ob in parts for v in ob.data.vertices]
    lo=Vector([min(p[k] for p in points) for k in range(3)]);hi=Vector([max(p[k] for p in points) for k in range(3)])
    center=(lo+hi)*.5;extent=hi-lo
    camera_data=bpy.data.cameras.new('PSO1_IconCamera');camera=bpy.data.objects.new('PSO1_IconCamera',camera_data);scene.collection.objects.link(camera)
    camera.location=center+Vector((0,1.5,0));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.type='ORTHO';camera_data.ortho_scale=max(extent.x,extent.z)/.82;camera_data.clip_start=.01;scene.camera=camera
    for name,offset,energy,size in [('Key',(.05,.40,.45),32,.40),('Fill',(-.30,.2,.18),18,.35),('Rim',(.12,-.28,.28),35,.30)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.shape='DISK';light.size=size
        ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=center+Vector(offset);ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
    scene.world=bpy.data.worlds.new('NeutralIconWorld');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.18,.18,.18,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
    scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
    scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    key=definition+'_optic_pso1_4x';output=I/(key+'.png');scene.render.filepath=str(output)
    bpy.ops.wm.save_as_mainfile(filepath=str(I/(key+'.blend')))
    bpy.ops.render.render(write_still=True)
    shutil.copy2(output,D/output.name)
    records[key]={'host':host,'source':str(O/('PSO1_'+host+'_Editable.blend')),'output':str(D/output.name),
      'dimensions':[1024,1024],'background':'transparent','forward':'left','purpose':'production UI icon, not acceptance render'}
    (O/'icons.json').write_text(json.dumps(records,indent=2))
    print('PSO1_ICON_SAVED',key,flush=True)
