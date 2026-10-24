"""Produce vector typography masks, mounted signs and roof-to-sky projection geometry."""
import bpy,bmesh,math,json,sys,ast
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent));from design import *
# Glyph masks are production textures from editable font geometry, not scene previews.
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='Standard'
world=bpy.data.worlds.new('MaskWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(0,0,0,1);scene.world=world
mat=bpy.data.materials.new('GlyphEmission');mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();e=nodes.new('ShaderNodeEmission');e.inputs[0].default_value=(1,1,1,1);o=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(e.outputs[0],o.inputs['Surface'])
camdata=bpy.data.cameras.new('MaskCamera');cam=bpy.data.objects.new('MaskCamera',camdata);scene.collection.objects.link(cam);cam.location=(0,-5,0);cam.rotation_euler=(math.pi/2,0,0);camdata.type='ORTHO';camdata.ortho_scale=2;scene.camera=cam
for spec in HOLOGRAMS:
 objs=[]
 for text,z,size,width in [(spec['title'],-.44,.24,1.68),(spec['subtitle'],-.73,.095,1.48)]:
  data=bpy.data.curves.new(spec['key']+text,'FONT');data.body=text;data.align_x='CENTER';data.align_y='CENTER';data.size=size;data.space_character=1.15
  ob=bpy.data.objects.new(data.name,data);scene.collection.objects.link(ob);ob.location=(0,0,z);ob.rotation_euler=(math.pi/2,0,0);data.materials.append(mat);bpy.context.view_layer.update()
  ob.scale.x=min(1,width/max(ob.dimensions.x,.001));objs.append(ob)
 scene.render.filepath=str(R/'Textures'/('T_AP19_'+spec['key']+'_Glyph.png'));bpy.ops.render.render(write_still=True)
 for ob in objs:bpy.data.objects.remove(ob,do_unlink=True)

bpy.ops.wm.open_mainfile(filepath=str(R.parent/'RefinementV18/WaterfrontLife_Source.blend'));scene=bpy.context.scene
# Update the exact materials used by the retained city and landmarks in the bake source.
for m in bpy.data.materials:
 if not m.use_nodes:continue
 name=m.name.split('.')[0]
 if name not in FAMILIES:continue
 for n in m.node_tree.nodes:
  if n.type=='TEX_IMAGE' and n.image and n.image.name.endswith('_E.png'):
   n.image=bpy.data.images.load(str(R/'Textures'/f'T_AP19_{name}_E.png'));n.image.pack()
 p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
 if p:p.inputs['Emission Strength'].default_value=1.05
groups={};ATLAS_METRES=(4.,4.)
tree=ast.parse((PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/author_scene.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('face','box','beam')],type_ignores=[]),'retained_helpers','exec'),globals())
baseface=face
def face(g,vs,mat='Metal',uv=None):
 if uv is None:
  normal=(Vector(vs[1])-Vector(vs[0])).cross(Vector(vs[2])-Vector(vs[0]));a=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3) if i!=a];uv=[(v[axes[0]]/4,v[axes[1]]/4) for v in vs]
 baseface(g,vs,mat,uv)
def panel(g,p,w,h,role):
 x,y,z=p;face(g,[(x-w/2,y,z-h/2),(x+w/2,y,z-h/2),(x+w/2,y,z+h/2),(x-w/2,y,z+h/2)],role,[(0,0),(1,0),(1,1),(0,1)])
def drum(g,p,axis,r,length,role,sides=24):
 p=Vector(p);axis=Vector(axis).normalized();side=axis.cross(Vector((0,1,0))).normalized();up=axis.cross(side).normalized()
 rings=[[p+axis*zz+side*math.cos(i*math.tau/sides)*r+up*math.sin(i*math.tau/sides)*r for i in range(sides)] for zz in (0,length)]
 face(g,rings[0][::-1],role);face(g,rings[1],role)
 for i in range(sides):face(g,[rings[0][i],rings[0][(i+1)%sides],rings[1][(i+1)%sides],rings[1][i]],role)
for j,b in enumerate(BOARDS):
 x,y,z=b['p'];w,h=b['w'],b['h'];g='Structures';light='Warm' if j else 'Teal'
 box(g,(x,y+.7,z),(w+.9,1.1,h+.9),'Metal')
 for side in (-1,1):
  box(g,(x+side*(w/2+.35),y+.05,z),(.6,1.2,h+1.2),'Metal');box(g,(x,y+.05,z+side*(h/2+.35)),(w+.9,1.2,.6),'Metal')
  box(g,(x+side*(w/2+.7),y-.14,z),(.18,.15,h+.9),light)
 for dz in (-h*.35,0,h*.35):
  for side in (-1,1):
   xx=x+side*w*.35;beam(g,(xx,y+1.2,z+dz),(xx,y+4.2,z+dz+2),.35,.4,'Metal');box(g,(xx,y+4.2,z+dz+2),(1.6,.35,1.8),'Metal')
 # Mounted maintenance ledge has a full structural floor and open rail.
 box(g,(x,y-1,z-h/2-1.1),(w+1,2.7,.3),'Metal')
 beam(g,(x-w/2,y-2.3,z-h/2),(x+w/2,y-2.3,z-h/2),.18,.18,'Metal')
 for i in range(5):beam(g,(x-w/2+i*w/4,y-2.3,z-h/2-1),(x-w/2+i*w/4,y-2.3,z-h/2),.18,.18,'Metal')
 panel('Display_'+b['key'],b['p'],w,h,'Display_'+b['key'])
