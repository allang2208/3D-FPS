"""Manufacture the worktop, lamp shell and routed flex in workshop-local metres."""
from pathlib import Path
import bpy,json,math,random
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';BASE=ROOT.parent
SCULPT=BASE/'DungeonWorkshopSculpt20260921';SURFACE=BASE/'DungeonWorkshopSurface20260921'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
MATS={};aliases={};R=random.Random(219215)
with bpy.data.libraries.load(str(SCULPT/'Authored/DungeonWorkshopComponents.blend'),link=False) as (src,dst):
    dst.materials=['WSSculpt_Machined']
MATS['Machined']=dst.materials[0]
aliases[MATS['Machined'].name]=json.loads((SCULPT/'Receipts/asset-import.json').read_text())['materials']['Machined']
recipes=json.loads((OUT/'material-manifest.json').read_text())
for key,r in recipes.items():
    m=bpy.data.materials.new('WSBench_'+key);m.use_nodes=True;N=m.node_tree.nodes;L=m.node_tree.links;p=next(n for n in N if n.type=='BSDF_PRINCIPLED')
    p.inputs['Metallic'].default_value=r.get('metallic',0);p.inputs['Roughness'].default_value=r.get('roughness',.6)
    if 'color' in r:p.inputs['Base Color'].default_value=(*r['color'],1)
    if 'emission' in r:p.inputs['Emission Color'].default_value=(*r['emission'],1);p.inputs['Emission Strength'].default_value=1
    for ch,path in r.get('maps',{}).items():
        t=N.new('ShaderNodeTexImage');t.image=bpy.data.images.load(path,check_existing=True)
        if ch!='BaseColor':t.image.colorspace_settings.name='Non-Color'
        if ch=='Normal':
            n=N.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=r.get('normal_strength',1);L.new(t.outputs['Color'],n.inputs['Color']);L.new(n.outputs['Normal'],p.inputs['Normal'])
        elif ch=='BaseColor':
            mul=N.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=(*r.get('color_tint',[1,1,1]),1)
            L.new(t.outputs['Color'],mul.inputs[1]);L.new(mul.outputs[0],p.inputs['Base Color'])
        elif ch=='Roughness':
            n=N.new('ShaderNodeMath');n.operation='MULTIPLY_ADD';n.inputs[1].default_value=r.get('roughness_scale',1);n.inputs[2].default_value=r.get('roughness_bias',0)
            L.new(t.outputs['Color'],n.inputs[0]);L.new(n.outputs[0],p.inputs['Roughness'])
        elif ch=='Metallic':L.new(t.outputs['Color'],p.inputs['Metallic'])
    MATS[key]=m
exec(compile((SURFACE/'Scripts/modeling.py').read_text(),'modeling.py','exec'),globals())

# Preserve the accepted planar top and its physical height. Rework each plank's UV islands.
with bpy.data.libraries.load(str(SCULPT/'Authored/DungeonWorkshopComponents.blend'),link=False) as (src,dst):
    dst.collections=[n for n in src.collections if n.startswith('SOURCE_BenchTop')]
planks=[]
for coll in dst.collections:
    scene.collection.children.link(coll);coll.hide_viewport=False;coll.hide_render=False
    planks.extend(o for o in coll.objects if o.type=='MESH')
for k,ob in enumerate(sorted(planks,key=lambda o:o.name)):
    first=k<3;long=Vector((0,1,0)) if first else Vector((1,0,0));cross=Vector((1,0,0)) if first else Vector((0,1,0))
    uv=ob.data.uv_layers.active;local=ob.data.uv_layers.new(name='WorkshopLocalXY')
    ob.data.materials.clear();ob.data.materials.append(MATS['BenchWood']);ob.data.materials.append(MATS['EndGrain'])
    colors=ob.data.color_attributes.new(name='PlankVariation',type='FLOAT_COLOR',domain='CORNER')
    tint=[.95,1.0,.92,.97,.94,1.0][k]
    for face in ob.data.polygons:
        end=abs(face.normal.dot(long))>.8;top=abs(face.normal.z)>.65;face.material_index=1 if end else 0
        for li in face.loop_indices:
            p=ob.data.vertices[ob.data.loops[li].vertex_index].co
            if end:coord=(p.dot(cross)/.27+.17*k,(p.z-.877)/.080)
            else:coord=(p.dot(long)/1.72+.193*k,(p.dot(cross) if top else p.z)/.62+.231*k)
            uv.data[li].uv=coord;local.data[li].uv=(p.x,p.y);colors.data[li].color=(tint,tint,tint,1)
    PARTS['BenchTop'].append(ob);ob['component_group']='BenchTop'

