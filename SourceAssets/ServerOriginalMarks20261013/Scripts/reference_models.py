"""Reference-derived three-fan GPU, armored DDR4 DIMM and M.2 2280 SSD."""
import math, bpy, bmesh
from mathutils import Vector
import mesh_helpers as H
from hardware_parts import box,cut,cyl,ring,panel,pcb,pcb_uv,round_cut,chip,smd,cap_row,edge_contacts,heat_sink,port_x

def poly_plate(name,outline,z0,z1,region='graphite',bevel=.035):
    count=len(outline);verts=[(x,y,z) for z in (z0,z1) for x,y in outline]
    faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
    for i in range(count):j=(i+1)%count;faces.append((i,j,j+count,i+count))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);H.register(obj,name,region);H.bevel(obj,bevel,3)
    return obj

def rigid_line(name,points,radius,region):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.bevel_depth=radius;curve.bevel_resolution=2
    spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
    for p,co in zip(spline.points,points):p.co=(*co,1)
    obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj);H.select(obj);bpy.ops.object.convert(target='MESH');H.register(obj,name,region)
    for face in obj.data.polygons:face.use_smooth=True
    return obj

def screw(name,p,r=.12):
    obj=cyl(name,p,r,.04,'steel',sides=32,radius=.005)
    for size in ((r*1.4,r*.23,.022),(r*.23,r*1.4,.022)):cut(obj,(p[0],p[1],p[2]+.022),size)
    return obj

def display_connector(name,y,kind):
    # Formed connector shells: HDMI has two chamfered shoulders, DP only one.
    x,z=-15.55,1.18;depth=1.56;w,h=1.97,.86
    shape=([(-.5,-.31),(-.36,-.5),(.36,-.5),(.5,-.31),(.5,.5),(-.5,.5)]
           if kind=='HDMI' else [(-.5,-.5),(.5,-.5),(.5,.5),(-.32,.5),(-.5,.21)])
    count=len(shape);verts=[]
    for xx,inner in ((x-depth*.5,False),(x-depth*.5,True),(x+depth*.5,False),(x+depth*.5,True)):
        for yy,zz in shape:verts.append((xx,y+yy*(w-.18 if inner else w),z+zz*(h-.15 if inner else h)))
    faces=[]
    for j in range(count):
        k=(j+1)%count
        faces.extend(((j,k,k+count,j+count),(j+count*2,j+count*3,k+count*3,k+count*2),
                      (j,j+count*2,k+count*2,k),(j+count,k+count,k+count*3,j+count*3)))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);H.register(obj,name,'steel');H.bevel(obj,.018,2)
    box(name+' rear insulation',(x+.63,y,z),(.23,1.74,.62),'plastic',.018,2)
    box(name+' contact tongue',(x+.08,y,z-.035),(.96,1.44,.12),'plastic',.022,2)
    for side in (-1,1):
        for j in range(9 if kind=='HDMI' and side<0 else 10):
            yy=y+(j-4.5)*.133
            box(name+' recessed gold terminal',(x+.02,yy,z-.035+side*.068),(.81,.058,.017),'gold',0)
    for sign in (-1,1):
        box(name+' shell retention spring',(x-.50,y+sign*.755,z+.19),(.31,.10,.045),'steel',.010,2)
    return obj

