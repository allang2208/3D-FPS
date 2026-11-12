"""Scoped offline pose inspection requested by the user; no gameplay launch."""
from pathlib import Path
import json, math
import bpy
from mathutils import Vector
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/Beast06V1')
OUT=BASE/'Inspection/Candidates'; OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Delivery/MantisM27_Beast06V1.blend'))
scene=bpy.context.scene; rig=next(o for o in scene.objects if o.type=='ARMATURE')
body=max((o for o in scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
for tr in rig.animation_data.nla_tracks: tr.mute=True
for ob in scene.objects: ob.hide_render=ob not in [rig,body]
body.data.materials.clear()
for label,col in [('Body',(.40,.43,.46,1)),('Left',(.12,.66,.29,1)),('Right',(.64,.24,.78,1))]:
    mat=bpy.data.materials.new(label); mat.diffuse_color=col; body.data.materials.append(mat)
vg={g.index:g.name for g in body.vertex_groups}; labels=[]
for v in body.data.vertices:
    best=max(v.groups,key=lambda g:g.weight,default=None); n=vg[best.group] if best else ''
    labels.append(1 if n=='blade_root_l' else 2 if n=='blade_root_r' else 0)
for p in body.data.polygons:
    ids=[labels[i] for i in p.vertices]; p.material_index=max(set(ids),key=ids.count)
scene.render.engine='BLENDER_WORKBENCH'; shading=scene.display.shading
shading.light='STUDIO'; shading.color_type='MATERIAL'; shading.show_shadows=True
shading.show_cavity=True; shading.cavity_type='BOTH'; shading.background_type='WORLD'
if not scene.world: scene.world=bpy.data.worlds.new('CandidateWorld')
scene.world.color=(.055,.06,.07)
scene.render.resolution_x=scene.render.resolution_y=480; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
cam_data=bpy.data.cameras.new('CandidateCamera'); cam=bpy.data.objects.new('CandidateCamera',cam_data)
scene.collection.objects.link(cam); scene.camera=cam; cam_data.type='ORTHO'; cam_data.ortho_scale=325; cam_data.clip_end=2500
target=Vector((0,-40,125)); cam.location=(420,-650,310)
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
manifest=json.loads((BASE/'Delivery/motion_manifest.json').read_text())
for role,info in manifest['clips'].items():
    rig.animation_data.action=bpy.data.actions['A_M27_'+role+'_Beast06V1']
    if rig.animation_data.action.slots: rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    # Every other frame for the short actions; 40 evenly spaced idle frames.
    frames=list(range(1,info['frames'],2)) if role!='Idle' else list(range(1,info['frames'],10))
    for index,frame in enumerate(frames):
        scene.frame_set(frame); scene.render.filepath=str(OUT/f'{role}_{index:03d}.png')
        bpy.ops.render.render(write_still=True)
print('M27_BEAST06_PREVIEWS_RENDERED',flush=True)
