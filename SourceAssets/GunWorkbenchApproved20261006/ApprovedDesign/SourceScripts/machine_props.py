import bpy,math,random
from mathutils import Vector
GROUPS={};ACTIVE=''
def group(name):
 global ACTIVE;ACTIVE=name;GROUPS.setdefault(name,[])
def reg(o,mat=None):
 if mat:o.data.materials.append(mat)
 o['layout_group']=ACTIVE;GROUPS[ACTIVE].append(o);return o
def mat(name,c,metal=0,rough=.5):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;b=n.get('Principled BSDF');b.inputs['Base Color'].default_value=(*c,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
 tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=160;tex.inputs['Detail'].default_value=2;bn=n.new('ShaderNodeBump');bn.inputs['Strength'].default_value=.08;bn.inputs['Distance'].default_value=.0005;l.new(tex.outputs['Fac'],bn.inputs['Height']);l.new(bn.outputs[0],b.inputs['Normal']);return m
M={}
def materials():
 M.update(shell=mat('Printer ceramic powdercoat',(.37,.43,.43),.55,.4),dark=mat('Graphite anodized frames',(.026,.035,.041),.72,.32),steel=mat('Brushed steel',(.38,.43,.47),.9,.27),black=mat('Rubber and belts',(.012,.018,.02),0,.72),orange=mat('Amber safety accents',(.82,.24,.045),.35,.4),brass=mat('Aged brass small fittings',(.46,.30,.1),.85,.34),paper=mat('Warm white labels',(.7,.72,.67),0,.7),blue=mat('Press blue-grey enamel',(.055,.14,.20),.45,.42),red=mat('Safety red',(.5,.027,.014),.1,.5))
 glass=mat('Smoked safety glazing',(.43,.66,.71),0,.07);bs=glass.node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=.88;bs.inputs['IOR'].default_value=1.45;M['glass']=glass
 screen=mat('Screen dark glass',(.007,.025,.04),.1,.23);M['screen']=screen
 for key,col in [('cyan',(.02,.7,.85)),('green',(.08,.8,.33))]:
  mm=mat('LED '+key,col,0,.35);b=mm.node_tree.nodes.get('Principled BSDF');b.inputs['Emission Color'].default_value=(*col,1);b.inputs['Emission Strength'].default_value=.65;M[key]=mm

def cube(name,loc,dim,material,bevel=.002):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:md=o.modifiers.new('Machined soft edges','BEVEL');md.width=bevel;md.segments=3;md.harden_normals=True;wn=o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');wn.keep_sharp=True
 return reg(o,material)
def cyl(name,loc,r,depth,material,axis='Z',verts=32):
 bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc);o=bpy.context.object;o.name=name
 if axis=='X':o.rotation_euler[1]=math.pi/2
 elif axis=='Y':o.rotation_euler[0]=math.pi/2
 for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
 be=o.modifiers.new('Edge bevel','BEVEL');be.width=min(.0012,r*.14,depth*.15);be.segments=2
 return reg(o,material)
def rod(name,a,b,r,material,verts=20):
 a,b=Vector(a),Vector(b);o=cyl(name,(a+b)/2,r,(b-a).length,material,verts=verts);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o

def ring(name,loc,major,minor,material,axis='Z'):
 bpy.ops.mesh.primitive_torus_add(major_segments=40,minor_segments=8,location=loc,major_radius=major,minor_radius=minor);o=bpy.context.object;o.name=name
 if axis=='Y':o.rotation_euler[0]=math.pi/2
 if axis=='X':o.rotation_euler[1]=math.pi/2
 for p in o.data.polygons:p.use_smooth=True
 return reg(o,material)
def text(name,body,loc,size,material,rotation=(math.pi/2,0,0)):
 cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.size=size;cu.extrude=.00012;cu.align_x='CENTER';o=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=rotation;return reg(o,material)
def bolt(name,loc,axis='Z',r=.006):
 o=cyl(name,loc,r,.004,M['steel'],axis,6);return o

def cable(name,pts,r=.003):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=10;cu.bevel_depth=r;cu.bevel_resolution=3;sp=cu.splines.new('BEZIER');sp.bezier_points.add(len(pts)-1)
 for b,p in zip(sp.bezier_points,pts):b.co=p;b.handle_left_type='AUTO';b.handle_right_type='AUTO'
 o=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(o);return reg(o,M['black'])