# Localised scratches, rather than a uniformly grungy layer. Hairline tapered wedge strips.
for group,cx,cy,sx,sy in [('main',.72,2.70,.16,.39),('return',1.89,3.60,.39,.13)]:
    for i in range(30):
        x=cx+R.uniform(-sx,sx);y=cy+R.uniform(-sy,sy);angle=R.uniform(-1.0,1.0)+(0 if group=='main' else math.pi/2)
        length=R.uniform(.009,.078);width=R.uniform(.00014,.00042)
        f=flat((x,y,.93908),angle)
        profile('BenchWear','Fine ingrained service cut',[(0,0),(width,length*.35),(width*.55,length*.8),(0,length),(-width*.6,length*.42)],f,.00010,'IngrainedCut' if i%5 else 'FreshCut',0)
for k in range(6):
    first=k<3;i=k%3;length=2.26 if first else 1.64
    center=Vector((.17+(i+.5)*.76/3,2.61,.9391) if first else (1.77,3.39+(i+.5)*.68/3,.9391))
    long=Vector((0,1,0)) if first else Vector((1,0,0));cross=Vector((1,0,0)) if first else Vector((0,1,0))
    for sign in (-1,1):
        for off in (-.045,.057):
            lengthcut=R.uniform(.016,.038);f=Frame(center+long*sign*(length/2-.003)+cross*off,cross,-long*sign)
            profile('BenchWear','Short end-grain check',[(-.00022,0),(.00031,0),(0,lengthcut)],f,.00008,'IngrainedCut',0)

# Task lamp: paired links and hardware surround a single, genuinely thick shade.
g='TaskLamp';base=Vector((.27,2.13,.958));p1=Vector((.36,2.13,1.27));p2=Vector((.58,2.17,1.56));head=Vector((.76,2.27,1.510))
lathe(g,'Pressed steel weighted base',Frame(base,(1,0,0),(0,0,1)),[(-.015,.044),(-.013,.068),(-.006,.071),(.002,.069),(.014,.053),(.020,.021),(.023,.016)],'LampPaint',112)
ring(g,'Rolled base edge',flat(base+Vector((0,0,-.008))),.070,.0012,'LampPaint',112)
for a in (0,math.tau/3,math.tau*2/3):
    x=base.x+math.cos(a)*.042;y=base.y+math.sin(a)*.042
    cylinder(g,'Rubber base pad',(x,y,.939),(x,y,.945),.009,'CableRubber',40)
cylinder(g,'Swivel bearing',base,base+Vector((0,0,.045)),.0165,'Machined',64)
for a,b in [(base+Vector((0,0,.034)),p1),(p1,p2),(p2,head)]:
    for dy in (-.016,.016):sweep(g,'Oval pressed steel link',[a+Vector((0,dy,0)),b+Vector((0,dy,0))],.007,'LampPaint',40,False,.56)
for p in (p1,p2):
    cylinder(g,'Pivot sleeve',p-Vector((0,.034,0)),p+Vector((0,.034,0)),.015,'Machined',64)
    for sign in (-1,1):
        f=Frame(p+Vector((0,sign*.034,0)),(1,0,0),(0,sign,0))
        lathe(g,'Domed friction adjuster',f,[(0,.014),(.002,.016),(.006,.015),(.010,.010),(.011,.003)],'LampPaint',80,.028)
        cylinder(g,'Pivot shoulder screw',f.p(0,.010),f.p(0,.012),.0045,'Machined',32)
        # A real screw slot, cut into the domed head.
        screw=PARTS[g][-1];slotframe=Frame(f.p(0,.0117),(1,0,0),(0,0,1))
        bore(screw,slotframe,[(-.0033,-.0006),(.0033,-.0006),(.0033,.0006),(-.0033,.0006)],.003)
for dy in (-.026,.026):
    a=Vector((.37,2.13+dy,1.28));b=Vector((.49,2.15+dy,1.415));axis=(b-a).normalized();u=axis.cross(Vector((0,1,0))).normalized();v=axis.cross(u)
    points=[a+(b-a)*t+.0065*(u*math.cos(t*16*math.tau)+v*math.sin(t*16*math.tau)) for t in [i/384 for i in range(385)]]
    sweep(g,'Steel tension spring',points,.00105,'Machined',10,False)
    for pp in (a,b):ring(g,'Formed spring eye',Frame(pp,(1,0,0),(0,0,1)),.005,.00105,'Machined',36)
