import bpy, json, math, random
from pathlib import Path
from mathutils import Vector, Matrix
R=Path('D:/FPS3D/FPSGAME/SourceAssets/GodSpaceLayout20260927'); (R/'Preview').mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.render.engine='CYCLES'; scene.cycles.samples=32; scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED'; scene.render.threads=12
scene.render.resolution_x=2000; scene.render.resolution_y=1500; scene.render.resolution_percentage=100
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background'); bg.inputs[0].default_value=(0.40,0.55,0.72,1); bg.inputs[1].default_value=.55
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'

def mat(name,col,rough=.4,metal=0):
 m=bpy.data.materials.new(name); m.diffuse_color=(*col,1); m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*col,1); p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal
 return m
white=mat('Preview white marble - simplified UE material',(.76,.79,.77),.32)
n=white.node_tree.nodes; l=white.node_tree.links; tc=n.new('ShaderNodeTexCoord'); ns=n.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value=1.7; ns.inputs['Detail'].default_value=3; l.new(tc.outputs['Generated'],ns.inputs['Vector']); ramp=n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position=.27; ramp.color_ramp.elements[0].color=(.43,.51,.54,1); ramp.color_ramp.elements[1].position=.45; ramp.color_ramp.elements[1].color=(.79,.82,.80,1); l.new(ns.outputs['Fac'],ramp.inputs[0]); l.new(ramp.outputs[0],n.get('Principled BSDF').inputs['Base Color'])
gold=mat('Aged champagne brass',(.43,.29,.11),.3,.72)
dark=mat('Blue grey stone inlay',(.075,.135,.17),.38)
wood=mat('Preview wood',(.18,.095,.037),.48)
iron=mat('Preview iron',(.05,.065,.07),.4,.55)
water=mat('Preview water - static',(.035,.26,.32),.18,.2)
blue=mat('Sapphire',(.02,.24,.40),.18,.5)
glow=mat('Proposed main deity core - blockout',(.6,.85,1),.22)
glow.node_tree.nodes.get('Principled BSDF').inputs['Emission Color'].default_value=(.3,.65,1,1); glow.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=2.5
# Import the existing UE source meshes once, sharing geometry for repeated placement.
assets={}; receipt=[]
for rec in json.loads((R/'exported_meshes.json').read_text(encoding='utf8')):
 key=Path(rec['file']).stem
 before=set(bpy.data.objects)
 bpy.ops.import_scene.fbx(filepath=rec['file'],use_anim=False,use_custom_normals=True)
 obs=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
 if not obs: raise RuntimeError('No geometry for '+key)
 # UE FBX importer supplies meter scaling and axis conversion. Bake the imported basis.
 for o in obs:
  o.data.transform(o.matrix_world); o.matrix_world=Matrix.Identity(4)
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]
 if len(obs)>1:bpy.ops.object.join()
 o=bpy.context.view_layer.objects.active; o.name='LIB_'+key
 # Normalize lengths to the actual UE bounding box (cm -> m), preserving the exporter axes.
 bb=[Vector(v) for v in o.bound_box]; lo=Vector(tuple(min(v[i] for v in bb) for i in range(3))); hi=Vector(tuple(max(v[i] for v in bb) for i in range(3)))
 source_dims=[(rec['bounds'][1][i]-rec['bounds'][0][i])*.01 for i in range(3)]
 # Center XY and place bottom at zero. All reusable building modules have a base pivot.
 for v in o.data.vertices:
  v.co.x=(v.co.x-(lo.x+hi.x)/2)*source_dims[0]/(hi.x-lo.x)
  v.co.y=(v.co.y-(lo.y+hi.y)/2)*source_dims[1]/(hi.y-lo.y)
  v.co.z=(v.co.z-lo.z)*source_dims[2]/(hi.z-lo.z)
 for slot in o.material_slots:
  name=slot.material.name.lower() if slot.material else ''
  slot.material=gold if any(k in name for k in ['gold','satin','bronze']) else blue if 'sapphire' in name else wood if 'wood' in name else iron if any(k in name for k in ['steel','iron']) else water if 'water' in name else white
 o.hide_render=True; o.hide_viewport=True
 assets[key]=o
 receipt.append(dict(mesh=rec['mesh'],dimensions_m=source_dims,vertices=len(o.data.vertices)))

def reuse(key,name,loc,rz=0,scale=(1,1,1)):
 o=assets[key].copy(); o.data=assets[key].data; bpy.context.collection.objects.link(o); o.name=name; o.hide_render=False; o.hide_viewport=False; o.location=loc; o.rotation_euler.z=math.radians(rz); o.scale=scale; return o

