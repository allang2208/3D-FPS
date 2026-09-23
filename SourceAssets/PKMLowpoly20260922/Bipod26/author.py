"""Split the existing PKM bipod and author its requested legs-down rest pose."""
import bpy,json,shutil,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;R=O.parent;E=O/'Exports';E.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'SourceInspection.blend'),use_scripts=False)
parts={i:bpy.data.objects['Bipod26_'+str(i)] for i in [65,72,127,128,129]}
pin=[v.co for v in parts[129].data.vertices]
hinge=Vector([(min(p[k] for p in pin)+max(p[k] for p in pin))*.5 for k in range(3)])
bpy.context.preferences.filepaths.save_version=0
report={'source':'Motion21/PKM_HingedOutlet_Editable.blend','rest_pose':'legs down, 12 degree outward splay; no ground deployment mechanic','hinge_root_m':list(hinge),
        'hinge_ue_cm':[hinge.x*100,-hinge.y*100,hinge.z*100],'parts':{}}
# Clamp and transverse pin stay with the barrel. The folded retaining clip
# stays on its own leg when the two legs are open; it does not tie them together.
groups={'Base':[72,129],'LegA':[127,65],'LegB':[128]}
for key,ids in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    pivot=Vector() if key=='Base' else hinge.copy()
    rotation=Matrix.Identity(4)
    if key!='Base':
        leg=parts[127 if key=='LegA' else 128]
        pivot.x=(min(v.co.x for v in leg.data.vertices)+max(v.co.x for v in leg.data.vertices))*.5
        rotation=Matrix.Rotation(math.radians(-12 if key=='LegA' else 12),4,'Y')@Matrix.Rotation(math.radians(-82),4,'X')
    obs=[]
    for i in ids:
        original=parts[i];mesh=original.data.copy();mesh.transform(rotation@Matrix.Translation(-pivot))
        ob=bpy.data.objects.new(f'PKM26_{key}_{i}',mesh);bpy.context.scene.collection.objects.link(ob)
        ob.select_set(True);ob.hide_render=False;obs.append(ob)
    bpy.context.view_layer.objects.active=obs[0]
    name='SM_PKM_Bipod_'+key
    bpy.ops.export_scene.fbx(filepath=str(E/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    points=[v.co for ob in obs for v in ob.data.vertices]
    report['parts'][key]={'name':name,'source_part_ids':ids,'pivot_root_m':list(pivot),
        'pivot_ue_cm':[pivot.x*100,-pivot.y*100,pivot.z*100],
        'size_cm':[(max(p[k] for p in points)-min(p[k] for p in points))*100 for k in range(3)],
        'center_local_cm':[(max(p[k] for p in points)+min(p[k] for p in points))*50*(1 if k!=1 else -1) for k in range(3)]}
    for ob in obs:ob.location=pivot;ob.select_set(False)
for ob in bpy.context.scene.objects:
    ob.hide_render=not ob.name.startswith('PKM26_')
    if ob.name.startswith('PKM26_'):ob.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_Bipod_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2))
# Production icon: the existing model and authored QBZ finish, neutral studio,
# camera along +X means the weapon's forward (-Y) is screen-left.
s=bpy.context.scene
points=[ob.matrix_world@v.co for ob in s.objects if ob.name.startswith('PKM26_') for v in ob.data.vertices]
low=Vector([min(v[k] for v in points) for k in range(3)]);high=Vector([max(v[k] for v in points) for k in range(3)]);center=(low+high)*.5
cam=s.camera;cam.location=center+Vector((.9,0,0));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=max((high-low).y,(high-low).z)/.82
s.render.engine='CYCLES';s.cycles.samples=48;s.render.film_transparent=True
s.render.resolution_x=s.render.resolution_y=1024;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.world.color=(.12,.12,.12)
for name,offset,power,size in [('Key',(.45,-.35,.50),70,.55),('Fill',(.4,.35,.05),35,.5),('Rim',(-.3,.0,.30),70,.4)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    ob=bpy.data.objects.new(name,light);s.collection.objects.link(ob);ob.location=center+Vector(offset);ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(O/'pkm_bipod_icon.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_Bipod_Icon.blend'))
icons=R.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'
for name in ['ue_pkm_lowpoly_category_bipod.png','ue_pkm_lowpoly_bipod_pkm_bipod.png']:
    shutil.copy2(O/'pkm_bipod_icon.png',icons/name)
shutil.copy2(icons/'underbarrel_false.png',icons/'bipod_false.png')
print('PKM26_AUTHORED',json.dumps(report),flush=True)
