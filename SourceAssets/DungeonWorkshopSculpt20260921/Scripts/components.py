"""Recognizable workshop objects: forged, cast, turned and pressed construction."""
def wrench(g,f,L=.24):
    s=L/.24
    points=[(-.010,-.017),(-.023,-.013),(-.030,.001),(-.029,.020),(-.018,.037),(-.010,.058),(-.007,.105),
            (-.008,.178),(-.014,.188),(-.020,.199),(-.020,.215),(-.014,.228),(0,.234),(.014,.228),(.020,.215),(.020,.199),(.014,.188),
            (.008,.178),(.007,.105),(.010,.058),(.022,.038),(.032,.022),(.034,.006),(.025,-.010),(.012,-.016),(.012,.014),(-.008,.020),(-.010,-.017)]
    points=points[:-1]
    pts=rounded([(x*s,y*s) for x,y in points],.004*s,6)
    ob=profile(g,'Continuous drop-forged combination wrench',pts,f,lambda y:(.005+.004*(math.exp(-((y-.012*s)/(.033*s))**2)+math.exp(-((y-.210*s)/(.025*s))**2)))*s,'Forged',.00125*s)
    center=.210*s
    hole=[((.0104+.0009*math.cos(a*6))*s*math.cos(a),center+(.0104+.0009*math.cos(a*6))*s*math.sin(a)) for a in [i*math.tau/72 for i in range(72)]]
    bore(ob,f,hole,.024*s)
    # Shallow forged channel, real recess on each side of the shank.
    for sign in (-1,1):
        cavity=rounded([(-.0033*s,.065*s),(.0033*s,.065*s),(.0028*s,.175*s),(-.0028*s,.175*s)],.003*s,6)
        bore(ob,f.offset(z=sign*.0031*s),cavity,.0022*s)
    return ob

def driver(g,f,L=.235,cross=True):
    lathe(g,'Moulded six-lobe screwdriver grip',f,[(0,.003),(.002,.009),(.007,.012),(.015,.0138),(.034,.0145),(.060,.0125),(.071,.0102),(.076,.008),(.077,.007)],'RedGrip',72,.10)
    lathe(g,'Grip collar and finger stop',f,[(.068,.010),(.070,.0145),(.074,.0145),(.077,.009),(.079,.008)],'RubberGrip',64)
    lathe(g,'Hardened screwdriver shaft',f,[(.078,.0032),(L-.021,.0032),(L-.015,.0028)],'Machined',48)
    # Ground blades taper into the tip, with the cross slot resolved in geometry.
    if cross:
        for ff in (f,Frame(f.c,f.n,f.v)):
            profile(g,'Ground Phillips flute',[(-.0032,L-.019),(.0032,L-.019),(.0011,L),(-.0011,L)],ff,.0015,'Machined',.0002)
    else:profile(g,'Ground slotted blade',[(-.0032,L-.021),(.0032,L-.021),(.0052,L-.006),(.0052,L),(-.0052,L),(-.0052,L-.006)],f,.0012,'Machined',.0002)
    for a in [i*math.tau/6 for i in range(6)]:
        sweep(g,'Recessed grip fluting',[f.p(.0117*math.cos(a),.020,.0117*math.sin(a)),f.p(.0123*math.cos(a),.035,.0123*math.sin(a)),f.p(.0108*math.cos(a),.057,.0108*math.sin(a))],.001,'RubberGrip',10)

def pliers(g,f):
    for sign in (-1,1):
        poly=[(sign*.034,.001),(sign*.043,.008),(sign*.039,.052),(sign*.027,.091),(sign*.006,.133),(-sign*.005,.153),(-sign*.003,.199),(-sign*.011,.206),(-sign*.020,.162),(-sign*.020,.145),(-sign*.005,.117),(sign*.018,.080),(sign*.029,.042)]
        profile(g,'Forged pliers half with integral jaw',rounded(poly,.005,6),f.offset(z=sign*.003),.0065,'Forged',.0013)
        pts=[f.p(sign*.037,.008,sign*.003),f.p(sign*.035,.033,sign*.003),f.p(sign*.029,.058,sign*.003),f.p(sign*.020,.082,sign*.003)]
        sweep(g,'Tapered dipped grip',pts,lambda t:.0075*(.75+.25*math.sin(math.pi*t)**.4),'RubberGrip',32,True,.85)
        for i in range(9):
            y=.166+i*.0034;x=sign*.004
            cylinder(g,'Cutting jaw serration',f.p(x,y,.003),f.p(x+sign*.007,y+.0005,.003),.00055,'Machined',8)
    cylinder(g,'Flush joint rivet',f.p(0,.136,-.010),f.p(0,.136,.010),.0085,'Machined',64)
    cylinder(g,'Rivet inset',f.p(0,.136,.010),f.p(0,.136,.0108),.0043,'Forged',48)

