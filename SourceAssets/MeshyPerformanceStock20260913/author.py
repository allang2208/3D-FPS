import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent;bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/'Imported.blend'));src=next(o for o in bpy.context.scene.objects if o.type=='MESH');src.data.transform(src.matrix_world);src.matrix_world=Matrix.Identity(4)
pts=[v.co.copy() for v in src.data.vertices];lo=min(v.x for v in pts);hi=max(v.x for v in pts);zlo=min(v.z for v in pts);zhi=max(v.z for v in pts)
# Source reference shows open tube on the short front end; pad spans the tall rear end.
rims=[[v for v in pts if abs(v.x-x)<(hi-lo)*.025] for x in [lo,hi]]
front_hi=(max(v.z for v in rims[1])-min(v.z for v in rims[1]))<(max(v.z for v in rims[0])-min(v.z for v in rims[0]))
rim=rims[int(front_hi)];rim=[v for v in rim if v.z>zlo+(zhi-zlo)*.6]
origin=Vector((hi if front_hi else lo,(min(v.y for v in rim)+max(v.y for v in rim))/2,(min(v.z for v in rim)+max(v.z for v in rim))/2))
rot=Matrix.Rotation(math.pi if front_hi else 0,4,'Z');scale=.18/(hi-lo)
for v in src.data.vertices:v.co=rot@(v.co-origin)*scale
src.data.update();src.data.uv_layers[0].name='GeneratedUV0';canonical=src.data.copy();src.hide_render=True;src.hide_set(True)
tex=P/'Textures';tex.mkdir(exist_ok=True)
import shutil
base=next(f for f in (P/'Source').glob('*.png') if not any(f.stem.endswith('_'+x) for x in ['normal','roughness','metallic','emission']))
files={'BaseColor':base,'Normal':next((P/'Source').glob('*_normal.png')),'Roughness':next((P/'Source').glob('*_roughness.png')),'Metallic':next((P/'Source').glob('*_metallic.png'))}
images={}
for key,f in files.items():
 shutil.copy2(f,tex/(key+'.png'));im=bpy.data.images.load(str(tex/(key+'.png')),check_existing=True);im.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color';images[key]=im
im=images['Metallic'];w,h=im.size;pixels=np.array(im.pixels[:],dtype=np.float32).reshape(h,w,4);labels=[]
for f in canonical.polygons:
 uv=sum((canonical.uv_layers[0].data[i].uv for i in f.loop_indices),Vector((0.,0.)))/len(f.loop_indices);val=pixels[min(h-1,max(0,int(uv.y*h))),min(w-1,max(0,int(uv.x*w))),0];x=sum(canonical.vertices[i].co.x for i in f.vertices)/len(f.vertices);labels.append(2 if x>.168 else 0 if val>.35 else 1)
report={'source_front_x_max':front_hi,'source_mount_center':list(origin),'length_m':.18,'variants':{}}
def active(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
for family in ['M4','AKM','QBZ191']:
 ob=bpy.data.objects.new('SM_PerformanceStock',canonical.copy());bpy.context.collection.objects.link(ob);ob.data.materials.clear()
 for kind in ['Metal','Polymer','Rubber']:
  m=bpy.data.materials.new('Stock'+kind+'_'+family);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.025,.029,.032,1);bs.inputs['Metallic'].default_value=.8 if kind=='Metal' else 0.;bs.inputs['Roughness'].default_value=.38 if kind=='Metal' else .65 if kind=='Polymer' else .85
  uv=n.new('ShaderNodeUVMap');uv.uv_map='GeneratedUV0'
  for key in ['BaseColor','Normal','Roughness']:
   if kind=='Metal' and key!='Normal':continue
   t=n.new('ShaderNodeTexImage');t.image=images[key];l.new(uv.outputs['UV'],t.inputs['Vector'])
   if key=='Normal':nm=n.new('ShaderNodeNormalMap');nm.uv_map='GeneratedUV0';l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],bs.inputs['Normal'])
   elif key=='BaseColor':l.new(t.outputs['Color'],bs.inputs['Base Color'])
   elif kind!='Rubber':l.new(t.outputs['Color'],bs.inputs['Roughness'])
  ob.data.materials.append(m)
 for f,label in zip(ob.data.polygons,labels):f.material_index=label
 front=.007 if family=='M4' else .0028 if family=='AKM' else 0.;ob.data.transform(Matrix.Translation((front,0,0)))
 parts=[]
 def cube(name,loc,size):
  bpy.ops.mesh.primitive_cube_add(size=1,location=loc);a=bpy.context.object;a.name=name;a.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);a.data.materials.append(ob.data.materials[0]);parts.append(a);return a
 if family=='AKM':
  a=cube('AKM_receiver_adapter',(.0016,0,-.0025),(.005,.041,.038));bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.0135,depth=.015,location=(.0016,0,0),rotation=(0,math.pi/2,0));cut=bpy.context.object;active(a);mod=a.modifiers.new('Tube passage','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
 if family=='QBZ191':
  ob.data.transform(Matrix.Translation((.000688,.065,.0615))@Matrix.Rotation(math.pi/2,4,'Z'))
  cube('QBZ_receiver_adapter',(.000688,.0585,.0615),(.034,.014,.042));cube('QBZ_adapter_shoulder',(.000688,.0645,.0615),(.029,.006,.033))
 for a in parts:
  active(a);mod=a.modifiers.new('Adapter edge','BEVEL');mod.width=.0005;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
  if not a.data.uv_layers:a.data.uv_layers.new(name='GeneratedUV0')
  for f in a.data.polygons:
   axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
   for li in f.loop_indices:
    co=a.data.vertices[a.data.loops[li].vertex_index].co;a.data.uv_layers[0].data[li].uv=(co[axes[0]]/.1,co[axes[1]]/.1)
 # Use separate adapter material to avoid sampling generated structural normals on new geometry.
 if parts:
  am=ob.data.materials[0].copy();am.name='StockAdapter_'+family;bs=next(n for n in am.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  for link in list(bs.inputs['Normal'].links):am.node_tree.links.remove(link)
  for a in parts:
   a.data.materials.clear();a.data.materials.append(am)
   for f in a.data.polygons:f.material_index=0
   bm=bmesh.new();bm.from_mesh(a.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(a.data);bm.free()
  active(ob)
  for a in parts:a.select_set(True)
  bpy.ops.object.join()
 uv=ob.data.uv_layers.new(name='ReceiverUV1');tile={'M4':(.12,.05),'AKM':(.12,.025),'QBZ191':(.1,.1)}[family]
 for f in ob.data.polygons:
  axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
  for li in f.loop_indices:
   co=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]/tile[0],co[axes[1]]/tile[1])
 ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True;active(ob);out=P/family;out.mkdir(exist_ok=True);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'PerformanceStock_Editable.blend'));bpy.ops.export_scene.fbx(filepath=str(out/'SM_PerformanceStock.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 report['variants'][family]={'triangles':sum(len(f.vertices)-2 for f in ob.data.polygons),'front_offset_m':front,'materials':[m.name if m else 'None' for m in ob.data.materials]};bpy.data.objects.remove(ob,do_unlink=True)
(P/'authoring.json').write_text(json.dumps(report,indent=2))