def box(name,loc,size,material=white,bevel=0):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material)
 if bevel: m=o.modifiers.new('edge finish','BEVEL');m.width=bevel;m.segments=2
 return o

def ring(name,loc,radius,tube,material=gold,rotation=(0,0,0)):
 bpy.ops.mesh.primitive_torus_add(major_segments=96,minor_segments=8,location=loc,major_radius=radius,minor_radius=tube,rotation=rotation);o=bpy.context.object;o.name=name;o.data.materials.append(material);return o

def polygon_prism(name,pts,z0,z1,material):
 N=len(pts);vs=[(x,y,z) for z in [z0,z1] for x,y in pts]; fs=[tuple(reversed(range(N))),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]; m=bpy.data.meshes.new(name);m.from_pydata(vs,[],fs);m.update();o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o);m.materials.append(material);return o

def perimeter(w,h,c):return [(-w/2+c,-h/2),(w/2-c,-h/2),(w/2,-h/2+c),(w/2,h/2-c),(w/2-c,h/2),(-w/2+c,h/2),(-w/2,h/2-c),(-w/2,-h/2+c)]
# Compact 80x96 m floating platform, cut corners and a layered underside.
outline=perimeter(80,96,10)
polygon_prism('NEW - floating foundation blockout',outline,-3.2,0,white)
for w,h,c,z0,z1,ma in [(81,97,10.5,-.35,.15,white),(78.8,94.8,10,-3.5,-3.15,gold),(74,90,9,-5.0,-3.5,white),(66,82,8,-6.2,-5,dark),(54,70,7,-7.0,-6.2,white)]:polygon_prism('NEW - undercroft cornice',perimeter(w,h,c),z0,z1,ma)
# Existing 18x8 m marble panels in the rectangular walkable area; corner infill is a new cut-edge module.
for ix in range(4):
 for iy in range(11):reuse('SM_MarbleFloorTiles',f'Paving_{ix}_{iy}',(-27+18*ix,-40+8*iy,.15),scale=(1,1,.25))
# Main axial approach, cross-route and a circular fountain forecourt.
box('Processional avenue',(0,0,.218),(9.4,88,.035),dark)
for x in [-4.84,4.84]:box('Avenue brass edge',(x,0,.24),(.12,88,.03),gold)
box('East west circulation',(0,8,.242),(73,5.2,.03),dark)
for y in [5.3,10.7]:box('Cross-route edge',(0,y,.27),(73,.10,.03),gold)
# Small square paving joins are material scale detail in the production plan.
for y in range(-42,44,2):box('Avenue inlay',(0,y,.25),(9,.035,.012),white)
# fountain plaza at (0,-6), actual mesh at original scale.
bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=10,depth=.12,location=(0,-6,.31));bpy.context.object.data.materials.append(white)
ring('Fountain medallion', (0,-6,.38),9.5,.09,gold)
reuse('SM_FountainPolishedV9','Existing V9 fountain',(0,-6,.38))
# A static water surface for the preview only, at the basin height.
bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=3.55,depth=.025,location=(0,-6,1.83));bpy.context.object.data.materials.append(water)
# Dedicated altar terrace, with readable 15cm risers and 35cm treads.
for i in range(6):box('NEW altar stair module',(0,27, .2+(i+1)*.075),(18-i*.7,20-i*.7,(i+1)*.15),white,.03)
box('Dais inlay',(0,27,1.116),(12,12,.025),dark)
ring('Core medallion',(0,27,1.15),5,.06,gold)
reuse('SM_SquareAltar','Existing expedition altar',(0,24.5,1.13),180)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,radius=1.5,location=(0,28.6,5.0));core=bpy.context.object;core.name='NEW - deity core visual placeholder';core.data.materials.append(glow)
for p in core.data.polygons:p.use_smooth=True
ring('NEW orbit ring A',(0,28.6,5),2.15,.035,gold,(math.pi/2,.4,0))
ring('NEW orbit ring B',(0,28.6,5),2.35,.025,gold,(.5,.25,0))
# Existing white celestial pavilion, unchanged physical proportions.
px,py=-24,13
reuse('SM_RomanPavilionBase_20','Existing pavilion base',(px,py,.2))
reuse('SM_RomanPavilionArch_20','Existing pavilion arch',(px,py,3.0))
reuse('SM_RomanPavilionDome_20','Existing celestial dome',(px,py,3.8))
for i in range(10):
 a=i*2*math.pi/10;reuse('SM_RomanColumn_Round_20','Pavilion column',(px+3.6*math.cos(a),py+3.6*math.sin(a),.4))
