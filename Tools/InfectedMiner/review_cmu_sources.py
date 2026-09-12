"""Inspect unmodified human capture on a proportional joint/body proxy."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
R=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912/Reference/CMU')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.preferences.addon_enable(module='io_anim_bvh')
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=4;s.render.resolution_x=420;s.render.resolution_y=520;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('MocapReview');s.world.use_nodes=True;next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.7
def mat(name,c):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=.7;return m
mats=[mat('Body',(.25,.32,.34)),mat('Left',(.12,.32,.55)),mat('Right',(.65,.28,.10))]
links=[('Hips','Spine1',.105),('Spine1','Neck',.12),('Neck','Head',.06)]
for side in ['Left','Right']:links.extend([(side+'UpLeg',side+'Leg',.065),(side+'Leg',side+'Foot',.045),(side+'Foot',side+'ToeBase',.045),(side+'Arm',side+'ForeArm',.045),(side+'ForeArm',side+'Hand',.035),('Spine1',side+'Arm',.055)])
objects=[]
for a,b,rad in links:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8);o=bpy.context.object;o.name=a+'_'+b;o.data.materials.append(mats[1 if a.startswith('Left') else 2 if a.startswith('Right') else 0]);objects.append((o,a,b,rad))
bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=12);head=bpy.context.object;head.data.materials.append(mats[0])
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.data.materials.append(mat('Floor',(.07,.08,.09)))
for p,e in [((3,-4,5),700),((-3,1,4),550)]:
    d=bpy.data.lights.new('Softbox','AREA');d.energy=e;d.size=4;o=bpy.data.objects.new('Softbox',d);s.collection.objects.link(o);o.location=p;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Camera');c=bpy.data.objects.new('Camera',d);s.collection.objects.link(c);s.camera=c;d.type='ORTHO';d.ortho_scale=3.15
clips=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['79_01','80_71','02_07','02_08','02_09']
for clip in clips:
    fps=120 if clip.startswith('02') else 60;s.render.fps=fps
    bpy.ops.import_anim.bvh(filepath=str(R/(clip+'.bvh')),global_scale=1,frame_start=1,use_fps_scale=False,update_scene_fps=False,rotate_mode='QUATERNION',axis_forward='-Z',axis_up='Y');r=bpy.context.object
    s.frame_set(1);bpy.context.view_layer.update();zs=[(r.matrix_world@b.head).z for b in r.pose.bones];scale=1.78/(max(zs)-min(zs));r.scale*=scale;bpy.context.view_layer.update()
    origin=(r.matrix_world@r.pose.bones['Hips'].matrix).translation;origin.z=0
    c.location=origin+Vector((3,-5,2.7));c.rotation_euler=(origin+Vector((0,0,1.1))-c.location).to_track_quat('-Z','Y').to_euler()
    folder=R/'Previews'/clip;folder.mkdir(parents=True,exist_ok=True);end=round(r.animation_data.action.frame_range[1]);rows=[]
    for i,f in enumerate(range(2,end+1,round(fps/4))):
        s.frame_set(f);bpy.context.view_layer.update();p={b.name:(r.matrix_world@b.matrix).translation for b in r.pose.bones}
        for o,a,b,rad in objects:
            v=p[b]-p[a];o.location=(p[a]+p[b])*.5;o.rotation_euler=v.to_track_quat('Z','Y').to_euler();o.scale=(rad,rad,v.length*.58)
        head.location=p['Head']+Vector((0,0,.075));head.scale=(.09,.10,.125)
        floor.location.z=min(p['LeftToeBase'].z,p['RightToeBase'].z)-.04
        rows.append({'frame':f,'time':(f-2)/fps,'hips':list(p['Hips']),'left_hand':list(p['LeftHand']),'right_hand':list(p['RightHand'])})
        s.render.filepath=str(folder/f'{i:04d}.png');bpy.ops.render.render(write_still=True)
    (R/(clip+'-review.json')).write_text(json.dumps({'source_clip':clip,'native_fps':fps,'frames':end-1,'seconds':(end-2)/fps,'scale':scale,'samples':rows},indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(R/(clip+'-source-review.blend')));bpy.data.objects.remove(r,do_unlink=True)
    print('CMU_SOURCE_REVIEWED '+clip,flush=True)
