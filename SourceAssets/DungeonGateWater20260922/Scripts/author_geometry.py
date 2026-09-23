"""Manufactured welded steel gate and feathered shallow-water surfaces, no render."""
import bpy,bmesh,math,json,random
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
CFG=json.loads((ROOT/'Config/design.json').read_text());R=random.Random(CFG['seed'])
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
parts=[];recipes={
 'Paint':dict(color=[.031,.043,.039],roughness=.49,metallic=0),
 'Steel':dict(color=[.20,.215,.22],roughness=.31,metallic=.94),
 'Weld':dict(color=[.078,.080,.067],roughness=.66,metallic=.55),
 'Dark':dict(color=[.009,.012,.011],roughness=.73,metallic=0),
 'Water':dict(color=[.045,.064,.057],roughness=.075,metallic=0)}
materials={}
for key,r in recipes.items():
    mat=bpy.data.materials.new('GateWater_'+key);mat.use_nodes=True
    p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*r['color'],1)
    p.inputs['Roughness'].default_value=r['roughness'];p.inputs['Metallic'].default_value=r['metallic']
    materials[key]=mat
    if key=='Water':
        p.inputs['IOR'].default_value=1.333;p.inputs['Transmission Weight'].default_value=.94
        nt=mat.node_tree;n=nt.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=36
        bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.05;bump.inputs['Distance'].default_value=.001
        nt.links.new(n.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    elif key!='Dark':
        nt=mat.node_tree;folder=ROOT.parent/'DungeonServices20260922/Authored/Textures'
        vc=nt.nodes.new('ShaderNodeVertexColor');vc.layer_name='Wear'
        sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(vc.outputs['Color'],sep.inputs['Color'])
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(folder/'ServicePaint_AgeMask.png'),check_existing=True);tex.image.colorspace_settings.name='Non-Color'
        mask=nt.nodes.new('ShaderNodeMath');mask.operation='MULTIPLY';nt.links.new(tex.outputs[0],mask.inputs[0]);nt.links.new(sep.outputs[2],mask.inputs[1])
        mix=nt.nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(*r['color'],1);mix.inputs[2].default_value=(.13,.045,.015,1)
        nt.links.new(mask.outputs[0],mix.inputs[0]);nt.links.new(mix.outputs[0],p.inputs['Base Color'])
        nm=nt.nodes.new('ShaderNodeTexImage');nm.image=bpy.data.images.load(str(folder/'ServicePaint_Normal.png'),check_existing=True);nm.image.colorspace_settings.name='Non-Color'
        normal=nt.nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.45
        nt.links.new(nm.outputs[0],normal.inputs['Color']);nt.links.new(normal.outputs[0],p.inputs['Normal'])

def finish(o,mat,bevel=0,wear=.3,rust=.1):
    o.data.materials.append(materials[mat]);parts.append(o);o['wear']=wear;o['rust']=rust
    if bevel:
        mod=o.modifiers.new('Rolled edge radius','BEVEL');mod.width=bevel;mod.segments=3
        bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
    return o

def box(name,c,size,mat='Paint',bevel=.0015,wear=.3,rust=.1):
    bpy.ops.mesh.primitive_cube_add(size=1,location=c);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,mat,bevel,wear,rust)

def rod(name,a,b,r,mat='Paint',sides=10,wear=.12,rust=.15):
    a,b=Vector(a),Vector(b);d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=d.length,location=(a+b)*.5)
    o=bpy.context.object;o.name=name;o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    finish(o,mat,0,wear,rust)
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    return o

def bolt(x,y,z):
    rod('Anchor washer',(x,y,z),(x,y-.002,z),.014,'Steel',24,.2,.3)
    rod('Hex anchor',(x,y-.002,z),(x,y-.008,z),.009,'Steel',6,.35,.25)

def bead(name,pts,r=.0025):
    # A continuous small weld, with a restrained, seeded scallop along its axis.
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=2;curve.bevel_depth=r;curve.bevel_resolution=1
    spline=curve.splines.new('POLY');spline.points.add(len(pts)-1)
    for p,co in zip(spline.points,pts):p.co=(*co,1);p.radius=R.uniform(.83,1.12)
    o=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH')
    return finish(bpy.context.object,'Weld',0,.25,.82)

y=CFG['gate']['plane_y_m'];posts=CFG['gate']['posts_x_m']
for x in posts:
    box('Structural upright',(x,y,1.5),(.07,.10,3.0),wear=.50,rust=.2)
    for z in (.15,1.53,2.86):
        box('Masonry anchor tab',(x,y-.015,z),(.136,.028,.09),wear=.40,rust=.45)
        for xx in (x-.046,x+.046):bolt(xx,y-.030,z)
    box('Post end cap',(x,y,2.995),(.075,.106,.01),'Steel',.001)
