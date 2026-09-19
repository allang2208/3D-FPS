"""Render current selected stock geometry in a shared, horizontal front-left projection."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix
P=Path(__file__).resolve().parent;O=P/'Icons';O.mkdir(exist_ok=True)
S=Path('D:/FPS3D/FPSGAME/SourceAssets')
entries={
 'false':(S/'M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend','M4_Stock Classic Unreal_Export'),
 'skeleton':(S/'ReferenceStock5080_20260912/DetailRefine/m4/Stock_Refined_Editable.blend','SM_SkeletonStock'),
 'qr_performance':(S/'MeshyPerformanceStock20260913/M4/PerformanceStock_Editable.blend','SM_PerformanceStock'),
 'core_stock':(S/'CoreStock20260914/Meshy0914005605/M4/CoreStock_Game_Editable.blend','SM_CoreStock'),
 'tactical_telescopic':(P/'TacticalTelescopic/M4/TacticalStock_Game_Editable.blend','SM_TacticalTelescopicStock')}
keys=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(entries)
for key in keys:
 path,name=entries[key];bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.preferences.filepaths.save_version=0
 ob=bpy.data.objects[name]
 if key=='false':
  rig=bpy.data.objects['SK_M4_Infima'];root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
  frame=Matrix.Rotation(-math.pi/2,4,'Z')@root.inverted()@ob.matrix_world
  ob.data=ob.data.copy();ob.data.transform(frame);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
  for m in list(ob.modifiers):
   if m.type=='ARMATURE':ob.modifiers.remove(m)
 for other in list(bpy.data.objects):
  if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
 ob.hide_render=False;ob.hide_set(False)
 pts=[ob.matrix_world@v.co for v in ob.data.vertices]
 lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)));hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
 center=(lo+hi)*.5;scale=2/(hi.x-lo.x)
 ob.matrix_world=Matrix.Scale(scale,4)@Matrix.Translation(-center)@ob.matrix_world
 scene=bpy.context.scene;scene.frame_set(0);scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
 scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
 scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8'
 scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.35
 scene.world=bpy.data.worlds.new('NeutralStockIconStudio');scene.world.use_nodes=True
 bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.36,.36,.36,1);bg.inputs[1].default_value=.55
 for loc,energy,size in [((-1.5,-3,3),700,4),((2,1.5,2.5),950,3),((-3,-1,-.5),180,2),((0,-4,.2),110,3)]:
  bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=energy;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
 bpy.ops.object.camera_add(location=(0,-5,0));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.36;scene.camera=cam
 scene.render.filepath=str(O/('stock_'+key+'.png'))
 bpy.data.orphans_purge(do_recursive=True);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/('stock_'+key+'.blend')))
 print('RENDER_STOCK_ICON',key,flush=True);bpy.ops.render.render(write_still=True)
 (O/('stock_'+key+'.json')).write_text(json.dumps({'source':str(path),'object':name,'front':'left (-X)','buttpad':'right (+X)','camera':'orthographic level side, up +Z, looking +Y','size':[1024,1024],'transparent':True,'actual_model_render':True,'runtime_tested':False},indent=2))
print('STOCK_ICON_RENDER_COMPLETE',flush=True)
