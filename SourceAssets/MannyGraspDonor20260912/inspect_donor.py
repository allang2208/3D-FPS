import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector
O=Path(__file__).parent
D=O/'Donor'
label='vre' if '--vre' in sys.argv else 'original'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(D/'SKM_MannyXR_right.fbx'), automatic_bone_orientation=False)
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH')
r.name='Epic_XR_Original'
mesh_rig_world=r.matrix_world.copy()
base_names=set(bpy.data.objects.keys())
bpy.ops.import_scene.fbx(filepath=str(D/('GrabAnimation.fbx' if label=='vre' else 'A_MannequinsXR_Grasp_Right.fbx')), automatic_bone_orientation=False)
ar=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and o!=r)
a=ar.animation_data.action.copy()
# UE exports animation object scale as well as bones. Preserve the mesh export's
# centimeter conversion; applying both object conversions would shrink it 100x.
for layer in a.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for fc in list(bag.fcurves):
                if not fc.data_path.startswith('pose.bones['):bag.fcurves.remove(fc)
r.animation_data_create();r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
r.matrix_world=mesh_rig_world
for ob in list(bpy.data.objects):
    if ob.name not in base_names:bpy.data.objects.remove(ob,do_unlink=True)
s=bpy.context.scene;s.frame_set(int(a.frame_range[1] if label=='vre' else a.frame_range[0]));bpy.context.view_layer.update()
data={'armature_world':[list(x) for x in r.matrix_world], 'frames':list(a.frame_range), 'bones':{}, 'mesh':{'name':mesh.name,'dimensions':list(mesh.dimensions)}}
for b in r.pose.bones:
    data['bones'][b.name]={'parent':b.parent.name if b.parent else None,'rest':[list(x) for x in b.bone.matrix_local], 'pose':[list(x) for x in b.matrix], 'basis':[list(x) for x in b.matrix_basis]}
(O/('donor_pose.json' if label=='original' else 'vre_pose.json')).write_text(json.dumps(data,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(D/(label+'_Grasp_Original.blend')))
# Original mesh and original authored pose, shown in palm-aligned views.
mat=bpy.data.materials.new('NeutralOriginal');mat.diffuse_color=(.36,.48,.58,1);mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.36,.48,.58,1);bs.inputs['Roughness'].default_value=.5
mesh.data.materials.clear();mesh.data.materials.append(mat)
h=r.matrix_world@r.pose.bones['hand_r'].matrix
def pos(name):return (r.matrix_world@r.pose.bones[name].matrix).translation
forward=(pos('middle_01_r')-h.translation).normalized()
across=(pos('index_01_r')-pos('pinky_01_r')).normalized();across=(across-forward*across.dot(forward)).normalized()
normal=across.cross(forward).normalized()
center=(h.translation+pos('middle_01_r'))*.5
cam=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',cam);s.collection.objects.link(co);s.camera=co;cam.type='ORTHO';cam.ortho_scale=.23;cam.clip_start=.001
s.render.engine='BLENDER_EEVEE';s.eevee.taa_render_samples=32;s.render.resolution_x=850;s.render.resolution_y=850;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Studio');s.world.color=(.12,.12,.12)
for i,off in enumerate([Vector((.4,-.4,.6)),Vector((-.4,.3,.5))]):
    light=bpy.data.lights.new('Area'+str(i),'AREA');light.energy=90;light.size=.7;lo=bpy.data.objects.new(light.name,light);s.collection.objects.link(lo);lo.location=center+off;lo.rotation_euler=(center-lo.location).to_track_quat('-Z','Y').to_euler()
for view,offset in [('back',normal*.4),('palm',-normal*.4),('thumb',across*.4+normal*.13),('front',forward*.4+normal*.13)]:
    co.location=center+offset;co.rotation_euler=(center-co.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/(label+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
print('DONOR_ORIGINAL_RENDER_PASS',flush=True)