def hammer(g,f):
    # Elliptical ash handle, flared heel, curved centreline, reduced neck.
    vs=[];fs=[];stations=catmull([(0,.013,.009),(.018,.015,.010),(.075,.012,.0085),(.15,.010,.0075),(.205,.011,.0085),(.252,.013,.009)],7);N=40
    for y,rx,rz in stations:
        shift=.007*math.sin(y/.25*math.pi)
        for i in range(N):
            a=i*math.tau/N;vs.append(f.p(shift+rx*math.cos(a),y,rz*math.sin(a)))
    for j in range(len(stations)-1):
        for i in range(N):a=j*N+i;b=j*N+(i+1)%N;fs.append((a,b,b+N,a+N))
    fs.extend([tuple(reversed(range(N))),tuple((len(stations)-1)*N+i for i in range(N))])
    h=part(g,'Shaped elliptical ash handle',vs,fs,'Timber',True)
    for face in h.data.polygons:
        for li in face.loop_indices:
            vi=h.data.loops[li].vertex_index;h.data.uv_layers.active.data[li].uv=(vi%N/N,stations[vi//N][0]/.27)
    head=profile(g,'Forged engineer hammer centre',rounded([(-.034,.224),(.034,.224),(.038,.266),(-.034,.270)],.009,8),f,.038,'Forged',.004)
    cross=Frame(f.p(0,.248,0),f.v,f.u)
    lathe(g,'Bell hammer face',cross,[(-.077,.017),(-.075,.023),(-.069,.024),(-.061,.022),(-.051,.016),(-.032,.017)],'Machined',64)
    lathe(g,'Rounded peen',cross,[(.030,.017),(.048,.015),(.061,.012),(.070,.010),(.076,.006),(.078,.001)],'Forged',64)
    profile(g,'Steel handle wedge',[(-.006,.267),(.007,.267),(.006,.273),(-.005,.273)],f,.021,'Machined',.0006)

def ratchet(g,f):
    points=[(-.009,0),(-.014,.020),(-.014,.081),(-.010,.128),(-.008,.165),(-.020,.190),(-.025,.208),(-.021,.229),(-.010,.240),(.010,.240),(.021,.229),(.025,.208),(.020,.190),(.008,.165),(.010,.128),(.014,.081),(.014,.020),(.009,0)]
    ob=profile(g,'Forged oval ratchet body',rounded(points,.008,8),f,lambda y:.008+.006*math.exp(-((y-.21)/.027)**2),'Forged',.0014)
    lathe(g,'Ergonomic ratchet grip',f,[(.004,.006),(.009,.012),(.025,.015),(.055,.0158),(.096,.014),(.120,.0095),(.123,.008)],'RubberGrip',64,.025)
    cylinder(g,'Quick release button',f.p(0,.214,.007),f.p(0,.214,.0115),.011,'Machined',64)
    ring(g,'Head cover seam',f.offset(y=.214,z=.0076),.018,.00075,'Machined',64)
    profile(g,'Reversing selector',rounded([(-.018,.190),(-.004,.184),(.003,.188),(-.005,.195),(-.017,.197)],.002,4),f.offset(z=.009),.004,'Machined',.0005)

def socket(g,f,r=.016,h=.04):
    ob=lathe(g,'Broached socket',Frame(f.c,f.u,f.n),[(0,r*.91),(.002,r),(.012,r),(.014,r*.96),(h-.003,r*.96),(h,r*.89)],'Machined',64)
    a=r*.61;poly=[(a*math.cos(i*math.tau/6+math.pi/6),a*math.sin(i*math.tau/6+math.pi/6)) for i in range(6)]
    bore(ob,f.offset(z=h*.73),poly,h*.77)
    for z in (.006,.009):ring(g,'Turned socket grip line',f.offset(z=z),r,.00045,'Forged',64)

def build_vise():
    g='BenchDetail';cx,cy=2.25,3.70
    # One cast shell joins the bell base, rounded arch and upright. Remesh only this casting.
    blanks=[]
    blanks.append(lathe(g,'Cast vise bell foundation',Frame((cx,cy,.941),(1,0,0),(0,0,1)),[(0,.105),(.006,.128),(.014,.13),(.028,.123),(.039,.100),(.049,.088)],'CastGreen',80))
    side=Frame((cx,cy,.985),(1,0,0),(0,0,1))
    poly=[(-.134,0),(.082,0),(.095,.020),(.078,.063),(-.009,.079),(-.032,.144),(-.056,.160),(-.105,.157),(-.117,.118),(-.113,.060),(-.140,.038)]
    blanks.append(profile(g,'Continuous arched fixed casting',rounded(poly,.018,9),side,lambda z:.133-.025*max(0,min(1,z/.16)),'CastGreen',0))
    blanks.append(box(g,'Cast rear anvil shoulder',(cx-.136,cy,1.087),(.095,.121,.058),'CastGreen',.016))
    for ob in blanks:
        active(ob)
        for mod in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    active(blanks[0])
    for ob in blanks:ob.select_set(True)
    bpy.ops.object.join();cast=blanks[0]
    PARTS[g]=[o for o in PARTS[g] if o not in blanks[1:]]
    rem=cast.modifiers.new('Foundry blend between connected lobes','REMESH');rem.mode='VOXEL';rem.voxel_size=.0016;rem.use_smooth_shade=True
    sm=cast.modifiers.new('Cast fillet relaxation','SMOOTH');sm.factor=.65;sm.iterations=6
    dec=cast.modifiers.new('Curvature retaining cast surface','DECIMATE');dec.ratio=.60
    cast.name='Vise fixed cast body with blended foot and arch'
    # Open slide, clear jaw gap and separate precision-machined bearing surfaces.
    box(g,'Rectangular machined slide',(cx+.068,cy,1.033),(.268,.071,.045),'Machined',.003)
    mov=profile(g,'Rounded moving jaw casting',rounded([(-.030,0),(.030,0),(.047,.031),(.037,.098),(-.026,.112),(-.036,.082)],.016,8),Frame((cx+.108,cy,1.028),(1,0,0),(0,0,1)),.130,'CastGreen',.007)
    box(g,'Polished rear anvil face',(cx-.147,cy,1.119),(.077,.124,.010),'Machined',.002)
    for xx in (cx-.037,cx+.070):
        box(g,'Replaceable hardened jaw plate',(xx,cy,1.151),(.014,.158,.037),'Machined',.0011)
        for j in range(23):
            yy=cy-.074+j*.0065;side=1 if xx<cx else -1
            cylinder(g,'Cross milled jaw teeth',(xx+side*.0072,yy,1.135),(xx+side*.0072,yy+.006,1.166),.00055,'Forged',8)
        for yy in (cy-.057,cy+.057):bolt(g,(xx,yy,1.172),(0,0,1),.003)
    cylinder(g,'Vise lead screw',(cx-.04,cy,1.020),(cx+.275,cy,1.020),.012,'Machined',56)
    helix=[(cx+.17+t*.097,cy+.0123*math.cos(t*18*math.tau),1.020+.0123*math.sin(t*18*math.tau)) for t in [i/540 for i in range(541)]]
    sweep(g,'Continuous trapezoidal lead thread',helix,.0012,'Forged',8,False)
    lathe(g,'Turned sliding-handle boss',Frame((cx+.255,cy,1.02),(0,1,0),(1,0,0)),[(0,.016),(.004,.023),(.019,.025),(.034,.023),(.038,.016)],'Machined',64)
    cylinder(g,'Sliding tommy bar',(cx+.275,cy-.108,.983),(cx+.275,cy+.111,1.057),.0058,'Machined',48)
    for p in ((cx+.275,cy-.108,.983),(cx+.275,cy+.111,1.057)):
        lathe(g,'Rounded handle stop',Frame(p,(1,0,0),(0,.948,.318)),[(-.008,.007),(-.005,.009),(.005,.009),(.008,.007)],'Machined',40)
    for dx,dy in [(-.084,-.080),(-.084,.080),(.082,-.080),(.082,.080)]:bolt(g,(cx+dx,cy+dy,.959),(0,0,1),.007)
    label(g,(cx-.065,cy-.065,1.080),(1,0,0),(0,0,1),.066,.023,7)
    # Cast ribs are generous blended strips, not plate decorations.
    for yy in (cy-.065,cy+.065):
        sweep(g,'Cast strengthening fillet',[(cx-.105,yy,1.012),(cx-.085,yy,1.050),(cx-.070,yy,1.099)],lambda t:.008-.002*t,'CastGreen',32)