# East service court uses real current furnace, casting station and crate meshes.
box('Workshop courtyard',(24,13,.27),(17,21,.10),dark)
for pos,key,yaw in [((28,20,.32),'SM_BlastFurnace',90),((23,20,.32),'SM_CastingStation',90),((29,11,.32),'SM_WarehouseCrate_T1_Wood_v2',90),((29,8,.32),'SM_WarehouseCrate_T1_Wood_v2',90)]:reuse(key,'Existing service '+key,pos,yaw)
# Four colonnade fragments, open views at the east/west cross-axis.
for x in [-35,35]:
 for ymin,ymax in [(-32,-12),(22,38)]:
  n=round((ymax-ymin)/4)
  for i in range(n+1):reuse('SM_RomanColumn_Detailed','Existing colonnade column',(x,ymin+(ymax-ymin)*i/n,.2))
  reuse('SM_Colonnade_Entablature','Existing colonnade beam',(x,(ymin+ymax)/2,2.65),90,((ymax-ymin)/16.32,1,1))
# Rear pairs frame altar while keeping a wide sky opening.
for xmid in [-20,20]:
 for dx in [-8,-4,0,4,8]:reuse('SM_RomanColumn_Detailed','Rear colonnade',(xmid+dx,39,.2))
 reuse('SM_Colonnade_Entablature','Rear entablature',(xmid,39,2.65))
# Balustrade all around the floating platform: no unguarded ground-exit gaps.
railpts=perimeter(78,94,9.6)
for edge,p in enumerate(railpts):
 q=railpts[(edge+1)%len(railpts)]; length=math.dist(p,q); n=math.ceil(length/2); yaw=math.degrees(math.atan2(q[1]-p[1],q[0]-p[0])); step=length/n
 for i in range(n):
  x=p[0]+(q[0]-p[0])*i/n;y=p[1]+(q[1]-p[1])*i/n
  reuse('SM_RomanBaluster_Small','Perimeter baluster',(x,y,.2))
  reuse('SM_RomanRail_200','Perimeter rail',(x+(q[0]-p[0])/(2*n),y+(q[1]-p[1])/(2*n),1.2),yaw,(step/2,1,1))
# Portal court. Three links are present in the current runtime; a fourth pad stays empty.
portal_locs=[(-22,-29,0),(22,-29,180),(-22,-19,0)]
for i,(x,y,yaw) in enumerate(portal_locs):
 box('NEW portal pad',(x,y,.35),(6,6,.3),dark)
 reuse('SM_GamedevPortal_Frame',f'Existing portal frame {i+1}',(x,y,.5),yaw)
 e=box('Portal energy preview',(x,y,2.22),(.04,1.65,2.86),glow);e.rotation_euler.z=math.radians(yaw)
box('Reserved future portal pad',(22,-19,.3),(6,6,.2),dark)
# Low seating and wayfinding are visibly blockouts, listed as missing modules.
for x in [-14,14]:
 for y in [-6,6]:box('NEW bench blockout',(x,y,.65),(3,.7,.9),white,.08)
# Terrain is a finite 24km low-poly matte backdrop; original procedural data, no downloaded imagery.
random.seed(27)
from mathutils import noise
N=128;span=24000; verts=[]; faces=[]
for j in range(N+1):
 for i in range(N+1):
  x=(i/N-.5)*span;y=(j/N-.5)*span
  n=noise.fractal(Vector((x*.0005,y*.0005,2.4)),1,2,4)
  mountain=max(0,n-.05)**2*1900
  river=250*math.sin(y*.00037)+650*math.sin(y*.00012)
  trench=math.exp(-((x-river)/380)**2)
  verts.append((x,y,-1450+mountain-70*trench))
for j in range(N):
 for i in range(N):
  a=j*(N+1)+i;faces.append((a,a+1,a+N+2,a+N+1))
