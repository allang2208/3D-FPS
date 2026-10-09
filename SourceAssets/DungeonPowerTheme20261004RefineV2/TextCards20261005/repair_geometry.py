"""Replace only text plate shells in preserved FBX; retain all other geometry and UCX."""
import bpy,json,sys,hashlib
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
import numpy as np
ROOT=Path(__file__).resolve().parent;SOURCE=ROOT.parent;PROJECT=ROOT.parents[2]
sys.path.insert(0,str(SOURCE/'Scripts'))
from geometry import basis
BASE='/Game/Dungeons/PowerTheme20261004/TextCards20261005'
cards=json.loads((ROOT/'cards.json').read_text('utf8'));by=defaultdict(list)
for c in cards:by[c['mesh']].append(c)
manifest=json.loads((SOURCE/'Authored/manifest.json').read_text('utf8'))
old={x['name']:x for x in manifest['objects']}
shared={
 'SM_Facility_PowerCabinet':('DungeonFacilityPropPolish20260928/Authored','/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_PowerCabinet'),
 'SM_Archive_ServerRack_V1':('DungeonDataArchive20260930/Equipment20260930/Authored','/Game/Dungeons/DataArchive20260930/EquipmentV1/Meshes/SM_Archive_ServerRack_V1')}
records=[]
for name,plates in by.items():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
 source=(PROJECT/'SourceAssets'/shared[name][0] if name in shared else SOURCE/'Authored')/(name+'.fbx')
 bpy.ops.import_scene.fbx(filepath=str(source))
 obj=bpy.data.objects.get(name)
 if not obj:raise RuntimeError('Source mesh missing '+name)
 mesh=obj.data;inv=obj.matrix_world.inverted()
 pos=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',pos);pos=pos.reshape(-1,3)
 world=pos@np.array(obj.matrix_world.to_3x3()).T+np.array(obj.matrix_world.translation)
 loops=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',loops)
 starts=np.empty(len(mesh.polygons),dtype=np.int32);mesh.polygons.foreach_get('loop_start',starts)
 remove=np.zeros(len(mesh.polygons),dtype=bool);plate_counts=[]
 for c in plates:
  n,u,v=basis(c['normal']);rel=world-np.array(c['center']);nx=rel@np.array(n);ux=rel@np.array(u);vx=rel@np.array(v)
  inside=(abs(ux)<=c['width']/2+c['old_margin']+1e-5)&(abs(vx)<=c['height']/2+c['old_margin']+1e-5)&(nx>=-c['old_depth']-1e-5)&(nx<=c['old_front']+1e-5)
  faces=np.logical_and.reduceat(inside[loops],starts)
  count=int(faces.sum())
  if count<4:raise RuntimeError('Original plate shell was not located: '+c['id'])
  remove|=faces;plate_counts.append(dict(id=c['id'],removed_faces=count))
 verts=[tuple(p) for p in pos];faces=[];uvs=[];normals=[];mats=[];smooth=[];colors=[]
 olduv=mesh.uv_layers[0].data;oldnorm=mesh.corner_normals
 age=mesh.color_attributes.get('ServiceAge')
 for f in mesh.polygons:
  if remove[f.index]:continue
  faces.append(tuple(f.vertices));mats.append(f.material_index);smooth.append(f.use_smooth)
  for li in f.loop_indices:
   uvs.append(tuple(olduv[li].uv));normals.append(tuple(oldnorm[li].vector))
   colors.append(tuple(age.data[li].color) if age and age.domain=='CORNER' else (.04,0,0,1))
 materials=list(mesh.materials)
 # Existing material indices remain stable so actor-level Chinese overlays survive.
 text=bpy.data.materials.new('PW_TextCards20261005');text.use_nodes=True
 tex=text.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'Authored/T_Power_TextCards.png'))
 text.node_tree.links.new(tex.outputs['Color'],text.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
 text.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.78
 text['ue_material_path']=BASE+'/Materials/M_Power_TextCards';materials.append(text);label_idx=len(materials)-1
 steel_idx=next((i for i,m in enumerate(materials) if m.name=='PW_Steel'),0)
 # Shared-atlas back/rim uses a constant steel swatch, never a stretched text cell.
 rim_uv=(.875,.75) if name=='SM_Facility_PowerCabinet' else (.1,.9)
 def face(points,material,uv=None):
  local=[inv@p for p in points];offset=len(verts);verts.extend(tuple(p) for p in local)
  faces.append(tuple(range(offset,offset+len(local))));mats.append(material);smooth.append(False)
  normal=(local[1]-local[0]).cross(local[2]-local[0]).normalized()
  metal_uv=[(rim_uv[0]+dx*.001,rim_uv[1]+dy*.001) for dx,dy in [(-1,-1),(1,-1),(1,1),(-1,1)]]
  uvs.extend(uv if uv else metal_uv);normals.extend([tuple(normal)]*len(local));colors.extend([(.04,0,0,1)]*len(local))
 for c in plates:
  center=Vector(c['center']);n,u,v=basis(c['normal']);w=c['width'];h=c['height'];border=.0035 if name.endswith('Refined') else .0015
  outer=[center+u*x*(w/2+border)+v*y*(h/2+border) for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
  inner=[center+u*x*w/2+v*y*h/2 for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
  back=[p-n*c['depth'] for p in outer]
  face(list(reversed(back)),steel_idx)
  for i in range(4):
   j=(i+1)%4
   face([back[i],back[j],outer[j],outer[i]],steel_idx)
   face([outer[i],outer[j],inner[j],inner[i]],steel_idx)
  x0,y0,x1,y1=c['rect'];face(inner,label_idx,[(x0/4096,1-y1/4096),(x1/4096,1-y1/4096),(x1/4096,1-y0/4096),(x0/4096,1-y0/4096)])
 new=bpy.data.meshes.new(name+'_TextCards');new.from_pydata(verts,[],faces);new.update()
 for m in materials:new.materials.append(m)
 new.polygons.foreach_set('material_index',mats);new.polygons.foreach_set('use_smooth',smooth)
 uv=new.uv_layers.new(name='UVMap');uv.data.foreach_set('uv',np.asarray(uvs,dtype=np.float32).ravel())
 ca=new.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER');ca.data.foreach_set('color',np.asarray(colors,dtype=np.float32).ravel())
 new.update();new.normals_split_custom_set(normals);new.update();obj.data=new
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 collision=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('UCX_')]
 for o in collision:o.select_set(True)
 target=ROOT/'Authored'/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(target),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
 previous=shared[name][1] if name in shared else '/Game/Dungeons/PowerTheme20261004/RefineV2/Meshes/'+name
 records.append(dict(name=name,source=str(source),previous_mesh=previous,mesh=BASE+'/Meshes/'+name,fbx=str(target),
   sha256=hashlib.sha256(target.read_bytes()).hexdigest(),plates=len(plates),replaced_faces=int(remove.sum()),details=plate_counts,
   text_slot=label_idx,collision_hulls=len(collision),nanite=old.get(name,{}).get('nanite',True)))
 # Editable source keeps original UCX, pivots, all untouched geometry and its normals.
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored'/(name+'.blend')))
 print('POWER_TEXT_MESH_AUTHORED',name,len(plates),int(remove.sum()),flush=True)
(ROOT/'manifest.json').write_text(json.dumps(dict(base=BASE,meshes=records,texture=str(ROOT/'Authored/T_Power_TextCards.png'),tests_run=False,rendered=False),indent=2),encoding='utf8')
