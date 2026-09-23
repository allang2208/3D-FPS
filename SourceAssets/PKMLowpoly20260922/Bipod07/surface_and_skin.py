"""Adapt the installed QBZ-191 coating to PKM-owned UVs and split its bipod."""
import bpy,json,ast,textwrap,math,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;R=O.parent;S=R.parent
BIPOD={65,72,127,128,129}

def refine(r):
 # Preserve the preceding wood, polymer, bevel and forearm-weight authoring.
 ns={'__file__':str(O/'surface_and_skin.py')}
 exec(compile((R/'Refinement06/surface_and_skin.py').read_text(),str(R/'Refinement06/surface_and_skin.py'),'exec'),ns)
 ns['refine'](r)
 scene=bpy.context.scene;r.data.pose_position='REST';bpy.context.view_layer.update()
 metal=[o for o in scene.objects if o.type=='MESH' and 'mechanical_bone' in o and any(m and m.name in ['PKM_BluedSteel','PKM_InteriorSteel','PKM_AmmoBoxPaint'] for m in o.data.materials)]
 groups={'Body':[o for o in metal if not o.name.startswith('New_') and not any(m.name=='PKM_InteriorSteel' for m in o.data.materials)],'Steel':[o for o in metal if not o.name.startswith('New_') and any(m.name=='PKM_InteriorSteel' for m in o.data.materials)]}
 source=ast.parse((S/'QBZ191Hero20260913/build.py').read_text())
 fn=next(x for x in source.body if isinstance(x,ast.FunctionDef) and x.name=='material')
 env={'bpy':bpy};exec(compile(ast.Module(body=[fn],type_ignores=[]),'QBZ191_Hero_material','exec'),env)
 scene.render.engine='CYCLES';scene.cycles.samples=8
 scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=False;scene.render.bake.margin=12
 scene.render.bake.normal_space='TANGENT';scene.render.bake.normal_r='POS_X';scene.render.bake.normal_g='POS_Y';scene.render.bake.normal_b='POS_Z'
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for d in prefs.devices:d.use=d.type=='OPTIX'
 if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
 report={'live_source':json.loads((O/'qbz_live_materials.json').read_text())['mesh'],'bipod_source_parts':sorted(BIPOD),'groups':{}}
 for group,objects in groups.items():
  if not objects:continue
  base,metallic,roughness=((.025,.029,.033),.72,.30) if group=='Body' else ((.020,.023,.027),.88,.25)
  mat=env['material']('AUTH_PKM_QBZ_'+group,base,metallic,roughness)
  n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');out=next(x for x in n if x.type=='OUTPUT_MATERIAL')
  # Generate in source meters, independent of rig/world position.
  coords=bpy.data.objects.new('PKM_SurfaceMeters_'+group,None);scene.collection.objects.link(coords)
  coords.matrix_world=r.data.bones['WPN_root'].matrix_local@Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
  value=n.new('ShaderNodeValue');value.outputs[0].default_value=metallic
  env2={'bpy':bpy,'n':n,'l':l,'bs':bs,'group':group,'base':bs.inputs['Base Color'].links[0].from_socket,'rough':bs.inputs['Roughness'].links[0].from_socket,'normal':bs.inputs['Normal'].links[0].from_socket,'metal':value.outputs[0]}
  wear=(S/'QBZ191ContactWear20260913/wear.py').read_text()
  exec(textwrap.dedent(wear[wear.index(' def mathnode'):wear.index(' emit=n.new')]),env2)
  for node in n:
   if node.type=='TEX_COORD':node.object=coords
  bpy.ops.object.select_all(action='DESELECT')
  for ob in objects:
   ob.hide_set(False);ob.hide_render=False;ob.select_set(True)
   # Material atlas is private to this geometry; keep UV0 for every UE input.
   ob.data=ob.data.copy()
   for uv in list(ob.data.uv_layers):ob.data.uv_layers.remove(uv)
   ob.data.uv_layers.new(name='PKM_QBZ_SurfaceUV')
   ob.data.materials.clear();ob.data.materials.append(mat)
   for p in ob.data.polygons:p.material_index=0
  bpy.context.view_layer.objects.active=objects[-1]
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.006,area_weight=.2,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
  # One temporary evaluated assembly avoids recompiling Cycles once per small bolt.
  bpy.ops.object.select_all(action='DESELECT');copies=[];deps=bpy.context.evaluated_depsgraph_get()
  for ob in objects:
   me=bpy.data.meshes.new_from_object(ob.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
   copy=bpy.data.objects.new('PKM_BakeSurface',me);scene.collection.objects.link(copy);copy.matrix_world=ob.matrix_world.copy();copy.select_set(True);copies.append(copy)
  bpy.context.view_layer.objects.active=copies[-1];bpy.ops.object.join();baker=bpy.context.object
  baker.data.materials.clear();baker.data.materials.append(mat)
  for p in baker.data.polygons:p.material_index=0
  # Bakes include receiver-local edge wear and microscopic finish, not QBZ engravings.
  emit=n.new('ShaderNodeEmission');target=n.new('ShaderNodeTexImage');n.active=target
  maps={};size=4096 if group=='Body' else 1024
  for channel,socket in [('BaseColor',env2['color']),('ORM',env2['orm'].outputs[0]),('Normal',None)]:
   im=bpy.data.images.new('T_PKM_QBZ_'+group+'_'+channel,width=size,height=size,alpha=False)
   im.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';target.image=im
   if socket:l.new(socket,emit.inputs['Color']);l.new(emit.outputs[0],out.inputs['Surface'])
   else:l.new(bs.outputs[0],out.inputs['Surface'])
   bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'EMIT')
   im.filepath_raw=str(O/'Textures'/(im.name+'.png'));im.file_format='PNG';im.save();maps[channel]=im
   print('PKM07_QBZ_BAKE',group,channel,flush=True)
  l.new(bs.outputs[0],out.inputs['Surface']);target.image=None
  bpy.data.objects.remove(baker,do_unlink=True)
  # The source preview reads the same baked inputs as the UE graph clone.
  run=bpy.data.materials.new('PKM_QBZ_'+group);run.use_nodes=True;rn=run.node_tree.nodes;rl=run.node_tree.links
  shader=rn.get('Principled BSDF');texs={}
  for channel,im in maps.items():
   t=rn.new('ShaderNodeTexImage');t.image=im;texs[channel]=t
  sep=rn.new('ShaderNodeSeparateColor');rl.new(texs['ORM'].outputs[0],sep.inputs[0]);rl.new(sep.outputs[2],shader.inputs['Metallic'])
  def mathnode(op,a,b):
   node=rn.new('ShaderNodeMath');node.operation=op
   for i,v in enumerate([a,b]):
    if isinstance(v,(int,float)):node.inputs[i].default_value=v
    else:rl.new(v,node.inputs[i])
   return node.outputs[0]
  # Match the installed Unified material's luminance mask and final roughness.
  rgb=rn.new('ShaderNodeSeparateColor');rl.new(texs['BaseColor'].outputs[0],rgb.inputs[0])
  lum=mathnode('ADD',mathnode('ADD',mathnode('MULTIPLY',rgb.outputs[0],.3),mathnode('MULTIPLY',rgb.outputs[1],.59)),mathnode('MULTIPLY',rgb.outputs[2],.11))
  def smoothstep(lo,hi):
   x=mathnode('MINIMUM',mathnode('MAXIMUM',mathnode('DIVIDE',mathnode('SUBTRACT',lum,lo),hi-lo),0),1)
   return mathnode('MULTIPLY',mathnode('MULTIPLY',x,x),mathnode('SUBTRACT',3,mathnode('MULTIPLY',x,2)))
  mask=mathnode('MULTIPLY',mathnode('MULTIPLY',smoothstep(.005,.024),mathnode('SUBTRACT',1,smoothstep(.15,.40))),.32)
  tint=rn.new('ShaderNodeMixRGB');rl.new(mask,tint.inputs[0]);rl.new(texs['BaseColor'].outputs[0],tint.inputs[1]);tint.inputs[2].default_value=(.025,.029,.032,1);rl.new(tint.outputs[0],shader.inputs['Base Color'])
  rl.new(mathnode('ADD',mathnode('MULTIPLY',sep.outputs[1],.62),.42*.38),shader.inputs['Roughness'])
  normal=rn.new('ShaderNodeNormalMap');normal.uv_map='PKM_QBZ_SurfaceUV';rl.new(texs['Normal'].outputs[0],normal.inputs['Color']);rl.new(normal.outputs[0],shader.inputs['Normal'])
  for ob in objects:
   ob.data.materials.clear();ob.data.materials.append(run)
   twin=bpy.data.objects.get('New_'+ob.name)
   if twin:
    # Preserve duplicate topology and rigid bone weights, copy only its surface UV.
    for uv in list(twin.data.uv_layers):twin.data.uv_layers.remove(uv)
    uv=twin.data.uv_layers.new(name='PKM_QBZ_SurfaceUV')
    for a,b in zip(uv.data,ob.data.uv_layers.active.data):a.uv=b.uv
    twin.data.materials.clear();twin.data.materials.append(run)
  report['groups'][group]={'material':run.name,'size':size,'textures':{k:v.filepath_raw for k,v in maps.items()},'objects':[ob.name for ob in objects]}
 # Export bipod in the SAME component bind frame as SK_PKM_Manny. Runtime
 # cancels WPN_root's reference transform before following its animated socket.
 bipod=[ob for ob in scene.objects if ob.type=='MESH' and ob.get('source_part_id') in BIPOD]
 bpy.ops.object.select_all(action='DESELECT')
 for ob in bipod:
  ob.select_set(True);ob.hide_set(False)
  for mod in list(ob.modifiers):
   if mod.type=='ARMATURE':ob.modifiers.remove(mod)
  world=ob.matrix_world.copy();ob.parent=None;ob.matrix_world=world
  ob['attachment_id']='pkm_bipod';del ob['mechanical_bone']
 bpy.context.view_layer.objects.active=bipod[0]
 bpy.ops.export_scene.fbx(filepath=str(O/'Exports/SM_PKM_Bipod.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True)
 for ob in bipod:
  mod=ob.modifiers.new('PKM_Bipod_SourcePose','ARMATURE');mod.object=r
  ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
  ob.hide_render=True;ob.hide_set(True)
 report['bipod_export']='Exports/SM_PKM_Bipod.fbx'
 r.data.pose_position='POSE'
 (O/'surface_manifest.json').write_text(json.dumps(report,indent=2))