def printer():
 group('Printer')
 for x in [-.185,.185]:
  for y in [-.18,.18]:cyl('Printer rubber foot',(x,y,.013),.024,.026,M['black'])
 cube('Printer rigid base',(0,0,.055),(.45,.45,.068),M['shell'],.008)
 cube('Printer base inset',(0,-.229,.063),(.39,.012,.036),M['dark'],.003)
 for x in [-.203,.203]:
  for y in [-.202,.202]:
   cube('Aluminium upright',(x,y,.318),(.026,.026,.468),M['dark'],.002)
   cube('Extrusion centre groove',(x,y-.014,.32),(.005,.002,.43),M['steel'],.0004)
 for y in [-.203,.203]:cube('Top cross rail',(0,y,.556),(.432,.03,.033),M['dark'])
 for x in [-.203,.203]:cube('Top side rail',(x,0,.556),(.03,.38,.033),M['dark'])
 cube('Rear electronics panel',(0,.207,.315),(.372,.016,.442),M['shell'],.006)
 cube('Rear exhaust grille',(0,.220,.445),(.14,.012,.105),M['black'])
 for i in range(10):cube('Exhaust fin',(-.063+i*.014,.228,.445),(.005,.005,.087),M['steel'],.0006)
 for x in [-.164,.164]:
  rod('Z guide rod',(x,.08,.108),(x,.08,.521),.006,M['steel']);cyl('Z stepper body',(x,.086,.113),.025,.034,M['dark'])
  rod('Z lead screw',(x,-.015,.14),(x,-.015,.504),.005,M['steel'])
  for z in [.15+i*.026 for i in range(14)]:ring('Lead screw accent',(x,-.015,z),.0055,.0011,M['steel'])
 cube('Bed support carrier',(0,.03,.141),(.335,.28,.014),M['dark'])
 cube('Build plate',(0,-.013,.159),(.30,.304,.013),M['steel'],.002)
 cube('PEI build surface',(0,-.013,.1665),(.294,.298,.002),M['black'],.0005)
 for x in [-.14,.14]:
  for y in [-.15,.124]:bolt('Bed adjust bolt',(x,y,.17),r=.004)
 cube('Printed sample module',(-.044,-.022,.190),(.066,.073,.045),M['orange'],.005)
 for i in range(9):cube('Sample layer line',(-.044,-.060,.171+i*.0048),(.058,.0008,.0007),M['dark'],.0001)
 for z in [.410,.443]:rod('X gantry rail',(-.182,0,z),(.182,0,z),.006,M['steel'])
 cube('Toolhead carrier',(.045,0,.414),(.067,.048,.074),M['dark'],.004)
 cube('Toolhead shroud',(.045,-.037,.402),(.078,.035,.066),M['shell'],.005)
 cyl('Toolhead fan recess',(.045,-.057,.407),.023,.005,M['black'],'Y')
 for i in range(7):
  a=i*2*math.pi/7;rod('Fan grille spoke',(.045,-.061,.407),(.045+.021*math.cos(a),-.061,.407+.021*math.sin(a)),.0017,M['steel'],8)
 cyl('Nozzle collar',(.045,-.01,.365),.012,.015,M['steel']);bpy.ops.mesh.primitive_cone_add(vertices=24,radius1=.003,radius2=.011,depth=.016,location=(.045,-.01,.349));reg(bpy.context.object,M['brass'])
 cube('Gantry drive belt',(0,.027,.466),(.35,.009,.005),M['black'],.0005)
 for x in [-.17,.17]:cyl('Belt idler',(x,.027,.466),.013,.011,M['dark'],'Y')
 cube('Safety front glass',(0,-.211,.322),(.365,.003,.42),M['glass'],.001)
 cube('Door handle',(.156,-.24,.315),(.016,.019,.122),M['dark'],.005)
 for z in [.20,.47]:cube('Door hinge',(-.185,-.219,z),(.025,.018,.033),M['steel'],.002)
 cube('Status screen',(0,-.239,.068),(.116,.006,.036),M['screen'],.001)
 text('Printer screen line','READY  |  FAB-03',(0,-.243,.074),.0068,M['cyan'])
 cube('Progress bar',(-.012,-.244,.062),(.068,.001,.003),M['green'],.0002)
 cyl('Control dial',(.104,-.24,.068),.012,.014,M['dark'],'Y');cyl('Control dial cap',(.104,-.249,.068),.009,.003,M['steel'],'Y')
 text('Printer top mark','3D FABRICATOR',(0,-.222,.548),.012,M['paper'])
 # Filament spool mounted safely above rear, entirely inside footprint margin.
 rod('Spool mount',(-.07,.12,.569),(-.07,.18,.64),.013,M['dark'])
 rod('Spool axle',(-.07,.12,.66),(-.07,.255,.66),.011,M['steel'])
 for y in [.152,.227]:
  ring('Spool flange',(-.07,y,.66),.093,.008,M['dark'],'Y');cyl('Spool hub',(-.07,y,.66),.025,.013,M['dark'],'Y')
  for i in range(6):
   a=i*math.pi/3;rod('Spool spoke',(-.07+.025*math.cos(a),y,.66+.025*math.sin(a)),(-.07+.086*math.cos(a),y,.66+.086*math.sin(a)),.005,M['dark'])
 for i in range(10):ring('Wound filament',(-.07,.16+i*.0065,.66),.076,.004,M['orange'],'Y')
 cable('Filament guide',[(-.145,.18,.702),(-.16,.10,.78),(.02,-.005,.66),(.045,-.005,.451)],.0019)
 for x in [-.20,.20]:
  for z in [.10,.542]:bolt('Frame bolt',(x,-.22,z),'Y',.0045)
 cube('Service side stripe',(.22,.055,.30),(.003,.10,.15),M['orange'],.001)
 cable('Printer supply cable',[(.18,.21,.08),(.21,.28,.07),(.1,.29,.012)],.004)

