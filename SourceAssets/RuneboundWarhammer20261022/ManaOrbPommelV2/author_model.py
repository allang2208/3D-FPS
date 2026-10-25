"""Approved exposed-crystal design: sculpted silver talons and contained 3D mana.

Production modelling and PBR baking only; no acceptance render or game startup.
"""
import bpy,bmesh,types,math,json,sys,random
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;FAMILY=P.parent
code=(FAMILY/'FinalTollHammerHeadV2/author_model.py').read_text('utf-8')
m=types.ModuleType('orb_surface_tools');m.__file__=str(P/'author_model.py')
exec(compile(code,'<retained_surface_tools>','exec'),m.__dict__)
m.initialize();bpy.context.preferences.filepaths.save_version=0
sys.path.insert(0,str(FAMILY/'HeadRunePBRV3'))
from surface_authoring import refine_metal
for mat in (m.STEEL,m.SILVER):refine_metal(mat)
R=.0405;CENTER=Vector((0,0,-.087));rng=random.Random(102424)
energy=m.simple_material('M_ManaOrbV2_Rune',(.19,.008,.42),0.,.26)
p=energy.node_tree.nodes.get('Principled BSDF');p.inputs['Emission Color'].default_value=(.38,.018,1,1);p.inputs['Emission Strength'].default_value=1.6
glass=m.simple_material('M_ManaOrbV2_Glass',(.19,.035,.4),0.,.085)
p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Transmission Weight'].default_value=.96;p.inputs['IOR'].default_value=1.44;p.inputs['Coat Weight'].default_value=.4
gem=m.simple_material('M_ManaOrbV2_Gem',(.105,.005,.31),.28,.095)
p=gem.node_tree.nodes.get('Principled BSDF');p.inputs['Coat Weight'].default_value=.55;p.inputs['Emission Color'].default_value=(.14,.004,.38,1);p.inputs['Emission Strength'].default_value=.45
core=m.simple_material('M_ManaOrbV2_Core',(.4,.06,.7),0.,.18)
p=core.node_tree.nodes.get('Principled BSDF');p.inputs['Emission Color'].default_value=(.6,.12,1,1);p.inputs['Emission Strength'].default_value=5.
volume=m.simple_material('M_ManaOrbV2_Volume',(.035,.002,.1),0.,.3)
p=volume.node_tree.nodes.get('Principled BSDF');p.inputs['Transmission Weight'].default_value=.92;p.inputs['Alpha'].default_value=.12
filament=m.simple_material('M_ManaOrbV2_Filaments',(.35,.02,.8),0.,.2)
p=filament.node_tree.nodes.get('Principled BSDF');p.inputs['Emission Color'].default_value=(.48,.045,1,1);p.inputs['Emission Strength'].default_value=3.
sparks=m.simple_material('M_ManaOrbV2_Particles',(.6,.16,1),0.,.2)
p=sparks.node_tree.nodes.get('Principled BSDF');p.inputs['Emission Color'].default_value=(.7,.24,1,1);p.inputs['Emission Strength'].default_value=4.
optical=[];internal=[]

# Native pivot, UV and the shaft-facing interface are retained verbatim.
factory=bpy.data.objects['SM_RuneboundWarhammer_pommel_factory']
collar=factory.copy();collar.data=factory.data.copy();m.BUILD.objects.link(collar)
collar.name='Native_shaft_interface_2mm';collar.hide_render=False;collar.hide_set(False);collar.location=(0,0,0)
bm=bmesh.new();bm.from_mesh(collar.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,-.002),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z+.002)<.00001 for v in e.verts)]
if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
bm.to_mesh(collar.data);bm.free();m.PARTS.append(collar)

def catmull(keys,t):
    x=max(0.,min(.999999,t))*(len(keys)-1);i=int(x);s=x-i
    a=Vector(keys[max(i-1,0)]);b=Vector(keys[i]);c=Vector(keys[min(i+1,len(keys)-1)]);d=Vector(keys[min(i+2,len(keys)-1)])
    return .5*((2*b)+(-a+c)*s+(2*a-5*b+4*c-d)*s*s+(-a+3*b-3*c+d)*s*s*s)

