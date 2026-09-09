import bpy,json,pathlib
p=pathlib.Path(__file__).parent/'editable-v6'
report=[]
for source in sorted(p.glob('*.glb')):
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.gltf(filepath=str(source))
 bpy.ops.file.pack_all()
 target=source.with_suffix('.blend')
 bpy.ops.wm.save_as_mainfile(filepath=str(target))
 bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False,use_scripts=False)
 entry={'weapon':source.stem,'meshes':sum(o.type=='MESH' for o in bpy.data.objects),'rigs':sum(o.type=='ARMATURE' for o in bpy.data.objects),'actions':len(bpy.data.actions),'saved_reopened':True}
 assert entry['rigs']>0 and entry['actions']>0
 report.append(entry);print('EDITABLE_REOPEN_OK',entry)
(p/'editable-check.json').write_text(json.dumps(report,indent=2))
