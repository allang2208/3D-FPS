import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent
after='--after' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(O/('PKM_WristCandidate.blend' if '--candidate' in sys.argv else 'PKM_WristContact_Editable.blend') if after else R/'HandReload10/PKM_ReloadHands_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['PKM_Manny_Rig'];a=bpy.data.actions['PKM_Game_idle_Wrist12' if after else 'PKM_Game_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix']);W=r.pose.bones['WPN_root'].matrix@fit
rest={b.name:b.matrix_local.copy() for b in r.data.bones};pose={b.name:b.matrix.copy() for b in r.pose.bones}
names=[n for n in pose if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
axis=(pose['hand_l'].translation-pose['lowerarm_l'].translation).normalized()
aligned=pose['hand_l'].to_3x3()@rest['hand_l'].to_3x3().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
data={'wrist_bend_deg':math.degrees(axis.angle(aligned)), 'W':[list(v) for v in W],
      'bones':{n:{'pose':[list(v) for v in pose[n]],'rest':[list(v) for v in rest[n]],'gun_position':list(W.inverted()@pose[n].translation)} for n in names},'objects':{}}
for ob in s.objects:
 if ob.type!='MESH':continue
 visible=(ob.name=='SK_Manny_Arms_Export' or 'mechanical_bone' in ob and not ob.name.startswith('New_'))
 ob.hide_render=not visible
 ob.color=(.34,.46,.58,1) if ob.name=='SK_Manny_Arms_Export' else (.18,.20,.23,1)
 if visible:ob.hide_set(False)
 if 'mechanical_bone' in ob and not ob.name.startswith('New_'):
  deps=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(deps);me=ev.to_mesh();pts=[W.inverted()@ev.matrix_world@v.co for v in me.vertices]
  if pts:data['objects'][ob.name]={'id':ob.get('source_part_id',-1),'bone':ob['mechanical_bone'],'bounds':[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]]}
  ev.to_mesh_clear()
 for mat in ob.data.materials:
  if mat:mat.diffuse_color=(.34,.46,.58,1) if ob.name=='SK_Manny_Arms_Export' else (.18,.20,.23,1)
(O/('source_after.json' if after else 'source_diagnosis.json')).write_text(json.dumps(data,indent=2))
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.studiolight_rotate_z=.45;s.display.shading.color_type='OBJECT';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.background_type='WORLD';s.world.color=(.065,.065,.065)
s.render.resolution_x=1000;s.render.resolution_y=850;s.render.resolution_percentage=100;s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=87
cam=bpy.data.objects.new('Wrist12Review',bpy.data.cameras.new('Wrist12Review'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.55
for name,pos,target in [('before_side',(.6,.18,.015),(.065,.065,-.06)),('before_underside',(.38,-.36,-.38),(.04,-.055,-.055))]:
 cam.location=W@Vector(pos);cam.rotation_euler=(W@Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/((name.replace('before','after') if after else name)+'.jpg'));bpy.ops.render.render(write_still=True)
print('PKM12_WRIST_AXIS_BEND_DEGREES',data['wrist_bend_deg'])