target=Vector((.68,2.72,.939));rot=Vector((0,0,-1)).rotation_difference((target-head).normalized())
n=rot@Vector((0,0,1));u=rot@Vector((1,0,0));v=rot@Vector((0,1,0));f=Frame(head,u,n)
outline=[(0,.027),(-.006,.034),(-.017,.039),(-.034,.048),(-.052,.062),(-.073,.081),(-.092,.101),(-.100,.106)]
outer=[Vector(p) for p in catmull(outline,5)];inner=[];thickness=.00125
for i,p in enumerate(outer):
    tangent=(outer[min(i+1,len(outer)-1)]-outer[max(i-1,0)]).normalized()
    normal=Vector((tangent.y,-tangent.x));inner.append(p-normal*thickness)
# Two surfaces share the closed rim. No coplanar liner, no diagonal-offset intersection.
profilepts=outer+list(reversed(inner))+[outer[0]]
shade=lathe(g,'Single closed steel shade enamel inside',f,profilepts,'LampPaint',128,cap=False)
shade.data.materials.append(MATS['Reflector']);count=len(outer)
for poly in shade.data.polygons:
    strip=poly.index//128
    if strip>=count:poly.material_index=1
    if strip in (count-1,2*count-1):poly.use_smooth=False
ring(g,'Rolled protective shade rim',Frame(head-n*.100,u,v),.1055,.0018,'LampPaint',128)
lathe(g,'Stamped rear cap',f,[(.0,.027),(.003,.027),(.015,.022),(.024,.013),(.026,.011)],'LampPaint',80)
# Actual circular ventilation bores pass through the upper shade wall.
for i in range(8):
    a=i*math.tau/8;radial=u*math.cos(a)+v*math.sin(a);pp=head-n*.013+radial*.037
    bore(shade,Frame(pp,n,radial.cross(n)),[(math.cos(j*math.tau/24)*.0018,math.sin(j*math.tau/24)*.003) for j in range(24)],.018)
lathe(g,'Recessed ceramic holder',f,[(-.006,.014),(-.030,.014),(-.033,.017),(-.042,.017)],'SocketCeramic',64)
lathe(g,'Frosted recessed bulb',f,[(-.039,.012),(-.049,.014),(-.060,.023),(-.074,.025),(-.086,.020),(-.092,.001)],'LampBulb',96)
for aa in (-1,1):bolt(g,head+u*aa*.020+n*.005,u*aa,.0025)
# Positive switch and rear strain relief, rather than an anonymous lump.
switchpos=base+Vector((.035,0,.011))
lathe(g,'Switch bezel',Frame(switchpos,(1,0,0),(0,0,1)),[(0,.008),(.002,.009),(.004,.008)],'Machined',48)
cylinder(g,'Bakelite push switch',switchpos+Vector((0,0,.003)),switchpos+Vector((0,0,.010)),.0055,'CableRubber',48)