for h in HOLOGRAMS:
 origin=Vector(h['origin']);center=Vector(h['p']);axis=(center-origin).normalized();g='Structures';x,y,z=origin
 # Base sits on the roof; head and real lens align with the actual projection axis.
 box(g,(x,y,z-1),(6,6,1),'Metal');drum(g,(x,y,z-.5),(0,0,1),1.8,1.4,'Metal')
 for side in (-1,1):beam(g,(x+side*2.1,y,z+.4),(x+side*2.1,y,z+3),.6,.7,'Metal')
 head=origin+Vector((0,0,2.7));drum(g,head,axis,1.55,3,'Metal')
 lens=head+axis*3.05;drum(g,lens,axis,1.34,.12,'Teal' if h['style']==0 else 'Violet')
 h['beam_origin']=tuple(lens);h['beam_length']=(center-lens).length;h['beam_axis']=tuple((center-lens).normalized())
 # Open 24-sided shell, six longitudinal spans. U stores length, untouched by FBX V flip.
 axis=Vector(h['beam_axis']);side=axis.cross(Vector((0,1,0))).normalized();up=axis.cross(side).normalized();n=24;rings=[]
 for j in range(7):
  t=j/6;p=lens+(center-lens)*t;r=1.34+10.66*t;rings.append([p+side*math.cos(i*math.tau/n)*r+up*math.sin(i*math.tau/n)*r for i in range(n)])
 for j in range(6):
  for i in range(n):face('Projection_'+h['key'],[rings[j][i],rings[j][(i+1)%n],rings[j+1][(i+1)%n],rings[j+1][i]],'Beam_'+h['key'],[(j/6,i/n),(j/6,(i+1)/n),((j+1)/6,(i+1)/n),((j+1)/6,i/n)])
 panel('Hologram_'+h['key'],h['p'],h['w'],h['h'],'Hologram_'+h['key'])
mats={};colors={'Metal':(.06,.08,.1),'Warm':(1,.63,.28),'Teal':(.12,.74,1),'Violet':(.8,.32,1)}
for role in set(role for data in groups.values() for role in data['m']):
 m=bpy.data.materials.new('AP19_'+role);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');rgb=colors.get(role,(.01,.02,.03));p.inputs['Base Color'].default_value=(*rgb,1);p.inputs['Metallic'].default_value=.6;p.inputs['Roughness'].default_value=.4
 if role in ['Warm','Teal','Violet']:p.inputs['Emission Color'].default_value=(*rgb,1);p.inputs['Emission Strength'].default_value=.8
 mats[role]=m
out=R/'Meshes';out.mkdir(exist_ok=True);records=[]
for key,data in groups.items():
 me=bpy.data.meshes.new(key);me.from_pydata(data['v'],[],data['f']);me.update();ob=bpy.data.objects.new('AP19_'+key,me);scene.collection.objects.link(ob);ob.location.y=SHIFT
 order=list(dict.fromkeys(data['m']))
 for role in order:me.materials.append(mats[role])
 uv=me.uv_layers.new(name='SurfaceUV')
 for poly,role,coords in zip(me.polygons,data['m'],data['uv']):
  poly.material_index=order.index(role);poly.use_smooth=key.startswith('Projection_')
  for li,co in zip(poly.loop_indices,coords):uv.data[li].uv=co
 if key.startswith('Projection_'):
  bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bm.to_mesh(me);bm.free();me.update()
 clone=ob.copy();clone.data=me.copy();clone.location=(0,0,0);clone.name='SM_AP19_'+key;scene.collection.objects.link(clone)
 for v in clone.data.vertices:v.co=((-v.co.x+10)*1.25,-(v.co.y+SHIFT)*1.25,(v.co.z-90)*1.25)
 bpy.ops.object.select_all(action='DESELECT');clone.select_set(True);bpy.context.view_layer.objects.active=clone;mod=clone.modifiers.new('Production triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 path=out/(clone.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 records.append(dict(key=key,name=clone.name,fbx=str(path),triangles=len(clone.data.polygons),materials=order,nanite=key=='Structures'));bpy.data.objects.remove(clone,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'LuminousSkyline_Source.blend'))
(R/'assembly.json').write_text(json.dumps(dict(meshes=records,boards=BOARDS,holograms=HOLOGRAMS),indent=2),encoding='utf8');print('AP19_GEOMETRY_AUTHORED',sum(r['triangles'] for r in records),flush=True)