for z in (.075,2.07,2.952):box('Fixed frame rail',(10.5,y,z),(4.36,.080,.055),wear=.46,rust=.20)

def panel(left,right,bottom,top,door=False):
    # Independent bounded mesh panels stop at the real steel rebates.
    yy=y-.009 if door else y+.008
    for x in (left,right):box('Door stile' if door else 'Panel stile',(x,yy,(bottom+top)/2),(.045,.054,top-bottom),wear=.6 if door else .34,rust=.17)
    for z in (bottom,top):box('Panel return rail',((left+right)/2,yy,z),(right-left,.054,.044),wear=.5,rust=.23)
    if bottom<.2:
        box('Latch height stiffener',((left+right)/2,yy,1.03),(right-left,.04,.032),wear=.36,rust=.18)
        # Folded kick plate with a narrow raised top return and corner screws.
        box('Kick plate',((left+right)/2,yy+.018,.187),(right-left-.052,.012,.138),wear=.20,rust=.52)
        box('Kick plate folded lip',((left+right)/2,yy+.011,.256),(right-left-.044,.025,.012),wear=.6,rust=.44)
    xl,xr=left+.022,right-.022;zl,zt=bottom+.022,top-.022
    nx=max(1,round((xr-xl)/.125));nz=max(1,round((zt-zl)/.13))
    xs=[xl+(xr-xl)*i/nx for i in range(1,nx)]
    zs=[zl+(zt-zl)*i/nz for i in range(1,nz)]
    for x in xs:
        rod('Round vertical wire',(x,yy+.009,zl),(x,yy+.009,zt),.004)
        for z in (zl,zt):bead('Wire to frame weld',[(x-.006+j*.002,yy+.004,z) for j in range(7)],.0018)
    for z in zs:rod('Cross wire',(xl,yy+.016,z),(xr,yy+.016,z),.0038)
    for i,x in enumerate(xs):
        for j,z in enumerate(zs):
            if (i+j)%3==0:rod('Spot welded intersection',(x,yy+.009,z),(x,yy+.020,z),.0053,'Weld',8,.15,.36)
    for x in (left,right):
        for z in (bottom,top):
            bead('Frame corner weld',[(x-.018+j*.003,yy-.028,z+(.018 if z==bottom else -.018)) for j in range(13)])

panel(8.394,10.521,.13,2.010,True)
panel(10.674,12.606,.13,2.010)
panel(8.379,10.541,2.125,2.911)
panel(10.659,12.621,2.125,2.911)

# Three split hinge knuckles have real parting gaps and a capped steel pin.
for z in (.39,1.10,1.78):
    box('Hinge fixed leaf',(8.344,y-.063,z),(.050,.014,.095),wear=.65,rust=.45)
    box('Hinge door leaf',(8.399,y-.063,z),(.055,.014,.095),wear=.7,rust=.42)
    for dz in (-.035,0,.035):rod('Hinge barrel',(8.373,y-.075,z+dz-.015),(8.373,y-.075,z+dz+.015),.014,'Steel',20,.45,.35)
    rod('Hinge pin cap',(8.373,y-.075,z+.053),(8.373,y-.075,z+.060),.017,'Steel',24,.6,.2)
    for x in (8.34,8.401):bolt(x,y-.075,z)

# Mortise lock box and keeper meet across the deliberate door reveal.
box('Latch reinforcement',(10.476,y-.019,1.22),(.116,.046,.264),wear=.65,rust=.3)
box('Lock face',(10.476,y-.047,1.22),(.091,.016,.20),'Steel',.002,.6,.1)
box('Keeper bracket',(10.557,y-.025,1.20),(.080,.074,.122),wear=.70,rust=.30)
box('Keeper shadow slot',(10.534,y-.064,1.20),(.016,.003,.066),'Dark',.001)
rod('Latch spindle',(10.48,y-.061,1.254),(10.48,y-.096,1.254),.014,'Steel',24,.95,.05)
rod('Lever handle',(10.48,y-.096,1.254),(10.372,y-.104,1.252),.010,'Steel',20,.95,.04)
rod('Lock escutcheon',(10.477,y-.057,1.170),(10.477,y-.065,1.170),.019,'Steel',32,.8,.09)
rod('Key opening',(10.477,y-.0652,1.174),(10.477,y-.066,1.174),.004,'Dark',16,0,0)
box('Key slot',(10.477,y-.066,1.165),(.004,.001,.012),'Dark',.0005)
for z in (1.134,1.304):bolt(10.477,y-.057,z)

