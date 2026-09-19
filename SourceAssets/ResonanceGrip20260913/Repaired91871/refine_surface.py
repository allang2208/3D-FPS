import bpy,bmesh,json,numpy as np
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/SourceAssets/ResonanceGrip20260913/Repaired91871/Game');P.mkdir(exist_ok=True)
I=P.parent/'Integration';report={};bpy.context.preferences.filepaths.save_version=0
for family in ['M4','AKM','QBZ191']:
 bpy.ops.wm.open_mainfile(filepath=str(I/family/'ResonanceGrip_Editable.blend'))
 ob=bpy.data.objects['SM_ResonanceGrip'];me=ob.data;mat=me.materials[0]
 images=[n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE'];packed=next(im for im in images if 'MetalRough' in im.filepath)
 w,h=packed.size;pixels=np.array(packed.pixels[:],dtype=np.float32).reshape(h,w,4)
 uv=me.uv_layers[0];metal=[]
 for f in me.polygons:
  coord=sum((uv.data[i].uv for i in f.loop_indices),__import__('mathutils').Vector((0.,0.)))/len(f.loop_indices)
  metal.append(float(pixels[min(h-1,max(0,int(coord.y*h))),min(w-1,max(0,int(coord.x*w))),2]))
 # Semantic material assignment with face adjacency regularization, not per-pixel noisy blending.
 labels=np.array(metal)>.28
 for f in me.polygons:
  if f.material_index>0:labels[f.index]=True
 edges={};neighbors=[set() for f in me.polygons]
 vertex_keys=[tuple(round(c,6) for c in v.co) for v in me.vertices]
 for f in me.polygons:
  for e in f.edge_keys:edges.setdefault(tuple(sorted((vertex_keys[e[0]],vertex_keys[e[1]]))),[]).append(f.index)
 for fs in edges.values():
  if len(fs)==2:a,b=fs;neighbors[a].add(b);neighbors[b].add(a)
 for _ in range(5):
  prev=labels.copy()
  for f,ns in enumerate(neighbors):
   if ns and sum(prev[i] for i in ns)==len(ns):labels[f]=True
   elif ns and not any(prev[i] for i in ns):labels[f]=False
 seen=set()
 for i in range(len(labels)):
  if i in seen:continue
  group=[];todo=[i];seen.add(i)
  while todo:
   j=todo.pop();group.append(j)
   for k in neighbors[j]:
    if k not in seen and labels[k]==labels[i]:seen.add(k);todo.append(k)
  if len(group)<300:
   boundary=[k for j in group for k in neighbors[j] if labels[k]!=labels[i]]
   if boundary:
    replacement=sum(labels[k] for k in boundary)>len(boundary)/2
    for j in group:labels[j]=replacement
 metalmat=bpy.data.materials.new('Resonance_Metal_'+family);metalmat.use_nodes=True;bs=next(n for n in metalmat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.025,.029,.032,1);bs.inputs['Metallic'].default_value=.8;bs.inputs['Roughness'].default_value=.38
 poly=bpy.data.materials.new('Resonance_Polymer');poly.use_nodes=True;bs=next(n for n in poly.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.014,.016,.018,1);bs.inputs['Roughness'].default_value=.64
 n=poly.node_tree.nodes;l=poly.node_tree.links;tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=650;tex.inputs['Detail'].default_value=2
 coords=n.new('ShaderNodeTexCoord');l.new(coords.outputs['Object'],tex.inputs['Vector']);bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.00004;l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
 me.materials.clear();me.materials.append(metalmat);me.materials.append(poly)
 for f,flag in zip(me.polygons,labels):f.material_index=0 if flag else 1
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 folder=P/family;folder.mkdir(exist_ok=True)
 bpy.ops.export_scene.fbx(filepath=str(folder/'SM_ResonanceGrip.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(folder/'ResonanceGrip_Surface_Editable.blend'))
 report[family]={'metal_faces':int(labels.sum()),'polymer_faces':int((~labels).sum()),'geometry':'preserved','material_region_source':'GLTF metallic channel plus mesh adjacency cleanup; no pixel crossfade'}
(P/'surface_regions.json').write_text(json.dumps(report,indent=2))

