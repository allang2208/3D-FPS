"""Save editable knit highs, garment masters and production inventory icons."""
import json,math,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldSweaterKnit20260929'
sys.path.insert(0,str(Path(__file__).resolve().parent))
if '--icons-only' in sys.argv:
 from render_field_sweater_inventory_icons import inventory
 inventory()
 raise SystemExit(0)
bpy.ops.wm.read_factory_settings(use_empty=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def material(name,color,pattern='Knit',cotton=False):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
 bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs['BSDF'],out.inputs['Surface'])
 uv=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=25/1.92*(8 if cotton else 1);l.new(uv.outputs['UV'],scale.inputs[0])
 maps={}
 for ch in ['BaseColor','Normal','ORM']:
  t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(R/'Textures'/pattern/(ch+'.png')),check_existing=True)
  t.image.colorspace_settings.name='sRGB' if ch=='BaseColor' else 'Non-Color';l.new(scale.outputs[0],t.inputs[0]);maps[ch]=t
 mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*color,1);l.new(maps['BaseColor'].outputs[0],mix.inputs[1]);l.new(mix.outputs[0],bs.inputs['Base Color'])
 sep=n.new('ShaderNodeSeparateColor');l.new(maps['ORM'].outputs[0],sep.inputs[0]);l.new(sep.outputs['Green'],bs.inputs['Roughness'])
 normal=n.new('ShaderNodeNormalMap');l.new(maps['Normal'].outputs[0],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
 bs.inputs['Sheen Weight'].default_value=.15 if cotton else .28;bs.inputs['Specular IOR Level'].default_value=.3;return m
olive=[material('Olive_Knit',(.115,.135,.080)),material('Olive_Rib',(.105,.124,.073),'Rib'),material('Olive_Inner',(.075,.085,.055))]
charcoal=[material('Charcoal_Cotton',(.045,.053,.065),cotton=True),material('Charcoal_Fold',(.041,.048,.059),cotton=True),material('Charcoal_Inner',(.030,.035,.043),cotton=True)]
def mesh_object(name,data):
 mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in data['positions']],[],data['triangles']);mesh.update()
 obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);uv=mesh.uv_layers.new(name='UVMap')
 for f,coords,slot in zip(mesh.polygons,data['uv'],data['triangle_materials']):
  f.use_smooth=True;f.material_index=slot
  for li,coord in zip(f.loop_indices,coords):uv.data[li].uv=(coord[0],1-coord[1])
 return obj
objects=[]
for label,folder,mats in [('Olive','Authored',olive),('Charcoal','ShortSleeve',charcoal)]:
 for profile in ['M4','Body']:
  source=R/folder/(profile+'.json')
  if label=='Charcoal' and profile=='Body':
   current=read(P/'Content/ColdSteelData/modular_outfits.json')['items']['ue_field_sweater_charcoal']['rig_meshes']['Body']
   if '/CharcoalGarmentRepair20260930/BodyV4/' in current:source=P/'SourceAssets/CharcoalGarmentRepair20260930/Authored/Body.json'
  data=read(source);obj=mesh_object(label+'_'+profile+'_GAME',data)
  for mat in mats:obj.data.materials.append(mat)
  obj['native_binding_source']=data['binding_source'];obj['native_author_json']=str(source);objects.append(obj)
  if profile=='Body':
   bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
   bpy.ops.export_scene.fbx(filepath=str(R/('SM_'+label+'_Garment.fbx')),use_selection=True,object_types={'MESH'},add_leaf_bones=False,apply_unit_scale=True,bake_anim=False)
# Explicit yarn-tube high objects, matching the surface projection inputs.
for family in ['Knit','Rib']:
 d=np.load(R/(family+'_high_surface.npz'));paths=d['paths'];radius=float(d['radius_cm']);vertices=[];faces=[]
 for path in paths:
  tangent=np.roll(path,-1,axis=0)-np.roll(path,1,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
  side=np.cross(tangent,np.array([0.,0.,1.]));side/=np.linalg.norm(side,axis=1)[:,None];up=np.cross(side,tangent)
  base=len(vertices);segments=len(path);cross=16
  for i,p in enumerate(path):
   for j in range(cross):vertices.append((p+radius*(side[i]*math.cos(j*2*math.pi/cross)+up[i]*math.sin(j*2*math.pi/cross)))*.01)
  for i in range(segments):
   for j in range(cross):faces.append([base+i*cross+j,base+((i+1)%segments)*cross+j,base+((i+1)%segments)*cross+(j+1)%cross,base+i*cross+(j+1)%cross])
 mesh=bpy.data.meshes.new(family+'_Yarn_HIGH');mesh.from_pydata(vertices,[],faces);obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj)
 obj['bake_only']=True;obj['surface_field']=str(R/(family+'_high_surface.npz'));obj.hide_render=True;obj.hide_set(True)
for o in objects:o.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(R/'FieldSweaterKnit_HIGH_and_GAME.blend'))
# Icons have an independent display rig, framing and exposure calibration. This
# production entry and --icons-only share it, so a rebuild cannot restore the old
# overexposed icons or the long-sleeve silhouette of the charcoal T-shirt.
from render_field_sweater_inventory_icons import inventory
inventory()
print('SWEATER_EDITABLE_AND_ICONS_SAVED',flush=True)
