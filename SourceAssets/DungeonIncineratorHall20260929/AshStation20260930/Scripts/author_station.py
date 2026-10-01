"""Blender hard-surface ash station, inlet duct, receiving drawer and Chinese signs."""
import json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
sys.path.insert(0,str(HALL/'SceneFix20260930/Scripts'))
import author_fixes as fx
from author_fixes import equipment as eq,g
CFG=json.loads((ROOT/'Config/layout.json').read_text(encoding='utf-8'))
BASE=CFG['ue_base'];ORIGIN=Vector(CFG['receiver_origin_m'])
box=g.box;rod=g.rod;bolt=g.bolt;lathe=g.lathe;plate=eq.plate

def receiver():
    eq.part('01_Fixed_frame_anchor_plates_and_slide_guides')
    for x in (-.79,.79):
        for y in (-.405,.405):
            box((x,y,.91),(.075,.075,1.82),'teal',.003)
            box((x,y,.012),(.18,.18,.024),'steel',.002)
            for dx in (-.061,.061):
                for dy in (-.061,.061):bolt((x+dx,y+dy,.025),(0,0,1),1.05)
        box((x,0,1.83),(.085,.94,.085),'teal',.004)
        for z in (.235,1.1):box((x,0,z),(.06,.87,.06),'teal',.002)
        # Drawer's floor guides have real upturned edges and end stops.
        box((x*.81,0,.055),(.13,1.16,.014),'steel',.002)
        box((x*.94,0,.091),(.012,1.16,.085),'steel',.002)
        box((x*.81,-.578,.099),(.14,.025,.10),'ochre',.002)
    box((0,-.405,1.83),(1.62,.075,.075),'teal',.003)
    eq.part('02_Sealed_receiver_hopper_thickness_folds_and_inspection_cover')
    lower=[(-.225,-.21,1.27),(.225,-.21,1.27),(.225,.21,1.27),(-.225,.21,1.27)]
    upper=[(-.65,-.365,1.78),(.65,-.365,1.78),(.65,.365,1.78),(-.65,.365,1.78)]
    for i in range(4):
        j=(i+1)%4;plate([lower[i],lower[j],upper[j],upper[i]],.006,'graphite',.001)
        eq.weld(lower[i],upper[i],.003)
    box((0,0,1.79),(1.36,.79,.020),'graphite',.004)
    for x in (-.645,.645):
        box((x,0,1.753),(.020,.79,.075),'steel',.002)
        for y in (-.30,0,.30):bolt((x,y,1.803),(0,0,1),.8)
    for y in (-.365,.365):
        box((0,y,1.753),(1.30,.020,.075),'steel',.002)
        for x in (-.47,-.16,.16,.47):bolt((x,y,1.803),(0,0,1),.8)
    # Bolted front access cover is mounted on a short welded inspection neck.
    box((0,.355,1.57),(.68,.11,.22),'graphite',.004)
    box((0,.416,1.57),(.70,.016,.24),'steel',.003)
    for x in (-.316,.316):
        for z in (1.484,1.656):bolt((x,.426,z),(0,1,0),.65)
    eq.part('03_Manual_isolation_slide_gate_and_bellows')
    box((0,0,1.232),(.67,.60,.066),'steel',.004)
    for x in (-.298,.298):
        for y in (-.255,.255):bolt((x,y,1.269),(0,0,1),1.05)
    box((.33,0,1.22),(.30,.26,.085),'graphite',.006)
    rod((.33,0,1.22),(.83,0,1.22),.015,'steel',24)
    for i in range(32):eq.torus((.41+i*.009,0,1.22),(1,0,0),.017,.0018,'steel',20,6)
    box((.735,0,1.22),(.062,.12,.12),'teal',.004)
    eq.torus((.875,0,1.22),(1,0,0),.135,.012,'ochre',64,12)
    lathe((.85,0,1.22),(1,0,0),[(0,.033),(.042,.033)],'steel',32)
    for i in range(4):
        a=i*math.tau/4;rod((.875,math.cos(a)*.03,1.22+math.sin(a)*.03),(.875,math.cos(a)*.124,1.22+math.sin(a)*.124),.008,'steel',16)
    bolt((.897,0,1.22),(1,0,0),1.6)
    # Closed gate, flexible dust seal and removable bin collar.
    box((0,0,1.12),(.46,.43,.15),'rubber',.006)
    for z in (1.061,1.086,1.111,1.136,1.161,1.186):
        for x in (-.231,.231):box((x,0,z),(.015,.449,.010),'graphite',.002)
        for y in (-.221,.221):box((0,y,z),(.47,.015,.010),'graphite',.002)
    box((0,0,1.033),(.56,.53,.020),'steel',.003)
    eq.part('04_Furnace_side_inlet_chute_flanges_and_support')
    a=Vector(CFG['inlet_at_furnace_m'])-ORIGIN
    b=Vector((0,-.03,1.89))
    eq.beam(a,b,.40,.32,'graphite',.006)
    direction=(b-a).normalized();n,u,v=g.basis(direction)
    for at in (a,a+(b-a)*.50,b):
        # Four-sided bolted flange with a real open bore.
        for sign in (-1,1):
            eq.beam(at+u*sign*.231-v*.207,at+u*sign*.231+v*.207,.022,.055,'steel',.010)
            eq.beam(at-v*sign*.184-u*.249,at-v*sign*.184+u*.249,.022,.055,'steel',.010)
        for su in (-1,1):
            for sv in (-1,1):bolt(at+u*su*.22+v*sv*.18+n*.018,n,1.1)
    # Furnace mounting shoe and short inlet seal cover the connected wall face.
    outward=Vector(CFG.get('inlet_outward_axis',[-1,0,0]))
    box(a+outward*.035,(.050,.62,.55),'steel',.004)
    for yy in (-.245,.245):
        for zz in (-.20,.20):bolt(a+outward*.061+Vector((0,yy,zz)),outward,1.25)
    box((0,-.03,1.835),(.48,.46,.095),'graphite',.005)
    eq.beam((.62,-.38,1.83),a+(b-a)*.56,.042,.042,'teal',.005)

