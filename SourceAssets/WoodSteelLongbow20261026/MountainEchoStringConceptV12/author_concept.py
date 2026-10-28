"""Requested concept sheet: one legendary string, three views and macro details."""
from pathlib import Path
import bpy,math,json
from mathutils import Vector

P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
font=bpy.data.fonts.load('C:/Windows/Fonts/msyh.ttc')

def material(name,rgb,metal=0,rough=.5,emission=0,texture=False):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;n.clear();l=m.node_tree.links
    out=n.new('ShaderNodeOutputMaterial')
    if emission:
        bs=n.new('ShaderNodeEmission');bs.inputs[0].default_value=(*rgb,1);bs.inputs[1].default_value=emission
    else:
        bs=n.new('ShaderNodeBsdfPrincipled');bs.inputs['Base Color'].default_value=(*rgb,1)
        bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
        if texture:
            tc=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=190;noise.inputs['Detail'].default_value=2
            l.new(tc.outputs['Generated'],noise.inputs['Vector']);bump=n.new('ShaderNodeBump')
            bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.012
            l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
    l.new(bs.outputs[0],out.inputs['Surface']);return m

silver=material('Silver grey braided fibres',(.40,.46,.49),.25,.42,texture=True)
charcoal=material('Graphite braided fibres',(.045,.052,.058),.05,.59,texture=True)
gold=material('Antique gold filament',(.40,.22,.065),.78,.32,texture=True)
steel=material('Satin silver sleeve',(.50,.57,.60),.85,.29,texture=True)
serving=material('Charcoal finger serving',(.024,.029,.033),0,.70,texture=True)
glow=material('Warm gold resonance',(.72,.30,.055),emission=2.1)
ink=material('Charcoal lettering',(.055,.069,.076),emission=1)
muted=material('Secondary lettering',(.09,.12,.135),emission=1)
accent=material('Muted brass typography',(.23,.12,.035),emission=1)
rule=material('Fine drawing rules',(.48,.50,.49),emission=1)
paper=material('Warm grey paper',(.79,.80,.77),emission=1)

def curve(name,pts,radius,mat,parent=None,closed=False):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.resolution_u=1;data.bevel_depth=radius;data.bevel_resolution=3
    s=data.splines.new('POLY');s.points.add(len(pts)-1)
    for p,xyz in zip(s.points,pts):p.co=(*xyz,1)
    s.use_cyclic_u=closed;data.materials.append(mat)
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.parent=parent;return o

def text(body,x,z,size=.30,mat=ink,align='LEFT'):
    d=bpy.data.curves.new(body,'FONT');d.body=body;d.font=font;d.size=size;d.align_x=align
    o=bpy.data.objects.new(body,d);scene.collection.objects.link(o);o.location=(x,-1.1,z);o.rotation_euler=(math.pi/2,0,0);d.materials.append(mat);return o

def line(name,points,mat=rule,r=.007):return curve(name,[(x,-1.0,z) for x,z in points],r,mat)

def root(name,loc,scale=1,rotation=(0,0,0)):
    o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.location=loc;o.scale=(scale,)*3;o.rotation_euler=rotation;return o

def tube(name,z,rad,depth,mat,parent):
    bpy.ops.mesh.primitive_cylinder_add(vertices=40,radius=rad,depth=depth,location=(0,0,z))
    o=bpy.context.object;o.name=name;o.data.materials.append(mat);o.parent=parent
    for f in o.data.polygons:f.use_smooth=True
    b=o.modifiers.new('Soft machined edges','BEVEL');b.width=.006;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return o

def braid(parent,start,end,phase=0):
    count=max(16,int((end-start)*90))
    curve('Flexible graphite core',[(0,0,start),(0,0,end)],.026,charcoal,parent)
    for j in range(8):
        pts=[]
        for i in range(count+1):
            z=start+(end-start)*i/count;a=z*math.tau*4.5+j*math.tau/8+phase
            rad=.038+.003*math.cos(z*math.tau*9)
            pts.append((rad*math.cos(a),rad*math.sin(a),z))
        curve('Interlaced silver fibre' if j%2==0 else 'Interlaced graphite fibre',pts,.014,silver if j%2==0 else charcoal,parent)
    pts=[]
    for i in range(count+1):
        z=start+(end-start)*i/count;a=-z*math.tau*3.0+phase
        pts.append((.051*math.cos(a),.051*math.sin(a),z))
    curve('Fine buried gold filament',pts,.0045,gold,parent)

