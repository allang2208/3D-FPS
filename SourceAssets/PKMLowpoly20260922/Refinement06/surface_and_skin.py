"""PKM-only surface and forearm weight revision; preserve Manny mesh identity."""
import bpy,json,pathlib,math
from mathutils import Vector,Matrix
O=pathlib.Path(__file__).parent;R=O.parent
WOOD=R.parent/'AKMIntegration20260910/Redwood/Wood051'

def refine(r):
 report={'wood_source':str(WOOD),'wood_license':'ambientCG Wood051 CC0, existing AKM local source','parts':[],'wrist_weight_vertices':{}}
 mats={}
 for label in ['PKM_LaminatedWood','PKM_WoodGripPanel','PKM_BluedSteel','PKM_AmmoBoxPaint','PKM_InteriorSteel']:
  mat=bpy.data.materials.get(label)
  if not mat:continue
  mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear()
  out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs[0],out.inputs[0])
  uv=n.new('ShaderNodeTexCoord')
  if label=='PKM_LaminatedWood':
   maps={}
   for name in ['Color','NormalGL','Roughness']:
    t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(WOOD/f'Wood051_2K-JPG_{name}.jpg'),check_existing=True)
    if name!='Color':t.image.colorspace_settings.name='Non-Color'
    l.new(uv.outputs['UV'],t.inputs['Vector']);maps[name]=t
   tint=n.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[2].default_value=(1.05,.50,.26,1)
   l.new(maps['Color'].outputs['Color'],tint.inputs[1]);l.new(tint.outputs[0],bs.inputs['Base Color'])
   rough=n.new('ShaderNodeMath');rough.operation='MULTIPLY_ADD';rough.inputs[1].default_value=.22;rough.inputs[2].default_value=.30
   l.new(maps['Roughness'].outputs['Color'],rough.inputs[0]);l.new(rough.outputs[0],bs.inputs['Roughness'])
   normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.16;l.new(maps['NormalGL'].outputs[0],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
  else:
   # Same physical scale and finish family as current QBZ polymer author graph.
   polymer=label=='PKM_WoodGripPanel';metal='Steel' in label
   col=(.017,.019,.021) if polymer else (.035,.039,.044) if metal else (.047,.065,.025)
   bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Metallic'].default_value=1 if metal else 0
   noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=155 if polymer else 95;noise.inputs['Detail'].default_value=2
   l.new(uv.outputs['UV'],noise.inputs['Vector'])
   rough=n.new('ShaderNodeMath');rough.operation='MULTIPLY_ADD';rough.inputs[1].default_value=.06;rough.inputs[2].default_value=.53 if polymer else .40 if metal else .52
   l.new(noise.outputs['Fac'],rough.inputs[0]);l.new(rough.outputs[0],bs.inputs['Roughness'])
   bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16 if polymer else .08;bump.inputs['Distance'].default_value=.000012 if polymer else .000004
   l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
  mats[label]=mat
 # Bake the newly authored non-wood tiles for identical UE surface inputs.
 tex=O/'Textures';tex.mkdir(exist_ok=True);scene=bpy.context.scene
 scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.margin=0
 bpy.ops.mesh.primitive_plane_add(size=1,location=(0,0,5));plane=bpy.context.object
 for label,mat in mats.items():
  if label=='PKM_LaminatedWood':continue
  plane.data.materials.clear();plane.data.materials.append(mat);nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
  for channel in ['BaseColor','Roughness','Normal']:
   img=bpy.data.images.new(label+'06_'+channel,width=1024,height=1024,alpha=False);img.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
   target=nt.nodes.new('ShaderNodeTexImage');target.image=img;nt.nodes.active=target
   if channel=='Normal':nt.links.new(bs.outputs[0],out.inputs[0]);kind='NORMAL'
   else:
    emit=nt.nodes.new('ShaderNodeEmission');socket=bs.inputs['Base Color' if channel=='BaseColor' else 'Roughness']
    if socket.is_linked:nt.links.new(socket.links[0].from_socket,emit.inputs['Color'])
    else:emit.inputs['Color'].default_value=socket.default_value if channel=='BaseColor' else (socket.default_value,)*3+(1,)
    nt.links.new(emit.outputs[0],out.inputs[0]);kind='EMIT'
   bpy.ops.object.bake(type=kind,normal_space='TANGENT');img.filepath_raw=str(tex/(label+'_'+channel+'.png'));img.file_format='PNG';img.save()
  nt.links.new(bs.outputs[0],out.inputs[0])
 bpy.data.objects.remove(plane,do_unlink=True)
 inv=(r.data.bones['WPN_root'].matrix_local@Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])).inverted()
 for ob in list(scene.objects):
  if ob.type!='MESH' or 'mechanical_bone' not in ob:continue
  sid=ob.get('source_part_id',-1)
  if sid in [45,46]:
   ob.data.materials.clear();ob.data.materials.append(mats['PKM_WoodGripPanel'])
  # Source UVs were imported from constant-colour materials. Give wood metric,
  # grain-aligned projection on each dominant surface (one tile per 18 cm).
  if any(m and m.name=='PKM_LaminatedWood' for m in ob.data.materials):
   uv=ob.data.uv_layers.active or ob.data.uv_layers.new(name='WoodMetricUV')
   for p in ob.data.polygons:
    coords=[inv@ob.data.vertices[i].co for i in p.vertices]
    normal=(coords[1]-coords[0]).cross(coords[2]-coords[0]);axis=max(range(3),key=lambda j:abs(normal[j]))
    for li,v in zip(p.loop_indices,coords):
     uv.data[li].uv=(v.y/.18,(v.z if axis==0 else v.x)/.18)
  if sid in [42,43,44,45,46,47,50,58,62,63,64,134,135,136,137,138,139,140]:
   mods=[m for m in ob.modifiers if m.type=='BEVEL']
   bevel=mods[0] if mods else ob.modifiers.new('PKM06_CloseSurfaceBevel','BEVEL')
   bevel.width=.0005 if sid in [45,46,135,136] else .0003;bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(35);bevel.use_clamp_overlap=True;bevel.harden_normals=True
   normals=next((m for m in ob.modifiers if m.type=='WEIGHTED_NORMAL'),None) or ob.modifiers.new('PKM06_WeightedNormals','WEIGHTED_NORMAL');normals.keep_sharp=True
   report['parts'].append(ob.name)
 # Rebalance only existing forearm influences; retain hand/finger weights,
 # clothing regions and total influence mass. No topology/identity replacement.
 hands=bpy.data.objects['SK_Manny_Arms_Export']
 for side in ['l','r']:
  ns=['lowerarm_'+side,'lowerarm_twist_02_'+side,'lowerarm_twist_01_'+side];groups=[hands.vertex_groups[n] for n in ns]
  start=r.data.bones[ns[0]].head_local;end=r.data.bones['hand_'+side].head_local;axis=end-start
  count=0
  for v in hands.data.vertices:
   weights={g.group:g.weight for g in v.groups};mass=sum(weights.get(g.index,0) for g in groups)
   if mass<.015:continue
   t=max(0,min(1,(v.co-start).dot(axis)/axis.length_squared))
   if t<.32:continue
   f=max(0,min(1,(t-.25)/.65));wanted=[max(0,1-2*f),1-abs(2*f-1),max(0,2*f-1)]
   for g,w in zip(groups,wanted):g.add([v.index],mass*w,'REPLACE')
   count+=1
  report['wrist_weight_vertices'][side]=count
 (O/'surface_skin.json').write_text(json.dumps(report,indent=2))