# UV density is physical; vertex masks locate wear, damp dust and corrosion.
for o in parts:
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    mesh=o.data
    if o.data.materials[0].name=='GateWater_Paint':
        bm=bmesh.new();bm.from_mesh(mesh);edges=[e for e in bm.edges if e.calc_length()>.1]
        if edges:bmesh.ops.subdivide_edges(bm,edges=edges,cuts=min(24,max(2,int(max(o.dimensions)/.1))),use_grid_fill=True)
        bm.to_mesh(mesh);bm.free();mesh.update()
    uv=mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap');vc=mesh.color_attributes.new(name='Wear',type='BYTE_COLOR',domain='CORNER')
    low=[min(v.co[i] for v in mesh.vertices) for i in range(3)];high=[max(v.co[i] for v in mesh.vertices) for i in range(3)]
    for f in mesh.polygons:
        axes=sorted(range(3),key=lambda i:abs(f.normal[i]))[:2]
        for li in f.loop_indices:
            v=mesh.vertices[mesh.loops[li].vertex_index].co;w=o.matrix_world@v
            uv.data[li].uv=(w[axes[0]]/.45,w[axes[1]]/.45)
            d=sorted(min(abs(v[i]-low[i]),abs(high[i]-v[i])) for i in range(3))
            edge=max(0,1-d[1]/.009)*o['wear'];damp=max(0,1-w.z/.52)
            vc.data[li].color=(edge,damp*.4,min(1,o['rust']+damp*.48),1)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();gate=bpy.context.object;gate.name='SM_DungeonRefinedGrille'
bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

# A smooth, irregular outline and concentric rings provide continuous shore masks.
verts=[];faces=[];attributes=[];uvs=[];N=96;rings=[.0,.18,.38,.60,.76,.86,.92,.96,1.0]
for p in CFG['puddles']:
    cx,cy=p['center_m'];radius=p['radius_m'];phase=p['phase']*math.tau
    center=len(verts);verts.append((cx,cy,CFG['water_height_m']));attributes.append((1,p['phase'],p['drip_strength'],1));uvs.append((0,0))
    for k,q in enumerate(rings[1:]):
        start=len(verts)
        for i in range(N):
            a=i*math.tau/N
            shape=1+.075*math.sin(a*3+phase)+.060*math.cos(a*5-phase)+.032*math.sin(a*9+phase*.7)
            dx=q*radius*1.8*shape*math.cos(a);dy=q*radius*.48*shape*math.sin(a)
            verts.append((cx+dx,cy+dy,CFG['water_height_m']));uvs.append((dx,dy))
            edge=max(0,min(1,(1-q)/.14));edge=edge*edge*(3-2*edge)
            attributes.append((edge,p['phase'],p['drip_strength'],1))
        if k==0:
            for i in range(N):faces.append((center,start+i,start+(i+1)%N))
        else:
            prev=start-N
            for i in range(N):j=(i+1)%N;faces.append((prev+i,start+i,start+j,prev+j))
mesh=bpy.data.meshes.new('Shallow water shores');mesh.from_pydata(verts,[],faces);mesh.update()
water=bpy.data.objects.new('SM_DungeonShallowPuddles',mesh);bpy.context.collection.objects.link(water);mesh.materials.append(materials['Water'])
uv=mesh.uv_layers.new(name='UVMap');vc=mesh.color_attributes.new(name='Wear',type='BYTE_COLOR',domain='CORNER')
for f in mesh.polygons:
    for li in f.loop_indices:
        i=mesh.loops[li].vertex_index;uv.data[li].uv=uvs[i];vc.data[li].color=attributes[i]
manifest={'source_blend':str(OUT/'DungeonGateWater_Source.blend'),'materials':recipes,'meshes':[],'config':CFG,'tests_run':False}
for o,actor,old,collision in [(gate,CFG['gate']['actor'],CFG['gate']['old_mesh'],True),(water,CFG['water_actor'],CFG['old_water_mesh'],False)]:
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Export triangulation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    fbx=OUT/(o.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,colors_type='LINEAR')
    manifest['meshes'].append(dict(name=o.name,fbx=str(fbx),actor=actor,old_mesh=old,collision=collision))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=manifest['source_blend'])
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('GATE_AND_PUDDLE_SOURCES_AUTHORED_NO_RENDER')
