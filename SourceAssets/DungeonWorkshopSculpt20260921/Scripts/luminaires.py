def build_task_lamp():
    g='TaskLamp';base=Vector((.27,2.13,.958));p1=Vector((.36,2.13,1.27));p2=Vector((.58,2.17,1.56));head=Vector((.76,2.27,1.510))
    lathe(g,'Weighted spun lamp base',Frame(base,(1,0,0),(0,0,1)),[(-.015,.044),(-.013,.068),(-.006,.071),(.002,.069),(.014,.053),(.020,.021),(.023,.016)],'CastGreen',96)
    for a in (0,math.tau/3,math.tau*2/3):
        xx=base.x+math.cos(a)*.042;yy=base.y+math.sin(a)*.042
        cylinder(g,'Lamp non-slip foot',(xx,yy,.939),(xx,yy,.945),.009,'RubberGrip',32)
    cylinder(g,'Rotating base socket',base,base+Vector((0,0,.045)),.017,'Machined',64)
    # Paired flattened links, with a centre gap and working pivot plates.
    for a,b in [(base+Vector((0,0,.034)),p1),(p1,p2),(p2,head)]:
        for dy in (-.016,.016):
            aa=a+Vector((0,dy,0));bb=b+Vector((0,dy,0))
            sweep(g,'Rounded parallel arm link',[aa,bb],.007,'CastGreen',32,False,.56)
    for p in (p1,p2):
        cylinder(g,'Turned pivot barrel',p-Vector((0,.034,0)),p+Vector((0,.034,0)),.018,'Machined',64)
        for sign in (-1,1):
            lathe(g,'Domed pivot thumb nut',Frame(p+Vector((0,sign*.036,0)),(1,0,0),(0,sign,0)),[(0,.014),(.002,.016),(.006,.015),(.010,.010),(.011,.003)],'CastGreen',64,.03)
    for dy in (-.026,.026):
        a=Vector((.37,2.13+dy,1.28));b=Vector((.49,2.15+dy,1.415));axis=(b-a).normalized();u=axis.cross(Vector((0,1,0))).normalized();v=axis.cross(u)
        pts=[a+(b-a)*t+.0065*(u*math.cos(t*16*math.tau)+v*math.sin(t*16*math.tau)) for t in [i/480 for i in range(481)]]
        sweep(g,'Close-wound tension spring',pts,.00115,'Machined',10,False)
        for pp in (a,b):ring(g,'Spring hook eye',Frame(pp,(1,0,0),(0,0,1)),.005,.0012,'Machined',32)
    target=Vector((.57,2.72,1.13));rot=Vector((0,0,-1)).rotation_difference((target-head).normalized())
    # Curved paraboloid-like spun shell with real open cavity, thickness and rolled mouth.
    n=rot@Vector((0,0,1));u=rot@Vector((1,0,0));v=rot@Vector((0,1,0));f=Frame(head,u,n)
    outer=[(0,.031),(-.004,.038),(-.014,.041),(-.031,.047),(-.051,.060),(-.071,.079),(-.093,.100),(-.100,.106)]
    op=[tuple(p) for p in catmull(outer,6)]
    shell=op+[(z+.0023,r-.0023) for z,r in reversed(op)]+[op[0]]
    lathe(g,'Thin spun bell shade with continuous inner surface',f,shell,'CastGreen',112,cap=False)
    # Independent light enamel lining extends only inside the bell.
    lathe(g,'Enamel reflector inner bowl',f,[(z+.0025,r-.0025) for z,r in op],'Reflector',112,cap=False)
    ring(g,'Rolled shade hem',Frame(head-n*.100,u,v),.1055,.0026,'Machined',112)
    lathe(g,'Lamp socket cap',f,[(.003,.020),(.020,.020),(.026,.015),(.028,.008)],'CastGreen',64)
    lathe(g,'Frosted recessed lamp bulb',f,[(-.025,.013),(-.045,.019),(-.064,.027),(-.079,.027),(-.088,.020),(-.091,.001)],'TaskLens',80)
    for a in [i*math.tau/8 for i in range(8)]:
        pp=head+u*(math.cos(a)*.036)+v*(math.sin(a)*.036)-n*.007
        sweep(g,'Shade neck ventilation slot',[pp-n*.002,pp-n*.006],.0016,'RubberGrip',12,False)
    sweep(g,'Task lamp articulated power lead',[(.20,2.64,1.31),(.225,2.52,1.015),(.235,2.25,.84),tuple(base),tuple(p1+Vector((-.008,.025,0))),tuple(p2+Vector((-.008,.025,0))),tuple(head+n*.016)],.0038,'RubberGrip',24)
    # Preserve the prior light position/direction; only shell construction is changed.

