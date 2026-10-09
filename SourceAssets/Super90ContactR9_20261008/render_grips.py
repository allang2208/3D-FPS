from pathlib import Path
O=Path(__file__).parent;src=O/'render_saved.py';ns={'__file__':str(src)}
exec(compile(src.read_text().split('items=[]')[0],str(src),'exec'),ns)
bpy=ns['bpy'];s=ns['s'];Vector=ns['Vector'];Matrix=ns['Matrix'];scene=ns['scene'];json=ns['json']
parts=json.loads((O/'Diagnostics/foregrip_geometry.json').read_text());camera=ns['camera'];camera.data.type='ORTHO';camera.data.ortho_scale=.26
for ob in ns['groups']['props']+ns['groups']['guide']:ob.hide_render=True
for family in ('vertical','canted','prism','angled'):
 p=s['pose'](0,7,False,family)[0];ns['apply'](p);g=parts[family];turn=p['WPN_root']@s['rest']['WPN_root'].inverted()
 me=bpy.data.meshes.new(family);me.from_pydata([turn@Vector(v) for v in g['vertices']],[],g['faces']);ob=bpy.data.objects.new(family,me);scene.collection.objects.link(ob)
 mat=bpy.data.materials.new(family);mat.diffuse_color=(.12,.6,.3,1);me.materials.append(mat)
 h=p['hand_l'];target=h.translation
 for i,at in enumerate(((.15,0,.12),(-.15,0,.12),(0,.15,.05))):
  camera.location=h@Vector(at);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/'Diagnostics/Frames'/f'grip_{family}_{i}.png');bpy.ops.render.render(write_still=True)
 bpy.data.objects.remove(ob,do_unlink=True)
