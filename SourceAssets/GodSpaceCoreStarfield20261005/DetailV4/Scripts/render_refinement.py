import bpy, math, json, sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored'; TEX=OUT/'Textures'; PRE=ROOT/'Previews'; PRE.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'GodSpaceCore_BaseGeometry.blend'))
s=bpy.context.scene
C=Vector((0,28.6,5))
def material(name):
 m=bpy.data.materials[name]; m.use_nodes=True; m.node_tree.nodes.clear(); return m,m.node_tree.nodes,m.node_tree.links
def node(nodes,kind,label=''):
 n=nodes.new(kind);n.label=label;return n
def setup_math(nodes,links):
 def val(n,i,v):
  if hasattr(v,'node'):links.new(v,n.inputs[i])
  else:n.inputs[i].default_value=v
 def mathn(op,a,b=None,c=None):
  n=node(nodes,'ShaderNodeMath',op);n.operation=op;val(n,0,a)
  if b is not None:val(n,1,b)
  if c is not None:val(n,2,c)
  return n.outputs[0]
 def vec(op,a,b=None,c=None):
  n=node(nodes,'ShaderNodeVectorMath',op);n.operation=op;val(n,0,a)
  if b is not None:val(n,3 if op=='SCALE' else 1,b)
  if c is not None:val(n,2,c)
  return n.outputs['Value' if op in ['DOT_PRODUCT','LENGTH','DISTANCE'] else 'Vector']
 return val,mathn,vec
def image(nodes,links,name,coords=None,color='sRGB'):
 n=node(nodes,'ShaderNodeTexImage',name);n.image=bpy.data.images.load(str(TEX/name),check_existing=False);n.image.colorspace_settings.name=color;n.interpolation='Linear';n.extension='REPEAT'
 if coords is not None:links.new(coords,n.inputs['Vector'])
 return n.outputs['Color']
def combine(nodes,links,vals):
 n=node(nodes,'ShaderNodeCombineXYZ')
 for i,v in enumerate(vals):
  if hasattr(v,'node'):links.new(v,n.inputs[i])
  else:n.inputs[i].default_value=v
 return n.outputs[0]
def separate(nodes,links,v):
 n=node(nodes,'ShaderNodeSeparateXYZ');links.new(v,n.inputs[0]);return list(n.outputs)

# World direction / camera-relative inner-sphere projection reproduces runtime HLSL.
m,ns,ls=material('Core_Starfield');v,ma,ve=setup_math(ns,ls)
g=node(ns,'ShaderNodeNewGeometry');N=ve('NORMALIZE',ve('SUBTRACT',g.outputs['Position'],tuple(C)))
campos=node(ns,'ShaderNodeCombineXYZ','Render camera position, updated per camera')
V=ve('NORMALIZE',ve('SUBTRACT',campos.outputs[0],g.outputs['Position']));ray=ve('SCALE',V,-1)
b=ve('DOT_PRODUCT',N,ray);disc=ma('SUBTRACT',ma('MULTIPLY',b,b),1-.92*.92)
travel=ma('MAXIMUM',ma('SUBTRACT',ma('MULTIPLY',b,-1),ma('SQRT',ma('MAXIMUM',disc,0))),0)
inner=ve('NORMALIZE',ve('ADD',N,ve('SCALE',ray,travel)))
t=ma('MINIMUM',ma('MAXIMUM',ma('DIVIDE',disc,.10),0),1)
t=ma('MULTIPLY',ma('MULTIPLY',t,t),ma('SUBTRACT',3,ma('MULTIPLY',2,t)));t=ma('MULTIPLY',t,.65)
direction=ve('NORMALIZE',ve('ADD',ve('SCALE',N,ma('SUBTRACT',1,t)),ve('SCALE',inner,t)))
x,y,z=separate(ns,ls,direction)
uv=combine(ns,ls,[ma('ADD',ma('MULTIPLY',ma('ARCTAN2',y,x),1/(2*math.pi)),.5),ma('SUBTRACT',1,ma('MULTIPLY',ma('ARCCOSINE',ma('MINIMUM',ma('MAXIMUM',z,-1),1)),1/math.pi)),0])
sky=image(ns,ls,'T_CoreStarfield_BaseColor.png',uv)
stars=image(ns,ls,'T_CoreStars_Emissive.png',uv,'Non-Color')
q=ve('SCALE',direction,18);qx,qy,qz=separate(ns,ls,q)
weights=[ma('POWER',ma('ABSOLUTE',a),4) for a in [x,y,z]];den=ma('MAXIMUM',ma('ADD',ma('ADD',weights[0],weights[1]),weights[2]),.0001)
details=[]
for pair,w in zip([(qy,qz),(qx,qz),(qx,qy)],weights):
 d=image(ns,ls,'T_CoreNebula_Detail.png',combine(ns,ls,[pair[0],pair[1],0]),'Non-Color');details.append(ve('SCALE',d,ma('DIVIDE',w,den)))
