import bpy, math, json, random
from pathlib import Path
from mathutils import Vector, noise
R=Path('D:/FPS3D/FPSGAME/SourceAssets/GodSpaceLayout20260927')
bpy.ops.wm.open_mainfile(filepath=str(R/'GodSpace_Layout_V1.blend'));s=bpy.context.scene
# Trim the four corner panels to the actual octagonal deck.
def clip(poly,a,b,c):
 out=[]
 for i,p in enumerate(poly):
  q=poly[(i+1)%len(poly)];dp=a*p[0]+b*p[1]-c;dq=a*q[0]+b*q[1]-c
  if dp<=0:out.append(p)
  if (dp<0<dq) or (dq<0<dp):
   t=dp/(dp-dq);out.append((p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t))
 return out
for ix in [0,3]:
 for iy in [0,10]:
  o=bpy.data.objects.get(f'Paving_{ix}_{iy}');o.hide_render=True
  cx=-27+18*ix;cy=-40+8*iy;pts=[(cx-9,cy-4),(cx+9,cy-4),(cx+9,cy+4),(cx-9,cy+4)]
  for a,b in [(1,1),(1,-1),(-1,1),(-1,-1)]:pts=clip(pts,a,b,77.8)
  n=len(pts);vs=[(x,y,z) for z in [.15,.2] for x,y in pts];fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)];me=bpy.data.meshes.new('Cut corner paving');me.from_pydata(vs,[],fs);me.update();ob=bpy.data.objects.new('NEW corner paving module',me);bpy.context.collection.objects.link(ob);me.materials.append(bpy.data.materials['Preview white marble - simplified UE material'])
# Add a readable meandering valley and aerial colour falloff to the remote earth.
ob=bpy.data.objects['NEW remote earth backdrop'];me=ob.data
col=me.color_attributes.new(name='EarthTint',type='FLOAT_COLOR',domain='POINT')
for v in me.vertices:
 x,y,z=v.co;river=250*math.sin(y*.00037)+650*math.sin(y*.00012);d=abs(x-river)
 n=noise.fractal(Vector((x*.0015,y*.0015,2.4)),1,2,4)
 if d<190:rgb=(.07,.25,.29)
 elif d<500:rgb=(.17,.30,.22)
 elif z>-1250:rgb=(.32+.07*n,.36+.07*n,.34+.07*n)
 else:rgb=(.14+.08*n,.25+.1*n,.16+.08*n)
 haze=min(.65,math.hypot(x,y)/15000+.15);sky=(.42,.55,.62);col.data[v.index].color=(*(rgb[k]*(1-haze)+sky[k]*haze for k in range(3)),1)