def end_loop(parent,sign):
    # The loop remains woven and flexible; the short sleeve only binds its neck.
    for j in range(4):
        pts=[]
        for i in range(181):
            a=i*math.tau/180
            x=.145*math.sin(a);z=sign*(4.0+.31*math.cos(a))
            twist=a*15+j*math.pi/2
            pts.append((x+.014*math.cos(twist),.014*math.sin(twist),z))
        curve('Woven end loop',pts,.011,silver if j%2==0 else charcoal,parent,True)
    tube('Tapered silver loop neck',sign*3.70,.066,.22,steel,parent)
    for dz in [-.095,.095]:tube('Brass neck edge',sign*3.70+dz,.071,.018,gold,parent)
    # Shallow three-peak motif remains attached to the neck surface.
    pts=[(-.046,-.062,sign*3.70-.025),(-.025,-.070,sign*3.70+.025),(0,-.072,sign*3.70-.008),(.022,-.070,sign*3.70+.04),(.047,-.062,sign*3.70-.025)]
    curve('Three peak loop engraving',pts,.004,gold,parent)

def center_serving(parent):
    tube('Soft finger contact core',0,.062,.72,serving,parent)
    pts=[]
    for i in range(641):
        z=-.36+.72*i/640;a=i/640*math.tau*45
        pts.append((.063*math.cos(a),.063*math.sin(a),z))
    curve('Close wound finger protection',pts,.0085,serving,parent)
    for z in [-.37,.37]:tube('Bound serving edge',z,.064,.025,charcoal,parent)
    # Narrow nocking locator above the finger path, no rigid protruding centerpiece.
    for z in [.075,.115]:tube('Nocking locator thread',z,.069,.012,gold,parent)

def marks(parent,lit=0):
    for k,z in enumerate([.62,.84,1.06]):
        mat=glow if k<lit else gold
        for delta in [-.012,.012]:
            curve('Resonance woven chevron '+str(k+1),[(-.038,-.049,z+.025+delta),(0,-.057,z+delta),(.038,-.049,z+.025+delta)],.006,mat,parent)

def complete_string(name,x,angle):
    p=root(name,(x,0,-.1),rotation=(0,0,angle));braid(p,-3.72,3.72);end_loop(p,1);end_loop(p,-1);center_serving(p);marks(p)
    return p

# Three views are generated from the same construction at exactly the same scale.
for title,x,angle in [('正面',-9.6,0),('侧面',-7.55,math.pi/2),('背面',-5.5,math.pi)]:
    complete_string('Full string '+title,x,angle)
    text(title,x,4.48,.26,muted,'CENTER');text('同尺度',x,-4.85,.18,muted,'CENTER')

# Enlarged detail studies use the same functions and material definitions.
upper=root('Detail upper woven loop',(-1.8,0,2.85),2.7)
braid(upper,-.44,.0)
# Shift the common end-loop geometry into this local detail window.
end_loop(upper,1)
for obj in list(upper.children):
    if obj.name.startswith(('Flexible','Interlaced','Fine buried')):continue
    obj.location.z-=3.70
    if obj.type=='CURVE':
        for spline in obj.data.splines:
            for p in spline.points:p.co.z-=3.70
        obj.location.z+=3.70

detail_braid=root('Detail braided resonance section',(5.9,0,3.18),5.4,rotation=(0,math.pi/2,0))
braid(detail_braid,.42,1.26);marks(detail_braid,2)
# Center that cropped section after its common-axis rotation.
detail_braid.location.x-=.84*5.4

center=root('Detail finger serving',(3.65,0,.02),5.5,rotation=(0,math.pi/2,0))
braid(center,-.72,.72);center_serving(center)

for count,x in enumerate([-.9,2.0,4.9,7.8]):
    p=root('State '+str(count),(x-.84*2.5,0,-3.15),2.5,rotation=(0,math.pi/2,0))
    braid(p,.48,1.22);marks(p,count)
    text(['静止','弦鸣 Ⅰ','弦鸣 Ⅱ','弦鸣 Ⅲ'][count],x,-3.87,.24,accent if count else muted,'CENTER')
    if count==3:
        curve('Fine full charge filament',[(x-.92,-.13,-3.15),(x+.92,-.13,-3.15)],.006,glow)