me=bpy.data.meshes.new('Backdrop 32768 triangles');me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new('NEW remote earth backdrop',me);bpy.context.collection.objects.link(ob)
terrain=mat('Remote landscape colour and aerial perspective',(.1,.23,.18),1)
n=terrain.node_tree.nodes;l=terrain.node_tree.links;tc=n.new('ShaderNodeTexCoord');no=n.new('ShaderNodeTexNoise');no.inputs['Scale'].default_value=13;no.inputs['Detail'].default_value=4;l.new(tc.outputs['Generated'],no.inputs[0]);cr=n.new('ShaderNodeValToRGB');cr.color_ramp.elements[0].color=(.12,.23,.24,1);cr.color_ramp.elements[0].position=.26;cr.color_ramp.elements[1].color=(.4,.48,.46,1);cr.color_ramp.elements[1].position=.78;l.new(no.outputs[0],cr.inputs[0]);l.new(cr.outputs[0],n.get('Principled BSDF').inputs['Base Color']);me.materials.append(terrain)
for p in me.polygons:p.use_smooth=True
# Two restrained textured cloud decks. Holes deliberately reveal the ground.
cloud=bpy.data.materials.new('NEW distant cloud deck prototype');cloud.use_nodes=True
n=cloud.node_tree.nodes;n.clear();l=cloud.node_tree.links;o=n.new('ShaderNodeOutputMaterial');tr=n.new('ShaderNodeBsdfTransparent');p=n.new('ShaderNodeBsdfPrincipled');p.inputs['Base Color'].default_value=(.84,.90,.95,1);p.inputs['Roughness'].default_value=1;mix=n.new('ShaderNodeMixShader');l.new(tr.outputs[0],mix.inputs[1]);l.new(p.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],o.inputs['Surface']);tc=n.new('ShaderNodeTexCoord');no=n.new('ShaderNodeTexNoise');no.inputs['Scale'].default_value=9;no.inputs['Detail'].default_value=5;no.inputs['Roughness'].default_value=.7;l.new(tc.outputs['Generated'],no.inputs['Vector']);cr=n.new('ShaderNodeValToRGB');cr.color_ramp.elements[0].position=.49;cr.color_ramp.elements[0].color=(0,0,0,1);cr.color_ramp.elements[1].position=.63;cr.color_ramp.elements[1].color=(.98,.98,.98,1);l.new(no.outputs['Fac'],cr.inputs[0]);l.new(cr.outputs[0],mix.inputs[0]);bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.45;bump.inputs['Distance'].default_value=45;l.new(no.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
for k,(z,size,dx,dy) in enumerate([(-280,13000,0,0),(-560,18000,1100,-1800)]):
 bpy.ops.mesh.primitive_plane_add(size=size,location=(dx,dy,z));o=bpy.context.object;o.name='NEW cloud layer '+str(k);o.data.materials.append(cloud);o.rotation_euler.z=k*.47
# Warm sun, blue ambient. Scene-wide fog is omitted from the prototype, preserving clarity.
ld=bpy.data.lights.new('Sun','SUN');ld.energy=2.7;ld.angle=math.radians(8);o=bpy.data.objects.new('Sun',ld);bpy.context.collection.objects.link(o);o.rotation_euler=(math.radians(25),math.radians(-28),math.radians(-30))
def camera(name,loc,target,lens=48):
 d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=40000;return o
hero=camera('Preview aerial',(105,-140,98),(0,4,-3),48)
walk=camera('Preview arrival',(13,-38,2.0),(0,19,4.3),24)
top=camera('Layout orthographic',(0,0,135),(0,0,0),45);top.data.type='ORTHO';top.data.ortho_scale=110
scene.camera=hero
bpy.ops.wm.save_as_mainfile(filepath=str(R/'GodSpace_Layout_V1.blend'))
# These Blender clouds only convey depth. UE integration reuses the game's cloud assets.
cloud_policy = dict(
    material='/Game/Weather/Materials/MI_FPSLayeredClouds',
    controller='FPSWeatherManager / StormCloudComponent',
    new_cloud_assets=False,
    external_references_scope='distant_ground_only',
    cloud_decks_meaning='Blender composition placeholders only; not UE layer count or altitude parameters',
    integration_status='Pending layout approval; reuse existing textures and weather, adapt per-map altitude/thickness/coverage and storm altitude control')
(R/'layout_manifest.json').write_text(json.dumps(dict(name='主神空间',status='Independent Blender layout preview; no UE integration',units='meters',platform=[80,96],altar=[0,24.5,1.13],core_placeholder=[0,28.6,5],fountain=[0,-6,.38],pavilion=[-24,13,.2],workshop=[24,13,.2],player_start=[13,-38,1.02],portals=portal_locs,cloud_decks=[-280,-560],cloud_policy=cloud_policy,earth=-1450,source_meshes=receipt),ensure_ascii=False,indent=2),encoding='utf8')
for name,cam in [('godspace_aerial',hero),('godspace_arrival',walk),('godspace_plan',top)]:
 scene.camera=cam;scene.render.filepath=str(R/'Preview'/(name+'.png'));bpy.ops.render.render(write_still=True)
print('PREVIEW_COMPLETE')
