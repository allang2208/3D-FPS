from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
row={n:Matrix(m) for n,m in json.loads((O/'final_poses.json').read_text())['reload'][101].items()}
r.matrix_world=Matrix.Identity(4);set_pose(row)
for n in ('hand_l','hand_r','WPN_Magazine','lowerarm_l'):
 print('BONE',n,'row',list(row[n].translation),'evaluated',list(r.pose.bones[n].matrix.translation),'basis',list(r.pose.bones[n].matrix_basis.translation),flush=True)
for n in ('M24_clip','M24_V9_BareArms','M24_Magazine10'):
 o=bpy.data.objects[n];print('OBJECT',n,'world',[list(v) for v in o.matrix_world],'modifiers',[(m.name,m.type) for m in o.modifiers],'constraints',[(c.name,c.type) for c in o.constraints],flush=True)
print('SKIN_GROUPS',[(v.index,v.name) for v in skin.vertex_groups][:6],flush=True)
setup_render();s.render.resolution_x=800;s.render.resolution_y=600
set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
bpy.data.objects['M24_clip'].hide_render=False;bpy.data.objects['M24_Magazine10'].hide_render=True
target=(row['hand_l'].translation+row['middle_02_l'].translation)*.5
cam.location=target+Vector((-.30,-.12,.10));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.29
bpy.context.view_layer.update()
mesh=skin.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh();ids=[v.index for v in skin.data.vertices if any(skin.vertex_groups[g.group].name=='hand_l' and g.weight>.7 for g in v.groups)]
print('LEFT_CENTER',list(sum((mesh.vertices[i].co for i in ids),Vector())/len(ids)),'BONE',list(row['hand_l'].translation),'CAM',cam.name,list(cam.location),list(target),'ACTIVE',s.camera.name,'MARKERS',[(m.name,m.camera.name if m.camera else None) for m in s.timeline_markers],flush=True)
s.render.filepath=str(O/'debug_hand.png');bpy.ops.render.render(write_still=True)