def graphics_assembly_details():
    # Cable runs follow the fixed fan supports, below the rotating blade surfaces.
    for index,x in enumerate((-10.43,0,10.43)):
        for wire in range(4):
            off=(wire-1.5)*.047
            H.cord('Fan motor wire '+str(index)+' '+str(wire),[(x+.45,off,4.37),(x+1.28,off,4.39),
                (x+3.57,.55+off,4.37),(x+4.62,.78+off,4.22),(x+4.94,2.55+off,3.56),
                (x+4.68,5.02+off,3.54)],.019,'rubber')
        box('Fan motor wire saddle',(x+3.6,.565,4.34),(.31,.32,.15),'plastic',.025,2)
        ring('Fan hub retaining lip',(x,0,5.053),.855,.792,.026,'graphite',sides=64)
    for wire in range(4):
        off=(wire-1.5)*.047
        H.cord('Shroud PWM harness', [(-5.75,5.02+off,3.54),(4.68,5.02+off,3.54),
               (14.91,5.02+off,3.54),(15.13,4.22+off,2.97),(13.65,3.73+off,1.17)],.019,'rubber')
    for x in (-5.74,4.68,14.93):
        box('Harness retaining clip',(x,5.03,3.57),(.21,.38,.17),'plastic',.026,2)
    box('Fan header solder base',(13.65,3.72,.63),(.66,.52,.14),'plastic',.012,2)
    connector=box('Four pin fan header',(13.65,3.72,.91),(.67,.50,.52),'plastic',.022,2)
    cut(connector,(13.65,3.72,1.12),(.51,.32,.42))
    for j in range(4):box('PWM header terminal',(13.43+j*.145,3.72,1.00),(.038,.038,.36),'solder',0)
    # The visible power connector carries a moulded latch and four small sense sockets.
    box('Power socket latch ramp',(9,-5.34,1.765),(.65,.40,.12),'plastic',.020,2)
    box('Power socket latch lip',(9,-5.59,1.795),(.72,.10,.14),'plastic',.015,2)
    sense=box('Power sense contact housing',(9,-5.36,1.95),(1.17,.75,.30),'plastic',.025,2)
    for j in range(4):
        xx=9+(j-1.5)*.255
        cut(sense,(xx,-5.64,1.95),(.155,.47,.14))
        box('Power sense terminal',(xx,-5.41,1.95),(.049,.14,.036),'solder',0)
    # Narrow ferrule bands and a turned cap make each exposed heat-pipe termination distinct.
    for i in range(5):
        yy=4.17+i*.19;zz=1.14+i*.23
        cap=cyl('Heatpipe sealed end',(13.78,yy,zz+.20),.176,.035,'steel',sides=24,radius=.012)
        cap.rotation_euler[1]=math.pi/2
    # Rear stiffening ribs belong to the metal backplate and stop before the vent field.
    for y in (-3.79,3.79):
        box('Stamped backplate reinforcing rib',(-4.0,y,.097),(18.8,.23,.076),'graphite',.025,3)
    for y in (-4.61,4.61):
        for x in (-12.75,-10.95,-9.15,-7.35,-5.55,-3.75,-1.95):
            box('Backplate pressed edge bead',(x,y,.095),(1.23,.11,.070),'graphite',.023,3)
    for y in (-5.63,5.63):
        # Formed retention-tab slot, same orientation as the mounting screw.
        tab=box('Chassis mounting flange',(-15.89,y,4.99),(.68,.48,.12),'steel',.025,2)
        round_cut(tab,(-15.90,y,4.99),.103,.40)

def fan_reference(x,y,z,index):
    r=4.75
    ring('Fan outer ring '+str(index),(x,y,z),r+.055,r-.065,.18,'plastic',sides=96)
    ring('Thin fan ring highlight '+str(index),(x,y,z+.10),r+.061,r+.018,.041,'graphite',sides=96)
    cyl('Fan motor hub '+str(index),(x,y,z+.04),1.09,.55,'plastic',sides=72,radius=.085)
    cyl('Hub satin medallion '+str(index),(x,y,z+.331),.78,.035,'hub',sides=64,radius=.022)
    for j in range(9):
        verts=[];faces=[];nr,nw=16,5
        for side in (0,1):
            for i in range(nr+1):
                t=i/nr;radius=1.03+3.57*t;centre=j*math.tau/9-.57*t-.10*t*t
                span=.22+.37*math.sin(t*math.pi*.59)
                for k in range(nw+1):
                    u=k/nw;a=centre+(u-.5)*span
                    # A rounded cambered face tapers to thinner leading/trailing edges.
                    thickness=.025+.026*math.sin(u*math.pi)*math.sin(t*math.pi*.82)
                    zz=z+.04+.21*math.sin(t*math.pi*.8)+(u-.5)*.29*t+thickness*side
                    zz+=.04*math.sin(u*math.pi)*math.sin(t*math.pi)
                    verts.append((x+radius*math.cos(a),y+radius*math.sin(a),zz))
        n=(nr+1)*(nw+1)
        for i in range(nr):
            for k in range(nw):
                a=i*(nw+1)+k;faces.extend(((a,a+1,a+nw+2,a+nw+1),(a+n+nw+1,a+n+nw+2,a+n+1,a+n)))
        perimeter=list(range(nw+1))+[i*(nw+1)+nw for i in range(1,nr+1)]+[nr*(nw+1)+k for k in range(nw-1,-1,-1)]+[i*(nw+1) for i in range(nr-1,0,-1)]
        for i,a in enumerate(perimeter):
            b=perimeter[(i+1)%len(perimeter)];faces.append((a,b,b+n,a+n))
        mesh=bpy.data.meshes.new('Swept compound blade');mesh.from_pydata(verts,[],faces);mesh.update()
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
        obj=bpy.data.objects.new('Fan '+str(index)+' blade '+str(j),mesh);bpy.context.collection.objects.link(obj);H.register(obj,obj.name,'blade')
        for face in mesh.polygons:face.use_smooth=True
    for a in (0,math.tau/3,math.tau*2/3):
        rigid_line('Motor support strut',[(x+.7*math.cos(a),y+.7*math.sin(a),z-.15),(x+4.5*math.cos(a+.16),y+4.5*math.sin(a+.16),z-.18)],.085,'plastic')