neck_sections=[(.0185,-.002),(.0188,-.006),(.0179,-.013),(.0182,-.021),(.0208,-.029),(.0257,-.038),(.0262,-.040)]
def neck(t,x,depth=0):
    r,z=catmull(neck_sections,t);a=x
    flute=1.+.028*math.cos(6*a)
    return Vector(((r*flute+depth)*math.cos(a),(r*flute+depth)*math.sin(a),z))
verts=[neck(j/64,math.tau*i/120) for j in range(65) for i in range(120)]
faces=[]
for j in range(64):
    for i in range(120):k=(i+1)%120;faces.append((j*120+i,j*120+k,(j+1)*120+k,(j+1)*120+i))
faces += [tuple(reversed(range(120))),tuple(64*120+i for i in range(120))]
neck_obj=m.solid('Fluted_tapered_socket',verts,faces,m.STEEL)
for z,r,w in [(-.004,.0189,.001),(-.008,.0188,.00055),(-.039,.0262,.0008)]:
    m.annulus('Fine_silver_socket_lip',m.frame((0,0,z),(0,0,1),(1,0,0)),r-.001,r+.00035,-w/2,w/2,m.SILVER,count=120,bevel=.00016)
for i in range(6):
    a=math.tau*i/6
    m.stroke('Socket_panel_border', [neck(.13+.8*j/64,a,.00018) for j in range(65)],.00045,m.SILVER,8)

def engrave(obj,name,paths):
    cutters=[]
    for i,points in enumerate(paths):
        # A closed rune must be a closed tubular loop, without coincident end
        # caps. Capped open strokes at a repeated endpoint invert boolean solids.
        pts=[Vector(p) for p in points[:-1]];verts=[];faces=[];sides=8
        for j,point in enumerate(pts):
            tangent=(pts[(j+1)%len(pts)]-pts[(j-1)%len(pts)]).normalized()
            helper=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
            u=tangent.cross(helper).normalized();v=tangent.cross(u).normalized()
            verts.extend(point+.00036*(u*math.cos(k*math.tau/sides)+v*math.sin(k*math.tau/sides)) for k in range(sides))
        for j in range(len(pts)):
            for k in range(sides):faces.append((j*sides+k,j*sides+(k+1)%sides,((j+1)%len(pts))*sides+(k+1)%sides,((j+1)%len(pts))*sides+k))
        m.solid(name+'_closed_cutter_'+str(i),verts,faces,m.BLACK,group=cutters)
    cut=m.join_group(cutters,name+'_joined_cutters');m.activate(obj)
    mod=obj.modifiers.new('Recessed rune cuts 0.25mm','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;mod.use_self=True
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)

# Every neck engraving follows its fluted surface; luminous inlay sits below it.
paths=[]
for i in range(6):
    a=math.tau*(i+.5)/6
    for j in range(3):
        t=.26+j*.185;shape=[(-.055,t), (0,t-.07),(.055,t),(0,t+.07),(-.055,t)]
        paths.append([neck(v,a+u,.00012) for u,v in shape])
        m.stroke('Socket_inset_rune',[neck(v,a+u,-.00007) for u,v in shape],.00015,energy,8,m.ENERGY)
engrave(neck_obj,'Socket',paths)

talon_keys=[(.019,-.023),(.0263,-.041),(.034,-.061),(.0426,-.083),(.0394,-.105),(.0265,-.122),(.012,-.130),(.002,-.136)]
def talon_frame(t,a):
    r,z=catmull(talon_keys,t);b=catmull(talon_keys,min(1,t+.001))-catmull(talon_keys,max(0,t-.001))
    normal=Vector((-b.y,b.x)).normalized();ang=a+.13*math.sin(t*math.tau)
    return r,z,ang,normal
def talon(t,x,d,a):
    r,z,ang,n=talon_frame(t,a);ang+=x/max(r,.005)
    return Vector(((r+n.x*d)*math.cos(ang),(r+n.x*d)*math.sin(ang),z+n.y*d))
