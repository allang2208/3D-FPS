import bpy, json, sys, gzip
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent
stage='after' if '--after' in sys.argv else 'before'
PREV=O if stage=='after' else O.parent/'M870AKMArmSupport20261016'
blend='M870_ReloadContact_Editable.blend' if stage=='after' else 'M870_AKMArmSupport_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(PREV/blend),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
a=json.loads((PREV/'authoring.json').read_text())['clips']['reload_continuous']['action']
r.animation_data.action=bpy.data.actions[a];r.animation_data.action_slot=r.animation_data.action.slots[0]
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
shell=bpy.data.objects['M870_ReloadShell']
shell_points=[rest['WPN_Shell'].inverted()@shell.matrix_world@v.co for v in shell.data.vertices]
shell_centre=sum(shell_points,Vector())/len(shell_points)
# The editable source's preview skin predates the retained native V7 surface.
# Diagnose contact on the actual installed native geometry and weights.
bpy.data.objects.remove(bpy.data.objects['M870_V7'],do_unlink=True)
d=json.loads(gzip.decompress((O.parent/'M870SurfaceFit20261016/native_arms.json.gz').read_bytes()))
faces=[f for f in d['faces'] if any(sum(w for n,w in d['weights'][i].items() if n.endswith('_r'))>.5 for i in f)]
mesh=bpy.data.meshes.new('NativeRightArm');mesh.from_pydata([(v[0]/100,-v[1]/100,v[2]/100) for v in d['vertices']],[],faces);mesh.update()
arm=bpy.data.objects.new('NativeRightArm',mesh);s.collection.objects.link(arm)
for face in mesh.polygons:face.use_smooth=True
for n in {n for w in d['weights'] for n in w}:arm.vertex_groups.new(name=n)
for i,weights in enumerate(d['weights']):
 for n,w in weights.items():arm.vertex_groups[n].add([i],w,'REPLACE')
arm.parent=r;arm.matrix_parent_inverse=Matrix.Identity(4);arm.matrix_basis=Matrix.Identity(4);arm.modifiers.new('Native skin','ARMATURE').object=r
report={'objects':[(o.name,o.type) for o in s.objects], 'shell_centre_local':list(shell_centre),'samples':[]}
for f in (18,24,30,36,40,44,46,48,50,60,80,94):
 s.frame_set(f)
 hand=r.pose.bones['hand_r'].matrix
 centre=r.pose.bones['WPN_Shell'].matrix@shell_centre
 bpy.context.view_layer.update();dep=bpy.context.evaluated_depsgraph_get()
 ev=shell.evaluated_get(dep);sm=ev.to_mesh();tree=BVHTree.FromPolygons([ev.matrix_world@v.co for v in sm.vertices],[list(p.vertices) for p in sm.polygons],all_triangles=False)
 av=arm.evaluated_get(dep);am=av.to_mesh();gaps={}
 for digit in ('thumb','index','middle','ring'):
  ids=[i for i,w in enumerate(d['weights']) if sum(value for n,value in w.items() if n.startswith(digit+'_') and n.endswith('_r'))>.8]
  near=[tree.find_nearest(av.matrix_world@am.vertices[i].co) for i in ids]
  gaps[digit]=min(v[3] for v in near if v[0] is not None)*1000
 av.to_mesh_clear();ev.to_mesh_clear()
 report['samples'].append({'frame':f,'hand':list(hand.translation),'shell':list(centre),'shell_in_hand':list(hand.inverted()@centre),
  'fingers':{n:list(r.pose.bones[n].matrix.translation) for n in ('thumb_03_r','index_03_r','middle_03_r','ring_03_r','pinky_03_r')},
  'shell_scale':list(r.pose.bones['WPN_Shell'].matrix.to_scale()),'hand_matrix':[list(v) for v in hand],
  'shell_matrix':[list(v) for v in r.pose.bones['WPN_Shell'].matrix],'digit_surface_gap_mm':gaps})
(O/(stage+'_contact.json')).write_text(json.dumps(report,indent=2))
for ob in s.objects:
 if ob.type=='MESH':
  ob.hide_render=False
  ob.color=(.65,.35,.20,1) if ob==arm else (.8,.025,.01,1) if ob==shell else (.10,.12,.14,1)
for ob in list(s.objects):
 if ob.type in ('CAMERA','LIGHT'):bpy.data.objects.remove(ob,do_unlink=True)
cam=bpy.data.objects.new('ContactCamera',bpy.data.cameras.new('ContactCamera'));s.collection.objects.link(cam);s.camera=cam
s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=960;s.render.resolution_y=720;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True
s.display.shading.background_type='WORLD'
if not s.world:s.world=bpy.data.worlds.new('ContactWorld')
s.world.color=(.08,.08,.08)
for f in (30,40,44):
 s.frame_set(f)
 hand=r.pose.bones['hand_r'].matrix
 centre=(hand.translation+r.pose.bones['WPN_Shell'].matrix@shell_centre)*.5
 cam.location=centre+Vector((-.28,.20,.27));cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.32
 s.render.filepath=str(O/f'{stage}_{f}.png');bpy.ops.render.render(write_still=True)
 if f==40:
  for ob in s.objects:
   if ob.type=='MESH' and ob not in (arm,shell):ob.hide_render=True
  cam.location=centre+Vector((.25,-.30,-.15));cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler()
  s.render.filepath=str(O/f'{stage}_{f}_palm.png');bpy.ops.render.render(write_still=True)
  for ob in s.objects:
   if ob.type=='MESH':ob.hide_render=False
print('M870_CONTACT_DIAGNOSED',str(O/'before_contact.json'))