def gpu():
    board=pcb('Triple-fan GPU black PCB',(-.7,0,.45),(29.5,10.95,.18),[((-8.42,-5.45,.45),(.25,.8,.8))])
    edge_contacts('GPU PCIe contact',-11.24,-5.48,.45,13.17,106,.70,(-8.60,-8.24))
    back=poly_plate('Machined rear support plate',[(-15.45,-5.4),(12.9,-5.4),(15.5,-4.25),(15.5,4.52),(14.6,5.47),(-14.8,5.47),(-15.45,4.66)],.13,.31,'graphite',.10)
    for x in (7.1,8.05,9.0,9.95,10.9,11.85,12.8):
        cut(back,(x,1.1,.24),(.46,6.55,.85))
    for x in (-13.7,-7.9,-.8,5.7,13.8):
        for y in (-4.65,4.65):cyl('Backplate captive fixing',(x,y,.115),.13,.035,'steel',sides=28,radius=.006)
    chip('GPU package under cold plate',(-3,0,.77),4.42,4.42,.43,False)
    for x in (-5.8,-.2):
        for y in (-2.45,0,2.45):chip('Graphics memory package',(x,y,.70),1.33,1.45,.28,False)
    # Split heatsink banks leave a real interruption at the central cold plate.
    for x,length in ((-9.10,12.75),(6.48,16.36)):
        heat_sink('Dense graphics fin bank',(x,.15,1.04),length,9.52,2.18,47,'aluminum','X')
    for i in range(5):
        y=4.17+i*.19;z=1.14+i*.23
        H.cord('Nickel finished heat pipe',[(-13.9,y,z),(-14.8,y,z+.4),(-13.1,y,z+.67),(0,y,z+.73),(12.55,y,z+.66),(13.8,y,z+.19)],.17,'steel')
    outline=[(-16.07,-5.28),(-15.60,-5.95),(14.88,-5.95),(16.08,-5.13),(16.08,5.23),(15.35,5.96),(-15.38,5.96),(-16.07,5.08)]
    body=poly_plate('Three fan structural shroud',outline,3.66,4.87,'plastic',.075)
    cut(body,(0,0,3.86),(30.94,10.72,.92))
    for x in (-10.43,0,10.43):round_cut(body,(x,0,4.37),4.92,3.4)
    # Satin side panels share the fan openings with the load-bearing black frame.
    left=poly_plate('Left silver faceted cover',[(-16.11,-5.27),(-15.49,-5.97),(-4.01,-5.97),(-5.58,-4.45),(-5.17,-.77),(-5.50,4.53),(-4.18,5.97),(-15.45,5.97),(-16.11,5.06)],4.84,5.06,'silver',.075)
    right=poly_plate('Right silver faceted cover',[(4.10,-5.97),(15.43,-5.97),(16.11,-5.23),(16.11,5.08),(15.39,5.97),(4.10,5.97),(5.56,4.33),(5.13,.73),(5.56,-4.34)],4.84,5.06,'silver',.075)
    for obj,x in ((left,-10.43),(right,10.43)):round_cut(obj,(x,0,4.6),4.925,2.5)
    for obj,sign in ((left,-1),(right,1)):
        # Genuine shallow tool seams remain outside the fan openings.
        for y in (-5.04,5.04):
            cut(obj,(sign*10.50,y,5.065),(7.78,.058,.115))
        for x in (sign*15.70,sign*5.71):
            cut(obj,(x,0,5.07),(.056,3.20,.12))
    for sign in (-1,1):
        # Sloped, chamfered perimeter bars and asymmetric shallow cut channels.
        outline=[(-14.82,sign*5.73),(-6.04,sign*5.73),(-5.31,sign*5.34),(-14.51,sign*5.34)]
        poly_plate('Left perimeter bevel strip',outline,5.03,5.10,'steel',.025)
        outline=[(6.00,sign*5.72),(14.79,sign*5.72),(14.46,sign*5.33),(5.33,sign*5.33)]
        poly_plate('Right perimeter bevel strip',outline,5.03,5.10,'steel',.025)
    for x in (-15.10,-5.32,5.32,15.10):
        for y in (-4.75,4.75):
            cyl('Shroud recessed screw seat',(x,y,5.07),.19,.027,'plastic',sides=32,radius=.01)
            screw('Flush shroud screw',(x,y,5.075),.11)
            ring('Shroud captive washer',(x,y,5.078),.153,.115,.012,'graphite',sides=28)
    for x in (-13.67,-12.70,12.70,13.67):
        H.cut(left if x<0 else right,(x,5.75,5.03),(.45,.16,.16))
    poly_plate('Centre lower faceted bridge',[(-5.26,-5.95),(5.26,-5.95),(3.85,-4.77),(1.13,-4.93),(0,-4.39),(-1.13,-4.93),(-3.85,-4.77)],4.86,5.10,'graphite',.04)
    for index,x in enumerate((-10.43,0,10.43)):fan_reference(x,0,4.73,index)
    # The two axial faces expose fin ends through long side openings.
    for y in (-5.51,5.51):
        box('Shroud side lower rail',(0,y,3.03),(31.28,.20,.32),'graphite',.065,3)
        for x in (-15.10,-5.26,5.26,15.10):box('Shroud side support',(x,y,3.75),(.42,.20,1.26),'graphite',.065,3)
    bracket=box('Triple-slot display bracket',(-16.26,0,2.56),(.16,11.55,5.12),'steel',.055,3)
    for index,y in enumerate((-4.32,-1.58,1.24,4.09)):
        cut(bracket,(-16.26,y,1.18),(.60,1.98,.85))
        display_connector('HDMI output' if index==0 else 'DP output '+str(index),y,'HDMI' if index==0 else 'DP')
    for y in (-4.55,-3.03,-1.52,0,1.52,3.03,4.55):
        for z in (2.67,3.77):cut(bracket,(-16.26,y,z),(.56,1.02,.47))
    # Recessed compact power plug and individual contacts; it does not clip the fins.
    power=box('GPU compact power socket',(9.00,-5.28,1.19),(2.03,1.01,1.03),'plastic',.055,3)
    for row in (-1,1):
        for i in range(6):
            x=9.00+(i-2.5)*.27;z=1.19+row*.20
            cut(power,(x,-5.65,z),(.19,.65,.28));box('Power socket terminal',(x,-5.37,z),(.065,.12,.08),'solder',0)
    box('CS graphics side badge backing',(0,-5.62,3.10),(10.8,.055,1.44),'graphite',.045,3)
    panel('CS graphics side identification',(0,-5.653,3.10),10.65,1.425,'primary','FRONT')
    panel('Graphics underside serial',(-5.2,0,.104),7.38,1.476,'secondary','BOTTOM')
    graphics_assembly_details()

