import bpy,pathlib,json
out=pathlib.Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(out/'source/hand-restored-textures.blend'),load_ui=False,use_scripts=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8
for o in bpy.data.objects:
 if o.type=='ARMATURE':o.data.pose_position='REST'
 if o.type=='MESH':
  o.hide_render=False;o.hide_viewport=False;o.hide_set(False)
  for m in o.modifiers:
   if m.type=='MULTIRES':m.levels=min(1,m.total_levels);m.render_levels=min(1,m.total_levels)
(out/'baked').mkdir(exist_ok=True)
report={}
for oi,obj in enumerate([o for o in bpy.data.objects if o.type=='MESH']):
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 if len(obj.data.vertices)>100:
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
 originals=list(obj.data.materials)
 for i,mat in enumerate(originals):obj.data.materials[i]=mat.copy()
 results={}
 for bake_type in ['DIFFUSE','NORMAL']:
  size=2048 if len(obj.data.vertices)>100 else 512
  im=bpy.data.images.new(f'donor_{oi}_{bake_type}',width=size,height=size,alpha=False)
  if bake_type=='NORMAL':im.colorspace_settings.name='Non-Color'
  for mat in obj.data.materials:
   n=mat.node_tree.nodes.new('ShaderNodeTexImage');n.image=im;mat.node_tree.nodes.active=n
  scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False;scene.render.bake.use_pass_color=True;scene.render.bake.margin=12
  bpy.ops.object.bake(type=bake_type)
  path=out/'baked'/f'donor_{oi}_{bake_type.lower()}.png';im.filepath_raw=str(path);im.file_format='PNG';im.save();results[bake_type]=path.name
 report[obj.name]=results
 for i,mat in enumerate(originals):obj.data.materials[i]=mat
(out/'bake-manifest.json').write_text(json.dumps(report,indent=2))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'source/hand-prepared.blend'))
print('BAKE_SOURCE_OK')