def width(t):return .00035+(.0048+.002*math.sin(3*math.pi*t)**2)*math.sin(math.pi*t)**.65
for i,degrees in enumerate((-155,-25,90)):
    a=math.radians(degrees);count=113;verts=[]
    for j in range(count):
        t=j/(count-1);w=width(t)
        for u,d in [(-.77,-.0009),(.77,-.0009),(1,-.00055),(1,.0006),(.77,.0011),(-.77,.0011),(-1,.0006),(-1,-.00055)]:
            verts.append(talon(t,u*w,d,a))
    faces=[tuple(reversed(range(8)))]
    for j in range(count-1):
        for k in range(8):faces.append((j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k))
    faces.append(tuple((count-1)*8+k for k in range(8)))
    obj=m.solid('Sculpted_swept_talon_'+str(i),verts,faces,m.SILVER)
    obj.data.materials.append(m.STEEL)
    for face in obj.data.polygons:
        if face.index>0 and face.index<len(faces)-1 and (face.index-1)%8==4:face.material_index=1
    paths=[]
    for j in range(7):
        t=.12+j*.101
        # Long diamonds linked by an angular stem, visible from every side.
        shape=[(-.00115,t),(0,t-.025),(.00115,t),(0,t+.025),(-.00115,t)]
        paths.append([talon(v,u,.00121,a) for u,v in shape])
        m.stroke('Talon_recessed_violet_inlay',[talon(v,u,.00102,a) for u,v in shape],.00015,energy,8,m.ENERGY)
    engrave(obj,'Talon_'+str(i),paths)
    # Thin edge chasing is real silver relief beside a wide recessed dark face.
    for side in (-1,1):
        m.stroke('Hand_chased_talon_edge',[talon(.035+.93*j/95,side*width(.035+.93*j/95)*.74,.00119,a) for j in range(96)],.00017,m.SILVER,6)

def medallion(name,f,sx,sy):
    outline=[(0,sy),(.42*sx,.36*sy),(sx,0),(.42*sx,-.34*sy),(0,-sy),(-.42*sx,-.34*sy),(-sx,0),(-.42*sx,.36*sy)]
    m.strip(name+'_solid_silver_frame',f,outline,-.0011,.0010,m.SILVER,.00022)
    m.strip(name+'_dark_recess',f,[(x*.79,y*.79) for x,y in outline],.0010,.00135,m.BLACK,.00013)
    # Faceted crystal has a girdle, crown and tiny table, never a flat decal.
    diamond=[(0,sy*.62),(sx*.56,0),(0,-sy*.62),(-sx*.56,0)]
    verts=[m.pt(f,x,y,d) for d,s in ((.0011,1.),(.0022,.78),(.0031,.19)) for x,y in [(x*s,y*s) for x,y in diamond]]
    faces=[(3,2,1,0),(8,9,10,11)]
    for j in range(2):
        for k in range(4):faces.append((4*j+k,4*j+(k+1)%4,4*(j+1)+(k+1)%4,4*(j+1)+k))
    obj=m.solid(name+'_faceted_amethyst',verts,faces,gem,group=optical)
    for poly in obj.data.polygons:poly.use_smooth=False
    for side in (-1,1):
        m.stroke(name+'_inner_edge',[m.pt(f,side*x*.71,y*.71,.00155) for x,y in [(0,sy),(.7*sx,0),(0,-sy)]],.0002,m.SILVER,8)

front=-math.pi/2
for i,a in enumerate((front,front+2*math.pi/3,front+4*math.pi/3)):
    radial=Vector((math.cos(a),math.sin(a),0));circ=Vector((-math.sin(a),math.cos(a),0))
    f=m.frame(radial*.0255+Vector((0,0,-.046)),radial*.94+Vector((0,0,.34)),circ)
    medallion('Crown_kite_'+str(i),f,.008,.016)
    f=m.frame(radial*.017+Vector((0,0,-.125)),radial*.68+Vector((0,0,-.73)),circ)
    medallion('Heel_kite_'+str(i),f,.007,.015)
    # Swept pointed leaves join the talons beneath the sphere, leaving openings.
    for s in (-1,1):
        f=m.frame(radial*.015+Vector((0,0,-.128)),radial*.65+Vector((0,0,-.76)),circ)
        outline=[(s*.003,-.010),(s*.014,-.002),(s*.020,.009),(s*.011,.004),(s*.006,.006)]
        m.strip('Pierced_heel_leaf',f,outline,-.001,.001,m.SILVER,.0003)

def sphere(name,r,mat,group,segments=96,rings=64):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,radius=r,location=CENTER)
    obj=bpy.context.object;obj.name=name;obj.data.materials.append(mat)
    for face in obj.data.polygons:face.use_smooth=True
    group.append(obj);return obj