def ram():
    board=pcb('DDR4 black memory PCB',(0,-.08,.38),(13.35,3.17,.14),[
        ((.36,-1.61,.38),(.23,.59,.8)),((-6.63,.13,.38),(.27,.41,.8)),((6.63,.13,.38),(.27,.41,.8))])
    edge_contacts('DDR4 gold contact',-6.51,-1.41,.38,13.02,144,.47,(.19,.52))
    for sign in (-1,1):
        for j in range(8):chip('Memory package under spreader',(-5.61+j*1.61,.11,.38+sign*.14),1.28,1.45,.12,False)
    outline=[(-6.70,-.98),(-6.16,-1.17),(-3.32,-1.17),(-3.00,-1.08),(.08,-1.08),(.32,-.84),(.60,-1.07),
             (3.51,-1.07),(3.76,-1.16),(6.13,-1.16),(6.70,-.97),(6.70,1.26),(6.27,1.48),
             (5.46,1.48),(5.30,1.66),(3.85,1.66),(3.66,1.48),(-3.68,1.48),(-3.84,1.66),(-5.24,1.66),(-5.43,1.48),(-6.25,1.48),(-6.70,1.26)]
    front=poly_plate('CS front heat spreader',outline,.53,.76,'graphite',.030)
    rear=poly_plate('CS rear heat spreader',outline,.0,.23,'graphite',.030)
    for x in (-6.56,6.56):
        for obj in (front,rear):cut(obj,(x,.03,.38),(.30,.42,1.25))
    # Physical stamped end notches and open top cooling fins follow the reference face.
    for x in (-5.91,-5.39,-4.87,-4.35):
        for obj in (front,rear):cut(obj,(x,1.47,.38),(.30,.68,1.25))
    for x in (4.87,5.39):
        for obj in (front,rear):cut(obj,(x,1.63,.38),(.27,.49,1.25))
    box('DIMM top folded cap',(0,1.47,.38),(7.23,.18,.74),'graphite',.035,3)
    for x in (-3.48,3.48):box('Heat spreader retaining fold',(x,1.38,.38),(.22,.47,.73),'plastic',.035,3)
    # Angular embossed channels have geometry depth, with softer raised edge highlights.
    for points in ([(-6.13,-.80),(-3.49,-.80),(-2.80,-.43),(-.79,-.43),(.31,.66),(2.62,.66),(3.15,1.10)],
                   [(-6.00,-.61),(-3.66,-.61),(-2.83,-.24),(-.87,-.24),(.32,.86),(2.50,.86)],
                   [(2.67,-.82),(4.99,-.82),(5.87,-.39),(6.35,-.39)]):
        rigid_line('Stamped spreader channel',[(x,y,.771) for x,y in points],.018,'plastic')
    # Artwork follows the actual front faces, including stamped edge notches.
    # No rectangular overlay spans the cooling cut-outs.
    front['ram_face_art']=True
    # A small model-identity strip on the rear is inferred from the package construction.
    panel('Memory rear inventory marking',(0,.10,-.008),6.5,1.30,'secondary','BOTTOM')
    for x in (-6.35,6.35):
        cyl('DIMM assembly rivet',(x,.88,.779),.073,.018,'plastic',sides=20,radius=.003)