# Editorial layout: all labels horizontal and outside the object silhouettes.
text('山鸣弓弦',-10.85,5.78,.64)
text('高地长弓  /  传说级弓弦改造  /  设计提案',-5.95,5.91,.265,muted)
text('MOUNTAIN ECHO',10.8,5.93,.22,accent,'RIGHT')
line('Header rule',[(-10.85,5.38),(10.85,5.38)])
text('01  /  完整形态',-10.85,4.88,.29,accent)
line('Column divider',[(-3.88,4.93),(-3.88,-5.06)])
text('02  /  山纹弦耳',-3.25,4.88,.29,accent)
text('03  /  银灰复编与金丝纹路',2.55,4.88,.29,accent)
line('Upper detail divider',[(1.35,4.48),(1.35,1.65)])
text('柔性编织弦圈',-.98,3.86,.23)
text('短银钢套',-.98,2.25,.23)
text('旧金山纹',-.98,1.85,.21,muted)
line('Loop leader',[(-.98,3.62),(-1.12,3.62),(-1.33,3.78)])
line('Sleeve leader',[(-.98,2.56),(-1.1,2.56),(-1.6,2.83)])
text('细金丝嵌入银灰纤维',2.55,2.12,.25)
text('三道织入纹逐层点亮，保持细弦轮廓',2.55,1.70,.21,muted)
line('Macro division',[(-3.25,1.24),(10.85,1.24)])
text('04  /  护指缠线与搭箭定位',-3.25,.79,.29,accent)
text('哑黑软缠线',-.3,-.94,.23)
text('窄金色定位线',5.2,-.94,.23)
line('Serving leader',[(1.25,-.73),(1.25,-.39),(2.8,-.29)])
line('Nock leader',[(6.25,-.73),(6.25,-.48),(4.20,-.29)])
text('指腹接触区保持平滑；装饰位于接触区之外',-3.25,-1.44,.21,muted)
line('State division',[(-3.25,-1.87),(10.85,-1.87)])
text('05  /  弦鸣蓄积',-3.25,-2.34,.29,accent)
text('满弓命中 → 三段渐亮 → 下一箭释放余响',-3.25,-4.58,.265)
text('暖金细光与短促双线余辉，保留瞄准视野',-3.25,-5.04,.21,muted)
line('Footer rule',[(-10.85,-5.55),(10.85,-5.55)])
text('概念材质：银灰复编纤维 / 哑黑护指缠线 / 旧金细丝 / 银钢弦耳',-10.85,-6.0,.23,muted)
text('原生三维设计板 · 非游戏实机画面',10.85,-6.0,.20,muted,'RIGHT')

bpy.ops.mesh.primitive_plane_add(size=200,location=(0,1.2,0),rotation=(math.pi/2,0,0))
bpy.context.object.name='Concept paper';bpy.context.object.data.materials.append(paper)
for name,loc,power,size in [('Key',(-6,-8,7),1700,6),('Fill',(8,-6,2),1100,5),('Rim',(3,1,6),900,4)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o)
    o.location=loc;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True
next(n for n in world.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.65;scene.world=world
data=bpy.data.cameras.new('Concept camera');data.type='ORTHO';data.ortho_scale=23.3
cam=bpy.data.objects.new('Concept camera',data);scene.collection.objects.link(cam);cam.location=(0,-30,0);cam.rotation_euler=(math.pi/2,0,0);scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=2800;scene.render.resolution_y=1680;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(P/'MountainEcho_String_Concept_v1.png')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'MountainEcho_String_Concept_v1.blend'))
bpy.ops.render.render(write_still=True)
meta=json.loads((P/'design.json').read_text(encoding='utf-8'))
meta.update({'generated_by':'Blender native 3D concept sheet','image':'MountainEcho_String_Concept_v1.png',
 'editable_source':'MountainEcho_String_Concept_v1.blend','imagegen_result':'Output rejected by the image service; no generated image used',
 'imagegen_request_id':'417471b9-d3f0-4505-8393-b08e4f7a54d9','stage':'concept_and_effect_proposal_complete'})
(P/'design.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print('MOUNTAIN_ECHO_CONCEPT_SAVED',flush=True)