def bezier_chain(spans,samples=22):
    result=[]
    for span in spans:
        a,b,c,d=map(Vector,span)
        result.extend((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d for t in [i/samples for i in range(samples)])
    return result+[Vector(spans[-1][-1])]
g='TaskCable'
plug=Frame((.228,2.590,1.310),(0,1,0),(1,0,0))
lathe(g,'Moulded socket plug',plug,[(0,.014),(.004,.018),(.011,.020),(.020,.019),(.027,.012),(.031,.006)],'CableRubber',64)
for zz in (.008,.013,.018):ring(g,'Plug gripping rib',Frame(plug.p(0,zz),(0,1,0),(0,0,1)),.0195,.0006,'CableRubber',64)
cylinder(g,'Plug flexible boot',(.254,2.590,1.310),(.300,2.590,1.310),.0046,'CableRubber',40)
for i in range(5):ring(g,'Moulded plug strain relief rib',Frame((.267+i*.005,2.590,1.310),(0,1,0),(0,0,1)),.0048-i*.00022,.0007,'CableRubber',32)
spans=[[(.300,2.59,1.310),(.34,2.59,1.27),(.225,2.62,.961),(.215,2.53,.9445)],
       [(.215,2.53,.9445),(.206,2.50,.9445),(.20,2.34,.9445),(.212,2.285,.9445)],
       [(.212,2.285,.9445),(.21,2.21,.9445),(.20,2.16,.97),(.202,2.13,.958)]]
sweep(g,'Five millimetre power flex on rear worktop',bezier_chain(spans),.0025,'CableRubber',24,False)
cylinder(g,'Lamp base entry grommet',(.199,2.13,.958),(.209,2.13,.958),.0058,'CableRubber',40)
for i in range(4):ring(g,'Base flex boot rib',Frame((.192+i*.003,2.13,.958),(0,1,0),(0,0,1)),.0042,.0007,'CableRubber',28)
arm=[[(.250,2.166,.971),(.25,2.18,1.03),(.333,2.173,1.205),(.365,2.174,1.253)],
     [(.365,2.174,1.253),(.397,2.18,1.277),(.414,2.178,1.292),(.393,2.178,1.321)],
     [(.393,2.178,1.321),(.439,2.18,1.382),(.515,2.204,1.492),(.57,2.212,1.540)],
     [(.57,2.212,1.540),(.602,2.219,1.595),(.621,2.23,1.603),(.634,2.23,1.566)],
     [(.634,2.23,1.566),(.673,2.248,1.550),tuple(head+n*.050),tuple(head+n*.020)]]
sweep(g,'Three point three millimetre lamp arm flex',bezier_chain(arm,18),.00165,'CableRubber',20,False)
for c in ((.32,2.162,1.143),(.477,2.202,1.436)):
    box(g,'Rubber-lined cable retaining clip',c,(.014,.011,.015),'LampPaint',.002)
# Source setup records the actual line diameters and desk elevation for future edits.
manifest=dict(objects=[],material_aliases=aliases,source_blend=str(OUT/'DungeonWorkshopBenchPolish.blend'),
    remove_actors=['DGN_Room_WS_RepairMotor'],hide_actors=['DGN_WSTools_TaskCable'],
    top_height_m=.939,power_cable_diameter_mm=5,arm_cable_diameter_mm=3.3,
    task_light=dict(position=[(10-(head-n*.104).x)*100,(head-n*.104).y*100,(head-n*.104).z*100],
                    target=[(10-target.x)*100,target.y*100,target.z*100],lumens=65,temperature=3400),
    tests_run=False,screenshots_taken=False)
bindings={'BenchTop':'DGN_WSTools_BenchTop','BenchWear':'DGN_Room_WS_LocalWear','TaskLamp':'DGN_Room_WS_TaskLight','TaskCable':'DGN_WSBench_TaskCable'}
WORLD=Matrix(((-1,0,0,10),(0,-1,0,0),(0,0,1,0),(0,0,0,1)))
exports=bpy.data.collections.new('ENGINE_EXPORTS');scene.collection.children.link(exports);deps=bpy.context.evaluated_depsgraph_get()
for group,objects in PARTS.items():
    if group.startswith('_') or not objects:continue
    coll=bpy.data.collections.new('EDITABLE_'+group);scene.collection.children.link(coll);copies=[]
    for ob in objects:
        for oldcoll in list(ob.users_collection):oldcoll.objects.unlink(ob)
        coll.objects.link(ob);ev=ob.evaluated_get(deps);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
        cp=bpy.data.objects.new(ob.name+'_export',me);exports.objects.link(cp);cp.matrix_world=ob.matrix_world.copy();copies.append(cp)
    active(copies[0])
    for ob in copies:ob.select_set(True)
    bpy.ops.object.join();ob=copies[0];ob.name='SM_WSBench_'+group;ob.data.transform(WORLD);ob.data.update()
    tri=ob.modifiers.new('Export triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
    file=OUT/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False)
    manifest['objects'].append(dict(name=ob.name,actor=bindings[group],fbx=str(file),collision=group=='BenchTop',cast_shadow=group!='BenchWear',triangles=len(ob.data.polygons),materials=[m.name for m in ob.data.materials]))
    coll.hide_viewport=True;coll.hide_render=True;print('BENCH_POLISH_EXPORTED',group,len(ob.data.polygons),flush=True)
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
bpy.ops.wm.save_as_mainfile(filepath=manifest['source_blend'])
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('BENCH_POLISH_AUTHORED_NO_RENDER',flush=True)