def ssd():
    board=pcb('Black M.2 2280 board',(0,0,.085),(8.0,2.20,.095),[
        ((3.65,.64,.085),(.77,.145,.6)),((3.63,-1.07,.085),(.61,.08,.6)),((3.63,1.07,.085),(.61,.08,.6))])
    # Open mounting semicircle at the end opposite the keyed edge contacts.
    round_cut(board,(-4.012,0,.085),.242,.8)
    collar=ring('M.2 mounting gold semicircle',(-4.005,0,.141),.303,.244,.014,'gold',sides=64)
    cut(collar,(-4.65,0,.141),(1.30,1.1,.65))
    for y in (-.965,.965):
        round_cut(board,(-3.84,y,.085),.052,.7)
        ring('M.2 end fiducial',(-3.84,y,.141),.087,.054,.014,'solder',sides=24)
    # Edge pads appear on both sides and stop at the physical M-key opening.
    for j in range(35):
        y=-1.005+(j+.5)*2.01/35
        if .556<y<.722:continue
        for side in (-1,1):box('M.2 connector gold pad',(3.72,y,.085+side*.053),(.53,.040,.012),'gold',0)
    for x in (-2.60,-.82,.95):
        chip('M.2 NAND package',(x,-.035,.181),1.53,1.43,.095,False)
    chip('M.2 controller',(2.69,-.11,.201),1.02,1.02,.133,True)
    chip('M.2 power manager',(2.30,.79,.197),.47,.40,.105,True)
    # The long matte black label sits on the memory packages, with exposed PCB margins.
    box('Black SSD label substrate',(-.86,-.07,.238),(6.00,1.48,.017),'chip',.014,2)
    panel('CS-S2 solid state label',(-.86,-.07,.248),5.91,1.285,'primary')
    # Reference-like populated component rails. Sizes stay within the board edges.
    for side in (-1,1):
        for j in range(29):
            x=-3.63+j*.223;y=side*.954
            if j%6==0:
                smd('Rail filter capacitor',(x,y,.181),(.159,.118,.064),'ceramic')
            else:smd('Rail resistor',(x,y,.159),(.099,.058,.037),'chip' if j%3 else 'ceramic')
    for x,y,w,h in ((2.79,.78,.28,.26),(3.16,.48,.19,.27),(3.10,-.85,.21,.30),(2.48,-.85,.26,.29),(-3.36,.62,.19,.22),(-3.53,-.61,.13,.24)):
        smd('Power stage capacitor',(x,y,.21),(w,h,.13),'ceramic')
    for x in (2.02,2.41,2.80,3.19):
        for y in (-.59,.57):smd('Controller bypass component',(x,y,.177),(.11,.07,.057),'ceramic')
    for x in (-3.80,-3.62,-3.44):
        for y in (.39,.58,.77):box('End test pad',(x,y,.145),(.060,.066,.018),'gold',0)
    for x in (3.05,3.20,3.35):
        for y in (-.58,-.44,-.30):box('Controller test point',(x,y,.145),(.047,.048,.016),'solder',0)
    for x in (-2.8,-.8,1.2):
        for y in (-.63,.63):smd('SSD reverse passive',(x,y,.024),(.14,.07,.026),'ceramic')
    panel('SSD reverse device serial',(-.20,0,.024),3.36,.63,'barcode','BOTTOM')

BUILDERS={'GPU':gpu,'RAM':ram,'SSD':ssd}
