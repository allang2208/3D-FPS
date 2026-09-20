"""Production UI assets only: M16-specific silhouettes, no review renders."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parent;out=O/'Icons';out.mkdir(exist_ok=True)
jobs={'magazine_false':'Magazine','stock_false':'Stock','reargrip_false':'PistolGrip','underbarrel_false':'Handguard','muzzle_false':'Muzzle','optic_false':'Receiver','magazine_ext_mag':'ext_mag'}
report={}
for key,part in jobs.items():
 bpy.ops.wm.open_mainfile(filepath=str(S/'M16Gameplay20260919/M16_Manny_Editable.blend'));bpy.context.preferences.filepaths.save_version=0
 r=bpy.data.objects['SK_M4_Infima'];R=r.data.bones['WPN_root'].matrix_local.copy()
 if part=='ext_mag':
  before=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Meshes/SM_M16_ext_mag.fbx'))
  ob=next(o for o in bpy.context.scene.objects if o not in before and o.type=='MESH')
 else:ob=bpy.data.objects['M16A2_'+part]
 ob.data=ob.data.copy();ob.data.transform(Matrix.Rotation(-math.pi/2,4,'Z')@R.inverted()@ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
 if part=='Receiver':
  # Only the fixed carry-handle rear sight, no front sight/barrel/receiver.
  bm=bmesh.new();bm.from_mesh(ob.data);remove=[v for v in bm.verts if v.co.z<.134 or v.co.x<-.204]
  bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(ob.data);bm.free()
 for other in list(bpy.data.objects):
  if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
 ob.hide_render=False;ob.hide_set(False)
 m=bpy.data.materials.new('M16_PBR_Icon');m.use_nodes=True;n=m.node_tree.nodes;links=m.node_tree.links;n.clear();bs=n.new('ShaderNodeBsdfPrincipled');output=n.new('ShaderNodeOutputMaterial');links.new(bs.outputs['BSDF'],output.inputs['Surface'])
 for kind,target in [('BaseColor','Base Color'),('Metallic','Metallic'),('Roughness','Roughness'),('Normal','Normal')]:
  im=bpy.data.images.load(str(S/'M16A2Migration20260919/Textures'/('m16a2_'+kind+'.png')),check_existing=False);im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';tex=n.new('ShaderNodeTexImage');tex.image=im
  if kind=='Normal':
   norm=n.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],norm.inputs['Color']);links.new(norm.outputs['Normal'],bs.inputs[target])
  else:links.new(tex.outputs['Color'],bs.inputs[target])
 ob.data.materials.clear();ob.data.materials.append(m)
 pts=[v.co for v in ob.data.vertices];lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
 scale=2/max(hi.x-lo.x,hi.z-lo.z);ob.matrix_world=Matrix.Scale(scale,4)@Matrix.Translation(-(lo+hi)*.5)
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for device in prefs.devices:device.use=device.type=='OPTIX'
 scene.cycles.device='GPU'
 scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100;scene.render.film_transparent=True
 scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.35
 scene.world=bpy.data.worlds.new('M16 icon studio');scene.world.use_nodes=True;bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.36,.36,.36,1);bg.inputs[1].default_value=.55
 for loc,energy,size in [((-1.5,-3,3),700,4),((2,1.5,2.5),950,3),((-3,-1,-.5),180,2),((0,-4,.2),110,3)]:
  bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=energy;l.data.shape='DISK';l.data.size=size;l.rotation_euler=(-l.location).to_track_quat('-Z','Y').to_euler()
 bpy.ops.object.camera_add(location=(0,-5,0));cam=bpy.context.object;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.38;scene.camera=cam
 name='ue_m16a2_'+key;scene.render.filepath=str(out/(name+'.png'));bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/(name+'.blend')));bpy.ops.render.render(write_still=True)
 report[name]={'source':'SM_M16_ext_mag' if part=='ext_mag' else 'M16A2_'+part,'front':'-X left','up':'+Z','size':[1024,1024],'purpose':'production UI icon','testing':'Not run'}
 (out/'manifest.json').write_text(json.dumps(report,indent=2));print('M16_ICON_AUTHORED',name,flush=True)
