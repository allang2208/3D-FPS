from pathlib import Path
exec(compile((Path(__file__).parent/'inspect.py').read_text().split("\nif __name__=='__main__':")[0],'setup','exec'))
current=skin;P=np.array([v.co[:] for v in current.data.shape_keys.key_blocks[0].data]);current_rest={n:m.copy() for n,m in rest.items()}
before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O.parent/'M24CustomScope20261026/V9/M4_V9_Template.fbx'),use_anim=False)
added=[ob for ob in bpy.data.objects if ob not in before];tr=next(ob for ob in added if ob.type=='ARMATURE');tm=next(ob for ob in added if ob.type=='MESH');slots={i for i,m in enumerate(tm.data.materials) if m and 'SkinV9' in m.name};used=sorted({v for p in tm.data.polygons if p.material_index in slots for v in p.vertices});transform=tr.matrix_world.inverted()@tm.matrix_world
Q=np.array([transform@tm.data.shape_keys.key_blocks[0].data[i].co for i in used]);pos=np.linalg.norm(P-Q,axis=1)
rest_error=max((tr.data.bones[n].matrix_local.translation-current_rest[n].translation).length for n in current_rest if n in tr.data.bones and not n.startswith('WPN_'))
weight_error=0
for i,j in enumerate(used):
    a={current.vertex_groups[g.group].name:g.weight for g in current.data.vertices[i].groups};b={tm.vertex_groups[g.group].name:g.weight for g in tm.data.vertices[j].groups}
    weight_error=max(weight_error,max(abs(a.get(n,0)-b.get(n,0)) for n in a.keys()|b.keys()))
report={'vertices':len(P),'max_v9_basis_delta_mm':float(pos.max()*1000),'max_reference_joint_delta_mm':rest_error*1000,'max_weight_delta':weight_error}
for ob in added:bpy.data.objects.remove(ob,do_unlink=True)
row=pose('idle',0)[0];set_pose(row);report['active_shapes']={k.name:k.value for k in skin.data.shape_keys.key_blocks if k.value}
folder=O/'BeforeViews';root=row['WPN_root']@rest['WPN_root'].inverted();target=row['hand_l'].translation;cam.location=target+root.to_3x3()@Vector((-.23,.08,.15));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.24;s.render.resolution_x=800;s.render.resolution_y=540
for key in skin.data.shape_keys.key_blocks:key.value=0
bpy.context.view_layer.update();s.render.filepath=str(folder/'wrist_no_shapes.png');bpy.ops.render.render(write_still=True)
(O/'template_comparison.json').write_text(json.dumps(report,indent=2));print('V9_COMPARISON',json.dumps(report),flush=True)