detail=ve('ADD',ve('ADD',details[0],details[1]),details[2]);dr,dg,db=separate(ns,ls,detail)
sr,sg,sb=separate(ns,ls,sky);mx=ma('MAXIMUM',ma('MAXIMUM',sr,sg),sb)
mask=ma('MINIMUM',ma('MAXIMUM',ma('DIVIDE',ma('SUBTRACT',mx,.012),.118),0),1);mask=ma('MULTIPLY',ma('MULTIPLY',mask,mask),ma('SUBTRACT',3,ma('MULTIPLY',mask,2)))
structure=ma('MAXIMUM',.35,ma('ADD',1,ma('MULTIPLY',mask,ma('ADD',ma('MULTIPLY',ma('SUBTRACT',dr,.5),.9),ma('MULTIPLY',ma('SUBTRACT',dg,.5),.32)))))
sky=ve('SCALE',sky,ma('MULTIPLY',structure,3.4))
starcol=ve('MULTIPLY',stars,(.78,.89,1));starcol=ve('SCALE',starcol,3.5)
rim=ma('POWER',ma('MAXIMUM',0,ma('SUBTRACT',1,ve('DOT_PRODUCT',N,V))),10)
em=ve('ADD',ve('ADD',sky,starcol),ve('SCALE',(.009,.065,.24),ma('MULTIPLY',rim,.9)))
p=node(ns,'ShaderNodeBsdfPrincipled');p.inputs['Base Color'].default_value=(.001,.002,.007,1);p.inputs['Roughness'].default_value=.46;p.inputs['Specular IOR Level'].default_value=.003
ls.new(em,p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=1
o=node(ns,'ShaderNodeOutputMaterial');ls.new(p.outputs[0],o.inputs['Surface'])

m,ns,ls=material('Core_EngravedGold');v,ma,ve=setup_math(ns,ls)
col=image(ns,ls,'T_CoreGold_BaseColor.png');orm=image(ns,ls,'T_CoreGold_ORM.png',color='Non-Color');ao,rough,metal=separate(ns,ls,orm)
normal=image(ns,ls,'T_CoreGold_Normal.png',color='Non-Color');nx,ny,nz=separate(ns,ls,normal)
# Source normal generator is DirectX +dy: flip green for Blender OpenGL normal convention.
normal=combine(ns,ls,[nx,ma('SUBTRACT',1,ny),nz]);nm=node(ns,'ShaderNodeNormalMap','DirectX green flipped');ls.new(normal,nm.inputs['Color']);nm.inputs['Strength'].default_value=1
p=node(ns,'ShaderNodeBsdfPrincipled');ls.new(col,p.inputs['Base Color']);ls.new(rough,p.inputs['Roughness']);ls.new(metal,p.inputs['Metallic']);ls.new(nm.outputs[0],p.inputs['Normal']);p.inputs['Anisotropic'].default_value=0
o=node(ns,'ShaderNodeOutputMaterial');ls.new(p.outputs[0],o.inputs['Surface'])

# Bright open-sky studio establishes visibility against daylight without compositing reference pixels.
w=bpy.data.worlds.new('Daylight validation');s.world=w;w.use_nodes=True;wn=w.node_tree.nodes;wl=w.node_tree.links;wn.clear()
sky=node(wn,'ShaderNodeTexSky');sky.sky_type='MULTIPLE_SCATTERING';sky.sun_elevation=math.radians(35);sky.sun_rotation=math.radians(125);sky.sun_intensity=.35
bg=node(wn,'ShaderNodeBackground');bg.inputs['Strength'].default_value=.20;wl.new(sky.outputs[0],bg.inputs[0]);wo=node(wn,'ShaderNodeOutputWorld');wl.new(bg.outputs[0],wo.inputs[0])
def area(name,pos,power,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=C+Vector(pos);o.rotation_euler=(C-o.location).to_track_quat('-Z','Y').to_euler()
area('Warm key',(3,-4,5),700,4);area('Cool edge',(-4,1,2),900,3)
ca=bpy.data.cameras.new('Low-angle game-distance camera');cam=bpy.data.objects.new('Low-angle game-distance camera',ca);s.collection.objects.link(cam);s.camera=cam
cam.location=C+Vector((.45,8.5,-3.0));ca.lens=46;cam.rotation_euler=(C-cam.location).to_track_quat('-Z','Y').to_euler()
for i in range(3):campos.inputs[i].default_value=cam.location[i]
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=32;s.cycles.use_denoising=True
s.render.resolution_x=1203;s.render.resolution_y=912;s.render.resolution_percentage=100
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=0
s.render.image_settings.file_format='PNG';s.render.film_transparent=False
for image in bpy.data.images:
 if image.source=='FILE':image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GodSpaceCore_Starfield_V4_Editable.blend'))
s.render.filepath=str(PRE/'V4_LowAngle_Daylight_Checkpoint.png');bpy.ops.render.render(write_still=True)
report={'blender_version':bpy.app.version_string,'camera_position':list(cam.location),'camera_lens_mm':ca.lens,'resolution':[s.render.resolution_x,s.render.resolution_y],'resolution_percentage':s.render.resolution_percentage,'render':'Blender Cycles CPU, not UE','geometry_modified':False,'materials_implemented':['world-direction inner sphere projection','separate linear stars emissive','triplanar nebula detail','gold BC ORM and tangent normal'],'runtime_verification':False}
(PRE/'render_receipt.json').write_text(json.dumps(report,indent=2))
