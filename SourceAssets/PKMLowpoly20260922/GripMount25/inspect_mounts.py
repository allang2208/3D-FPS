"""Inspect current PKM grip interfaces in the runtime WPN_root author space."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Motion21/PKM_HingedOutlet_Editable.blend'),use_scripts=False)
r=bpy.data.objects['PKM_Manny_Rig'];r.data.pose_position='REST';bpy.context.view_layer.update()
root=r.matrix_world@r.data.bones['WPN_root'].matrix_local;graph=bpy.context.evaluated_depsgraph_get()
report={'weapon':{},'attachments':{}};weapon=[]
for ob in list(bpy.context.scene.objects):
    ob.hide_render=True
    if ob.type!='MESH' or not ob.name.startswith('PKM_') or ob.name.startswith('PKM_Bipod'):continue
    # Match the runtime mesh exporter, excluding parked/non-export source parts.
    if 'mechanical_bone' not in ob:continue
    if not any(m.type=='ARMATURE' and m.object==r for m in ob.modifiers):continue
    ev=ob.evaluated_get(graph);mesh=bpy.data.meshes.new_from_object(ev,depsgraph=graph)
    xf=root.inverted()@ev.matrix_world;mesh.transform(xf)
    copy=bpy.data.objects.new('Factory_'+ob.name,mesh);bpy.context.scene.collection.objects.link(copy)
    copy.color=(.24,.28,.33,1);weapon.append(copy)
    points=[v.co for v in mesh.vertices]
    report['weapon'][ob.name]={'min':[min(v[k] for v in points) for k in range(3)],'max':[max(v[k] for v in points) for k in range(3)]}

groups={}
for key in ['vertical','tactical_vertical','canted','prism','angled','phantom_reargrip','balanced_reargrip','stable_antislip_reargrip']:
    source=R/('GripContact15' if key.endswith('reargrip') else 'Accessories14')/f'SM_PKM_{key}.blend'
    with bpy.data.libraries.load(str(source),link=False) as (src,dst):dst.objects=src.objects
    obs=[];info={}
    for ob in dst.objects:
        if ob.type!='MESH':continue
        bpy.context.scene.collection.objects.link(ob);ob.hide_render=True;ob.hide_set(False);ob.color=(.7,.39,.12,1)
        points=[ob.matrix_world@v.co for v in ob.data.vertices]
        info[ob.name]={'min':[min(v[k] for v in points) for k in range(3)],'max':[max(v[k] for v in points) for k in range(3)],'materials':[m.name for m in ob.data.materials]}
        obs.append(ob)
    report['attachments'][key]=info;groups[key]=obs

s=bpy.context.scene;cd=bpy.data.cameras.new('MountInspection');cam=bpy.data.objects.new('MountInspection',cd);s.collection.objects.link(cam);s.camera=cam
cd.type='ORTHO';cd.clip_start=.001;s.render.engine='BLENDER_WORKBENCH'
s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.display.shading.background_type='WORLD';s.world.color=(.07,.07,.07)
s.render.resolution_x=900;s.render.resolution_y=680;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
for key,obs in groups.items():
    rear=key.endswith('reargrip')
    for ob in weapon:ob.hide_render=rear and ob.name in ['Factory_PKM_Part_045','Factory_PKM_Part_046']
    for ob in obs:ob.hide_render=False
    center=Vector((0,.012,-.025) if rear else (0,-.36,-.013))
    for view in ['side','oblique']:
        cam.location=center+Vector((.60,0,.025) if view=='side' else (.47,.25,-.18))
        cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=.255 if rear else .30
        s.render.filepath=str(O/f'before_{key}_{view}.png');bpy.ops.render.render(write_still=True)
    for ob in obs:ob.hide_render=True
(O/'source_geometry.json').write_text(json.dumps(report,indent=2))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'MountInspection.blend'))
print('PKM25_INTERFACES_READ',flush=True)