sphere('Optical_violet_crystal_shell',R,glass,optical,128,96)
sphere('Contained_raymarched_nebula_proxy',R*.965,volume,internal,64,40)
sphere('Pulsing_mana_heart',.0042,core,internal,48,32)

# Physical, bounded inner filaments. UV.x carries travelling light packets.
for k in range(5):
    points=[]
    for j in range(161):
        t=j/160;a=t*math.tau*(1.7+.13*k)+k*1.2566
        r=.006+.020*math.sin(math.pi*t)**.7
        local=Vector((r*math.cos(a),r*math.sin(a),(.023*(t-.5))*math.sin(k+1)))
        # Fixed differently tilted orbits; animated rotation happens in material.
        from mathutils import Matrix
        local=Matrix.Rotation(.43*k,3,'X')@local
        points.append(CENTER+local)
    obj=m.stroke('Inner_mana_filament_'+str(k),points,.00012 if k%2 else .00017,filament,6,internal)
    uv=obj.data.uv_layers.new(name='UVMap')
    for poly in obj.data.polygons:
        for loop in poly.loop_indices:
            idx=obj.data.loops[loop].vertex_index;uv.data[loop].uv=(idx//6/160,idx%6/6)
for i in range(32):
    v=Vector((rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(-1,1))).normalized()*rng.uniform(.010,.032)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=rng.uniform(.00012,.0003),location=CENTER+v)
    obj=bpy.context.object;obj.name='Orbiting_contained_spark_'+str(i);obj.data.materials.append(sparks)
    color=obj.data.color_attributes.new(name='Color',type='BYTE_COLOR',domain='CORNER')
    phase=rng.random()
    for c in color.data:c.color=(phase,.3+.6*rng.random(),.5,1)
    internal.append(obj)

design=json.loads((FAMILY/'ManaOrbPommelConceptV2/design.json').read_text('utf-8'))
design.update(status='approved_for_detailed_modeling',approval='User: 按设计图进行精细化建模，同时魔法球内附加特效',model_revision='ManaOrbPommelV2')
(FAMILY/'ManaOrbPommelConceptV2/design.json').write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'ManaOrbPommel_Construction.blend'))
metal=m.join_group(m.PARTS,'Sculpted_blackened_silver_setting');m.unwrap(metal)
start=code.index('def bake_maps(');end=code.index('\ndef finalize(',start)
bake=code[start:end].replace('T_FinalToll_','T_ManaOrbV2_').replace('M_FinalToll_PBR_Surface','M_ManaOrbV2_Metal')
exec(compile(bake,'<4k_forged_silver_bake>','exec'),m.__dict__);m.bake_maps(metal)
runes=m.join_group(m.ENERGY,'Recessed_violet_rune_inlays');m.unwrap(runes)
final=m.join_group([metal,runes]+optical+internal,'SM_Runebound_EmpoweredManaOrb_V2')
# Baking/joining never moves the retained factory pivot.
final.location=(0,0,0);final['installation_offset_cm']=[0,0,-8.5];final['exclusive_weapon']='ue_runebound_warhammer'
for obj in list(bpy.context.scene.objects):
    if obj!=final:bpy.data.objects.remove(obj,do_unlink=True)
m.activate(final)
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(final.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='COPY',embed_textures=False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'ManaOrbPommel_Editable.blend'))
final.data.calc_loop_triangles()
receipt={'mesh':final.name,'fbx':str(P/'Export'/(final.name+'.fbx')),'materials':[v.name for v in final.data.materials],'triangles':len(final.data.loop_triangles),'location_cm':[0,0,-8.5],'interface':'factory upper 2 mm retained','source':str(P/'ManaOrbPommel_Editable.blend'),'concept':str(FAMILY/'ManaOrbPommelConceptV2/empowered_mana_orb_design_01.png'),'pbr_resolution':4096,'normal_convention':'OpenGL tangent normal; flip green on UE import','orb_center_cm':[0,0,-8.7],'orb_radius_cm':4.05,'vfx':['contained 24-step nebula','pulsing core','5 rotating 3D filaments','32 orbiting sparks'],'tested':False}
(P/'production_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('APPROVED_MANA_ORB_V2_EXPORTED',flush=True)