def drawer():
    eq.part('01_Receiving_drawer_wheels_and_frame')
    for x in (-.56,.56):
        for y in (-.39,.39):eq.caster(x,y,y>0,y>0)
        box((x,0,.386),(.080,1.04,.080),'ochre',.003)
    for y in (-.47,.47):box((0,y,.386),(1.22,.06,.08),'ochre',.003)
    eq.part('02_Thick_ash_bin_and_folded_rim')
    plate([(-.625,-.465,.435),(.625,-.465,.435),(.625,.465,.435),(-.625,.465,.435)],.005,'steel')
    for x in (-.625,.625):
        box((x,0,.715),(.005,.94,.56),'steel',.001)
        box((x,0,1.001),(.034,.98,.014),'steel',.003)
        for z in (.49,.91):box((x,0,z),(.024,.94,.04),'ochre',.002)
    for y in (-.467,.467):
        box((0,y,.715),(1.25,.005,.56),'steel',.001)
        box((0,y,1.001),(1.30,.034,.014),'steel',.003)
        for x in (-.43,.43):box((x,y,.715),(.045,.025,.54),'ochre',.002)
    # Split gasketed top, joined around a real rectangular receiver aperture.
    for x in (-.46,.46):box((x,0,1.016),(.355,.944,.008),'graphite',.002)
    for y in (-.37,.37):box((0,y,1.016),(.57,.214,.008),'graphite',.002)
    for x in (-.289,.289):box((x,0,1.022),(.019,.54,.009),'rubber',.002)
    for y in (-.265,.265):box((0,y,1.022),(.59,.02,.009),'rubber',.002)
    for x in (-.47,.47):
        eq.curved([(x,.48,.64),(x,.65,.64),(x,.729,.71),(x,.729,.83)],.014,'steel',16,5)
        box((x,.485,.65),(.07,.024,.13),'ochre',.002)
        for z in (.605,.695):bolt((x,.501,z),(0,1,0),.65)
    rod((-.47,.729,.83),(.47,.729,.83),.017,'steel',24)
    lathe((-.30,.729,.83),(1,0,0),[(0,.023),(.60,.023)],'rubber',32)
    for x in (-.66,.66):
        box((x,.44,.53),(.038,.095,.13),'ochre',.003)
        eq.torus((x,.500,.53),(1,0,0),.022,.003,'steel',24,8)
    eq.part('03_Label_mount_and_drain_plug')
    box((0,.478,.735),(.46,.02,.18),'ochre',.003)
    lathe((.37,.475,.475),(0,1,0),[(0,.025),(.025,.025),(.032,.029)],'steel',6,False)

def sign_material():
    mat=bpy.data.materials.new('AshStation_Signage');mat.use_nodes=True
    nodes=mat.node_tree.nodes;bsdf=nodes.get('Principled BSDF');links=mat.node_tree.links
    image=bpy.data.images.load(str(ROOT/'Authored/Textures/T_AshStation_Signage_BaseColor.png'));image.pack()
    tex=nodes.new('ShaderNodeTexImage');tex.image=image;links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value=.62;return mat