def press():
 group('AmmoPress')
 for x in [-.155,.155]:
  for y in [-.13,.13]:cyl('Press isolation foot',(x,y,.012),.026,.024,M['black'])
 cube('Press cast base',(0,0,.05),(.38,.34,.065),M['blue'],.012)
 cube('Press bed support',(0,-.015,.10),(.255,.24,.055),M['dark'],.007)
 cube('Press work surface',(0,-.018,.131),(.26,.24,.009),M['steel'],.002)
 # Single solid side columns and upper bridge; external non-operational game prop.
 for x in [-.14,.14]:
  cube('Press cast column',(x,.07,.313),(.072,.12,.46),M['blue'],.011)
  cube('Column milled inset',(x,.004,.33),(.028,.006,.306),M['dark'],.003)
  rod('Polished guide rail',(x*.62,-.015,.18),(x*.62,-.015,.474),.011,M['steel'])
 cube('Upper cast bridge',(0,.038,.541),(.357,.23,.088),M['blue'],.012)
 cube('Upper bevel cover',(0,.035,.601),(.29,.19,.037),M['dark'],.007)
 cyl('Ram housing',(0,-.03,.437),.047,.147,M['dark']);cyl('External ram sleeve',(0,-.03,.328),.024,.101,M['steel']);cyl('Ram tip cover',(0,-.03,.274),.032,.02,M['dark'])
 cube('Enclosed lower block',(0,-.026,.161),(.087,.083,.05),M['dark'],.008)
 cube('Safety clear guard',(0,-.15,.303),(.25,.004,.294),M['glass'],.002)
 for x in [-.126,.126]:cube('Guard side rail',(x,-.148,.302),(.01,.011,.303),M['orange'],.0015)
 cube('Guard lower grip',(0,-.16,.157),(.09,.02,.018),M['dark'],.004)
 # Motor housing and covered flywheel on the side.
 cyl('Press motor',(.225,.087,.50),.066,.10,M['dark'],'X')
 for i in range(8):cyl('Motor cooling fin',(.181+i*.012,.087,.50),.071,.004,M['steel'],'X')
 cyl('Drive cover',(-.198,.075,.48),.088,.035,M['blue'],'X');ring('Drive cover trim',(-.219,.075,.48),.079,.004,M['dark'],'X')
 for i in range(8):
  a=i*math.pi/4;bolt('Drive cover fastener',(-.221,.075+.068*math.cos(a),.48+.068*math.sin(a)),'X',.0035)
 cyl('Lever pivot',(.195,-.015,.36),.022,.03,M['steel'],'X');rod('Press handle',(.21,-.02,.36),(.28,-.18,.23),.009,M['steel']);rod('Press handle rubber',(.28,-.18,.23),(.30,-.228,.198),.015,M['black'])
 cube('Control housing',(-.10,-.191,.072),(.14,.035,.059),M['dark'],.004)
 cyl('Emergency stop',(-.142,-.216,.075),.014,.012,M['red'],'Y');cyl('Ready lamp',(-.078,-.214,.078),.005,.005,M['green'],'Y')
 text('Press nameplate','AMMO PRESS',(0,-.083,.552),.021,M['paper'])
 text('Press designation','MK-II / BENCH UNIT',(0,-.085,.531),.009,M['paper'])
 cyl('Gauge case',(.095,-.093,.579),.027,.015,M['dark'],'Y');cyl('Gauge face',(.095,-.102,.579),.023,.001,M['paper'],'Y')
 for i in range(11):
  a=math.radians(-30+i*24);rod('Gauge tick',(.095+.017*math.cos(a),-.104,.579+.017*math.sin(a)),(.095+.021*math.cos(a),-.104,.579+.021*math.sin(a)),.0007,M['black'],6)
 rod('Gauge needle',(.095,-.105,.579),(.085,-.105,.592),.00065,M['red'],8)
 for x in [-.154,.154]:
  for y in [-.133,.133]:bolt('Anchor bolt',(x,y,.085),r=.006)
 cable('Protected wiring',[(.16,.16,.51),(.15,.20,.36),(.11,.20,.13)],.006)
 return GROUPS['AmmoPress']