ma=me.materials[0];nt=ma.node_tree;at=nt.nodes.new('ShaderNodeVertexColor');at.layer_name='EarthTint';nt.links.new(at.outputs['Color'],nt.nodes.get('Principled BSDF').inputs['Base Color'])
# Keep the broad decks, but open larger windows down to the land.
ma=bpy.data.materials['NEW distant cloud deck prototype'];cr=next(n for n in ma.node_tree.nodes if n.type=='VALTORGB');cr.color_ramp.elements[0].position=.56;cr.color_ramp.elements[1].position=.7
# A small number of actual volume silhouettes close to the lower platform provide parallax.
# These are offline preview volumes, not a claimed runtime solution.
ma=bpy.data.materials.new('Cloud hero volumes - offline preview');ma.use_nodes=True;n=ma.node_tree.nodes;n.clear();l=ma.node_tree.links
out=n.new('ShaderNodeOutputMaterial');vol=n.new('ShaderNodeVolumePrincipled');vol.inputs['Color'].default_value=(.9,.95,1,1);vol.inputs['Anisotropy'].default_value=.22;l.new(vol.outputs['Volume'],out.inputs['Volume'])
tc=n.new('ShaderNodeTexCoord');noise_n=n.new('ShaderNodeTexNoise');noise_n.inputs['Scale'].default_value=4.5;noise_n.inputs['Detail'].default_value=3;noise_n.inputs['Roughness'].default_value=.68;l.new(tc.outputs['Generated'],noise_n.inputs['Vector']);cr=n.new('ShaderNodeValToRGB');cr.color_ramp.elements[0].position=.36;cr.color_ramp.elements[1].position=.68;l.new(noise_n.outputs['Fac'],cr.inputs[0])
sub=n.new('ShaderNodeVectorMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=(.5,.5,.5);l.new(tc.outputs['Generated'],sub.inputs[0]);length=n.new('ShaderNodeVectorMath');length.operation='LENGTH';l.new(sub.outputs[0],length.inputs[0]);edge=n.new('ShaderNodeMapRange');edge.inputs['From Min'].default_value=.32;edge.inputs['From Max'].default_value=.5;edge.inputs['To Min'].default_value=1;edge.inputs['To Max'].default_value=0;l.new(length.outputs['Value'],edge.inputs['Value']);mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';l.new(cr.outputs[0],mul.inputs[0]);l.new(edge.outputs[0],mul.inputs[1]);density=n.new('ShaderNodeMath');density.operation='MULTIPLY';density.inputs[1].default_value=.032;l.new(mul.outputs[0],density.inputs[0]);l.new(density.outputs[0],vol.inputs['Density'])
random.seed(27)
for idx,(x,y,z,rx,ry,rz) in enumerate([(-260,420,-170,240,140,90),(80,610,-180,280,190,100),(-330,-180,-260,240,140,100),(420,380,-270,270,160,80),(-500,850,-220,240,140,100),(600,-450,-370,360,220,120)]):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=1,location=(x,y,z));o=bpy.context.object;o.name='NEW cloud depth silhouette '+str(idx);o.scale=(rx,ry,rz);o.data.materials.append(ma)
# A directional sky gradient keeps the arrival view from reading as a flat grey backdrop.
n=s.world.node_tree.nodes;l=s.world.node_tree.links;bg=n.get('Background');tex=n.new('ShaderNodeTexSky');tex.sky_type='HOSEK_WILKIE';tex.sun_direction=(.3,-.4,.65);tex.turbidity=3;tex.ground_albedo=.25;l.new(tex.outputs['Color'],bg.inputs['Color']);bg.inputs['Strength'].default_value=.22
# Frame the whole deck and leave room for the land/cloud relation.
a=bpy.data.objects['Preview aerial'];a.location=(112,-142,104);a.rotation_euler=(Vector((0,7,-4))-a.location).to_track_quat('-Z','Y').to_euler();a.data.lens=47
# An edge view is essential to judge the vertical scenery layers.
d=bpy.data.cameras.new('Preview overlook');o=bpy.data.objects.new('Preview overlook',d);bpy.context.collection.objects.link(o);o.location=(31,3,2);o.rotation_euler=(Vector((330,550,-380))-o.location).to_track_quat('-Z','Y').to_euler();d.lens=27;d.clip_end=40000
s.cycles.samples=40;s.cycles.volume_bounces=1;s.cycles.volume_step_rate=2
s.camera=a
# Remove unreferenced imported texture stubs so the delivered blend is self-contained.
for m in list(bpy.data.materials):
 if m.users==0:bpy.data.materials.remove(m)
for im in list(bpy.data.images):
 if im.users==0:bpy.data.images.remove(im)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'GodSpace_Layout_V1.blend'))
for name,cam in [('godspace_aerial',a),('godspace_overlook',o),('godspace_arrival',bpy.data.objects['Preview arrival']),('godspace_plan',bpy.data.objects['Layout orthographic'])]:
 s.camera=cam;s.render.filepath=str(R/'Preview'/(name+'.png'));bpy.ops.render.render(write_still=True)
print('PREVIEW_REFINED')
