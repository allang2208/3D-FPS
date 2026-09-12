"""Author game-ready QR variants from the actual 5080 textured master.
No validation render or game test is launched by this production script.
"""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent;OLD=P.parent/'SkeletonStock20260912';parts=[]
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def export(o,key):
 out=P/key.upper();out.mkdir(exist_ok=True);active(o);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'QRPerformanceStock_Editable.blend'))
 mod=o.modifiers.new('FBX triangles','TRIANGULATE');mod.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 bpy.ops.export_scene.fbx(filepath=str(out/'SM_QRPerformanceStock.fbx'),use_selection=True,object_types={'MESH'},global_scale=.01,axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
def flat(name,color,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;return m
def metal(key):
 if key=='m4':
  with bpy.data.libraries.load(str(OLD/'m4_fit_reference.blend'),link=False) as (a,b):b.materials=['Body.001']
  m=b.materials[0].copy()
 else:
  m=flat('AKM_receiver',(.035,.038,.042),.55);nt=m.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');root=P.parent/'AKMSoviet20260911/Source/ak47fbx_extracted/textures'
  for label,socket in [('Base_color','Base Color'),('Metallic','Metallic'),('Roughness','Roughness'),('Normal_OpenGL','Normal')]:
   im=bpy.data.images.load(str(root/('AK_'+label+'.png')),check_existing=True);n=nt.nodes.new('ShaderNodeTexImage');n.image=im
   if label!='Base_color':im.colorspace_settings.name='Non-Color'
   if socket=='Normal':v=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(n.outputs['Color'],v.inputs['Color']);nt.links.new(v.outputs['Normal'],bs.inputs[socket])
   else:nt.links.new(n.outputs['Color'],bs.inputs[socket])
 m.name='StockMetal';return m
def cube(name,loc,size,mat):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);return o
def adapter(mat):
 o=cube('AKM_receiver_adapter',(.16,0,-.25),(.5,4.1,3.8),mat)
 bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=1.35,depth=1.5,location=(.16,0,0),rotation=(0,math.pi/2,0));cut=bpy.context.object;active(o);m=o.modifiers.new('Tube passage','BOOLEAN');m.operation='DIFFERENCE';m.object=cut;bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cut,do_unlink=True)
 m=o.modifiers.new('Edge radius','BEVEL');m.width=.055;m.segments=3;bpy.ops.object.modifier_apply(modifier=m.name)
 for f in o.data.polygons:f.use_smooth=True
 m=o.modifiers.new('Face normals','WEIGHTED_NORMAL');bpy.ops.object.modifier_apply(modifier=m.name);active(o);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);return o