def build_ceiling_lights():
    g='CeilingFixtures'
    for idx,(cx,cy,L,z) in enumerate([(4.0,1.8,1.26,3.025),(1.6,3.1,.98,3.12)]):
        # Rounded pressed trough: top panel, sloping shoulders, vertical returns and bottom flange.
        section=rounded([(-.086,.037),(.086,.037),(.111,.020),(.116,-.019),(.108,-.031),(-.108,-.031),(-.116,-.019),(-.111,.020)],.007,6)
        body=profile(g,'Pressed luminaire tray',section,Frame((cx,cy,z),(0,1,0),(0,0,1)),L-.028,'Enamel',.004)
        # Open out the bottom of the tray, leaving thin sheet folds instead of a solid box.
        cut=rounded([(-.101,-.070),(.101,-.070),(.101,.016),(-.101,.016)],.009,6)
        bore(body,Frame((cx,cy,z),(0,1,0),(0,0,1)),cut,L-.085)
        # Curved prismatic diffuser, thin arched shell with integral end caps.
        diffuser=rounded([(-.097,-.029),(.097,-.029),(.094,-.057),(.078,-.067),(-.078,-.067),(-.094,-.057)],.006,6)
        profile(g,'Curved sealed prismatic diffuser',diffuser,Frame((cx,cy,z),(0,1,0),(0,0,1)),L-.086,'Lens',.003)
        for side in (-1,1):
            sweep(g,'Continuous elastomer sealing gasket',[(cx-L/2+.032,cy+side*.102,z-.031),(cx+L/2-.032,cy+side*.102,z-.031)],.0032,'RubberGrip',20,False)
            box(g,'Moulded end cap',(cx+side*(L/2-.015),cy,z-.004),(.035,.239,.075),'Enamel',.011)
            for yy in (-.065,.065):bolt(g,(cx+side*L/2,cy+yy,z),(side,0,0),.0032)
        for i in range(int(L/.012)):
            xx=cx-L/2+.055+i*.012
            if xx>cx+L/2-.055:break
            # Lens ribs follow the rounded cross section rather than floating on a flat slab.
            pts=[(xx,cy-.091,z-.039),(xx,cy-.087,z-.057),(xx,cy-.074,z-.066),(xx,cy+.074,z-.066),(xx,cy+.087,z-.057),(xx,cy+.091,z-.039)]
            sweep(g,'Extruded prism rib',pts,.00075,'Lens',8,True)
        for dx in (-L*.31,L*.31):
            for sign in (-1,1):
                pts=[(cx+dx,cy+sign*.106,z+.008),(cx+dx,cy+sign*.123,z+.001),(cx+dx,cy+sign*.124,z-.036),(cx+dx,cy+sign*.105,z-.048)]
                sweep(g,'Stainless over-centre diffuser clip',pts,.003,'Machined',16,True,.60)
                cylinder(g,'Clip pivot',(cx+dx-.012,cy+sign*.120,z+.002),(cx+dx+.012,cy+sign*.120,z+.002),.0035,'Machined',24)
            box(g,'Folded mounting saddle',(cx+dx,cy,z+.045),(.067,.256,.009),'Machined',.0025)
            cylinder(g,'Suspension rod',(cx+dx,cy,z+.048),(cx+dx,cy,3.280),.006,'Machined',40)
            box(g,'Ceiling anchor plate',(cx+dx,cy,3.289),(.100,.080,.016),'Enamel',.007)
            for yy in (-.024,.024):bolt(g,(cx+dx,cy+yy,3.279),(0,0,-1),.0045)
        box(g,'Rounded electrical junction box',(cx+L*.42,cy+.19,3.256),(.13,.12,.06),'Enamel',.010)
        box(g,'Junction lid',(cx+L*.42,cy+.19,3.224),(.124,.114,.008),'Enamel',.008)
        sweep(g,'Flexible luminaire supply',[(cx+L*.42,cy+.19,3.22),(cx+L*.47,cy+.16,z+.08),(cx+L*.46,cy+.03,z+.035)],.0065,'RubberGrip',24)
