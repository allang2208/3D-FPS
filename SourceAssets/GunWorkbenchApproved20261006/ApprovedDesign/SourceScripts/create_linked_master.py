import bpy,pathlib,json
R=pathlib.Path(__file__).resolve().parents[1];F=R/'output/Delivery/GunWorkbenchDesign';bpy.ops.wm.read_factory_settings(use_empty=True)
for name in ['TableAndMat','Lamp','RetainedTools','NewProps','NewAmmo','SceneSetup']:
 with bpy.data.libraries.load(str(F/(name+'.blend')),link=True) as (src,dst):dst.objects=src.objects
 for o in dst.objects:bpy.context.scene.collection.objects.link(o)
s=bpy.context.scene;s.camera=next(o for o in s.objects if o.type=='CAMERA');s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.render.resolution_x=1800;s.render.resolution_y=1500;s.world=bpy.data.worlds.new('Studio World');s.world.color=(.15,.15,.15);s.view_settings.view_transform='AgX'
for lib in bpy.data.libraries:lib.filepath=bpy.path.relpath(lib.filepath,start=str(F))
bpy.ops.wm.save_as_mainfile(filepath=str(F/'GunWorkbench_Design_Master.blend'));bpy.ops.wm.open_mainfile(filepath=str(F/'GunWorkbench_Design_Master.blend'));bpy.context.view_layer.update();missing=[lib.filepath for lib in bpy.data.libraries if lib.is_missing];assert not missing;assert len(bpy.context.scene.objects)==343
(F/'portable_validation.json').write_text(json.dumps({'objects':len(bpy.context.scene.objects),'missing_libraries':missing,'library_count':len(bpy.data.libraries),'status':'linked master reopened successfully'},indent=2));print('PORTABLE_PASS',len(bpy.context.scene.objects))