def map_metal(o,key):
 # UV1 is the generated unwrap; UV0 samples only a known receiver steel island.
 if o.data.uv_layers:o.data.uv_layers[0].name='GeneratedUV1'
 else:o.data.uv_layers.new(name='GeneratedUV1')
 if key=='akm':
  bm=bmesh.new();bm.from_mesh(o.data)
  for axis,step in [(0,12.0),(1,2.5),(2,2.5)]:
   low=min(v.co[axis] for v in bm.verts);high=max(v.co[axis] for v in bm.verts)
   for i in range(math.floor(low/step)+1,math.ceil(high/step)):
    co=[0,0,0];co[axis]=i*step;n=[0,0,0];n[axis]=1;bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=co,plane_no=n)
  bm.to_mesh(o.data);bm.free()
 uv=o.data.uv_layers.new(name='ReceiverUV');box=(.54,.73,.655,.85) if key=='m4' else (.055,.053,.285,.092)
 for f in o.data.polygons:
  dominant=max(range(3),key=lambda j:abs(f.normal[j]));ua=2 if dominant==0 else 0;va=2 if dominant==1 else 1;tu=math.floor(f.center[ua]/12);tv=math.floor(f.center[va]/2.5)
  for li in f.loop_indices:
   if not o.data.materials[f.material_index].name.startswith('StockMetal'):
    uv.data[li].uv=o.data.uv_layers[0].data[li].uv
    continue
   p=o.data.vertices[o.data.loops[li].vertex_index].co
   a=(p.x+.14*p.y+.5)/19.1;b=(p.z+.18*p.y+12.3)/15.0
   if key=='akm':a=p[ua]/12-tu;b=p[va]/2.5-tv
   uv.data[li].uv=(box[0]+(box[2]-box[0])*max(.005,min(.995,a)),box[1]+(box[3]-box[1])*max(.005,min(.995,b)))
 old=[tuple(d.uv) for d in o.data.uv_layers[0].data];new=[tuple(d.uv) for d in uv.data]
 for i,v in enumerate(new):o.data.uv_layers[0].data[i].uv=v
 for i,v in enumerate(old):uv.data[i].uv=v
 o.data.uv_layers[0].name='ReceiverUV0';uv.name='GeneratedUV1';o.data.uv_layers.active_index=0;o.data.uv_layers[0].active_render=True
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(next(P.glob('qr_performance_stock_textured_master*.glb'))))
high=next(o for o in bpy.context.scene.objects if o.type=='MESH');matrix=high.matrix_world.copy();pts=[matrix@v.co for v in high.data.vertices];xmin=min(p.x for p in pts);xmax=max(p.x for p in pts)
def rim(x):return [p for p in pts if abs(p.x-x)<(xmax-xmin)*.025]
ends=[rim(xmin),rim(xmax)];depths=[max(p.z for p in r)-min(p.z for p in r) for r in ends];front_hi=depths[1]<depths[0];r=ends[1 if front_hi else 0]
origin=Vector((xmax if front_hi else xmin,(min(p.y for p in r)+max(p.y for p in r))/2,(min(p.z for p in r)+max(p.z for p in r))/2));rotation=Matrix.Rotation(math.pi if front_hi else 0,4,'Z');scale=18.0/(xmax-xmin)
for v in high.data.vertices:v.co=rotation@((matrix@v.co-origin)*scale)
high.matrix_world=Matrix.Identity(4);high.name='QR_5080_Textured_Master';bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'QRPerformanceStock_Generated.blend'))
bm=bmesh.new();bm.from_mesh(high.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00002);bm.to_mesh(high.data);bm.free()
low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low);low.name='QR_Game_Source';active(low);low.data.calc_loop_triangles();m=low.modifiers.new('Game LOD0','DECIMATE');m.ratio=min(1,48000/len(low.data.loop_triangles));m.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=m.name)
low.data.materials[0]=high.data.materials[0].copy();mat=low.data.materials[0];nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');base=next(n.image for n in nt.nodes if n.type=='TEX_IMAGE' and any(l.to_socket==bs.inputs['Base Color'] for l in n.outputs['Color'].links))
base.filepath_raw=str(P/'T_QRStock_BaseColor.png');base.file_format='PNG';base.save()
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.use_selected_to_active=True;s.render.bake.cage_extrusion=.012;s.render.bake.max_ray_distance=.04;s.render.bake.margin=8;s.render.bake.use_clear=False
normal=bpy.data.images.new('T_QRStock_Normal',4096,4096);normal.colorspace_settings.name='Non-Color';normal.generated_color=(.5,.5,1,1);n=nt.nodes.new('ShaderNodeTexImage');n.image=normal;nt.nodes.active=n;high.select_set(True);bpy.ops.object.bake(type='NORMAL')
import numpy as np
pixels=np.empty(len(normal.pixels),dtype=np.float32);normal.pixels.foreach_get(pixels);rgba=pixels.reshape((-1,4));rgba[rgba[:,2]<.5,:3]=(.5,.5,1);normal.pixels.foreach_set(pixels);normal.update();normal.filepath_raw=str(P/'T_QRStock_Normal.png');normal.file_format='PNG';normal.save()
high.hide_render=True;high.hide_set(True);high.select_set(False)
poly=flat('StockPolymer',(.04,.042,.045),.57);rubber=flat('StockRubber',(.008,.009,.010),.85)
for material in [poly,rubber]:
 nt=material.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');uv=nt.nodes.new('ShaderNodeUVMap');uv.uv_map='GeneratedUV1';n=nt.nodes.new('ShaderNodeTexImage');n.image=normal;nt.links.new(uv.outputs['UV'],n.inputs['Vector']);nm=nt.nodes.new('ShaderNodeNormalMap');nm.uv_map='GeneratedUV1';nt.links.new(n.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
 if material==poly:
  n=nt.nodes.new('ShaderNodeTexImage');n.image=base;nt.links.new(uv.outputs['UV'],n.inputs['Vector']);nt.links.new(n.outputs['Color'],bs.inputs['Base Color'])
zlo=min(v.co.z for v in low.data.vertices);zhi=max(v.co.z for v in low.data.vertices);regions=[]
for f in low.data.polygons:
 c=f.center;regions.append(2 if c.x>16.85 else 1 if c.z>-.95 else 0)
records={'source':str(next(P.glob('qr_performance_stock_textured_master*.glb'))),'author_length_cm':18.0,'front_generated_x_max':front_hi,'mounts_root_m':{'m4':[0,-.0385,.0725],'akm':[.0008,-.083,.035]},'variants':{},'testing':'not performed; user will test'}
for key in ['m4','akm']:
 o=low.copy();o.data=low.data.copy();bpy.context.collection.objects.link(o);o.hide_set(False);o.hide_render=False;steel=metal(key);o.data.materials.clear()
 for material in [steel,poly,rubber]:o.data.materials.append(material)
 for f,i in zip(o.data.polygons,regions):f.material_index=i
 map_metal(o,key)
 if key=='akm':
  a=adapter(steel);map_metal(a,key);active(o);a.select_set(True);bpy.ops.object.join()
 active(o);o.name='SM_QRPerformanceStock';low.hide_render=True;low.hide_set(True);o.data.calc_loop_triangles();records['variants'][key]={'triangles':len(o.data.loop_triangles),'dimensions_cm':list(o.dimensions)}
 export(o,key);bpy.data.objects.remove(o,do_unlink=True)
(P/'authoring.json').write_text(json.dumps(records,indent=2));print('QR_STOCK_EXPORTED',json.dumps(records),flush=True)