def signs():
    eq.part('01_Stair_entry_chinese_instruction_board')
    c=Vector(CFG['main_sign_position_m'])
    for x in (-.36,.36):
        box(c+Vector((x,-.029,.75)),(.046,.046,1.50),'graphite',.002)
        box(c+Vector((x,-.03,.008)),(.16,.16,.016),'steel',.002)
        for dx in (-.051,.051):bolt(c+Vector((x+dx,-.03,.017)),(0,0,1),.6)
    fx.solid_nameplate(c+Vector((0,0,1.40)),1.10,.445,'main',(0,1,0),.008)
    for x in (-.505,.505):
        for z in (1.228,1.572):bolt(c+Vector((x,.0003,z)),(0,1,0),.45)
    eq.part('02_Receiver_and_drawer_labels')
    fx.solid_nameplate(ORIGIN+Vector((0,.427,1.57)),.594,.162,'machine',(0,1,0),.003)
    fx.solid_nameplate(ORIGIN+Vector((0,.49,.735)),.423,.15,'bin',(0,1,0),.002)
    fx.solid_nameplate(ORIGIN+Vector((.42,.137,1.225)),.19,.085,'gate',(0,1,0),.002)
    eq.part('03_Pit_edge_caution_plate')
    # Centre in the clear bay between x=-9.45/-8.60 posts. The entire backing
    # sits in front of the rail, with two brackets attached to the middle rail.
    c=Vector(CFG['caution_sign_position_m'])
    rail_front=fx.CFG['ash_pit']['rect'][3]+.08+.03
    back=c.y-.055
    for dx in (-.21,.21):
        box((c.x+dx,rail_front+.014,.645),(.028,.028,.25),'steel',.001)
        y0=rail_front+.028;y1=back+.002
        box((c.x+dx,(y0+y1)*.5,c.z),(.028,y1-y0,.028),'steel',.001)
        bolt((c.x+dx,rail_front+.029,.535),(0,1,0),.45)
    box(c+Vector((0,-.035,0)),(.62,.04,.30),'graphite',.004)
    fx.solid_nameplate(c,.59,.27,'caution',(0,1,0),.004)
    for x in (-.27,.27):bolt(c+Vector((x,.001,0)),(0,1,0),.5)

def run():
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
    fx.ROOT=ROOT;fx.BASE=BASE;mat=eq.material();records=[]
    rail_specs=fx.rails_layout()
    records.append(fx.export('Railings',fx.author_rails,[fx.rail_prism(s['a'],s['b'],-.025,s['height']+.04,.08) for s in rail_specs],mat,'_AshV3'))
    fixed=[fx.cube((x,y,.92),(.08,.08,1.84)) for x in (-.79,.79) for y in (-.405,.405)]
    fixed += [fx.cube((0,0,1.52),(1.36,.80,.59)),fx.cube((.47,0,1.22),(.96,.31,.28))]
    a=Vector(CFG['inlet_at_furnace_m'])-ORIGIN;b=Vector((0,-.03,1.89));n,u,v=g.basis(b-a)
    vs=[tuple(p+u*dx*.22+v*dy*.18) for p in (a,b) for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1))]
    fixed.append((vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]))
    records.append(fx.export('AshReceiver',receiver,fixed,mat,'_V3'));records[-1]['position_m']=list(ORIGIN)
    records.append(fx.export('AshDrawer',drawer,[fx.cube((0,0,.52),(1.40,1.10,1.04)),fx.cube((0,.715,.75),(1.02,.09,.26))],mat,'_V3'));records[-1]['position_m']=list(ORIGIN)
    # Sign boards have their own readable atlas; all front faces remain single-surface.
    atlas=json.loads((ROOT/'Authored/sign_atlas.json').read_text(encoding='utf-8'))
    def sign_tex(surface,u,v):
        r=atlas['rects'].get(surface,[2,834,18,850]);x0,y0,x1,y1=r
        return ((x0+u*(x1-x0))/2048,1-(y0+v*(y1-y0))/2048)
    original_tex=g.tex;original_material=g.MATERIAL;g.tex=sign_tex;g.MATERIAL=BASE+'/Materials/M_AshStation_Signage'
    records.append(fx.export('AshSigns',signs,[],sign_material(),'_V3'));records[-1]['collision_policy']='none'
    g.tex=original_tex;g.MATERIAL=original_material
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/AshReceivingStation_PrecisionV3.blend'))
    (ROOT/'Authored/manifest.json').write_text(json.dumps({'revision':CFG['revision'],'objects':records,'tests_run':False,'rendered':False,'rail_runs':rail_specs},ensure_ascii=False,indent=2),encoding='utf-8')
    print('ASH_STATION_AUTHORED',len(records),flush=True)

if __name__=='__main__':run()
