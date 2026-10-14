# External display accessories, not functioning firearm assemblies.
def parts_tray():
 group('ComponentsTray')
 cube('Component tray base',(0,0,.012),(.59,.32,.024),M['dark'],.008)
 cube('Foam liner',(0,0,.026),(.565,.295,.008),M['black'],.004)
 for yy in [-.156,.156]:cube('Tray lip',(0,yy,.027),(.575,.01,.03),M['steel'],.003)
 for xx in [-.291,.291]:cube('Tray end lip',(xx,0,.027),(.01,.30,.03),M['steel'],.003)
 # Cosmetic handguard housing with an external mounting rail.
 cube('Handguard shell',(-.116,.072,.057),(.273,.052,.054),M['dark'],.009)
 cube('Handguard inset',(-.116,.044,.057),(.238,.003,.031),M['black'],.002)
 for i in range(8):cube('Handguard external vent',(-.218+i*.029,.042,.057),(.017,.002,.012),M['steel'],.002)
 cube('Rail backbone',(-.116,.072,.087),(.258,.027,.012),M['steel'],.0015)
 for i in range(13):cube('Rail top segment',(-.236+i*.02,.072,.096),(.011,.033,.006),M['dark'],.001)
 # Inert barrel-like display blank with capped ends.
 rod('Display tube',(-.252,-.046,.040),(.010,-.046,.040),.010,M['steel'])
 for xx in [-.212,-.030]:cube('Tube support',(xx,-.046,.033),(.022,.034,.012),M['black'],.002)
 # Optic exterior on foam, front lens coated blue.
 cyl('Optic tube',(.15,.065,.057),.025,.15,M['dark'],'X')
 for xx in [.083,.217]:ring('Optic end ring',(xx,.065,.057),.027,.005,M['steel'],'X')
 cyl('Optic glass',(.229,.065,.057),.022,.002,M['glass'],'X')
 cyl('Optic adjustment',(.157,.065,.09),.013,.018,M['dark']);cyl('Optic side dial',(.16,.034,.057),.011,.015,M['dark'],'Y')
 cube('Optic support',(.15,.065,.034),(.08,.04,.012),M['black'],.002)
 # Grip shell and small collar modules, with explicit gaps.
 o=cube('Detached grip shell',(.145,-.089,.055),(.091,.055,.048),M['dark'],.012);o.rotation_euler[2]=-.16
 for i in range(5):cube('Grip rib',(.111+i*.014,-.092,.079),(.004,.040,.0025),M['black'],.001)
 for xx in [.245,.275]:ring('Loose collar',(xx,-.072,.037),.012,.004,M['steel'])
 text('Tray identification','COMPONENTS',(0,-.163,.024),.012,M['paper'])

def work_mat():
 group('AssemblyMat')
 cube('Service mat',(0,0,.004),(.65,.36,.008),M['black'],.009)
 for x in [-.29,.29]:cube('Mat edge stripe',(x,0,.0085),(.001,.31,.001),M['shell'],.0001)
 # Keep the centre clear for assembly; tools lie in their own channels.
 for i in range(3):
  x=-.23+i*.075;rod('Screwdriver shaft',(x,.055,.015),(x,.144,.015),.003,M['steel'],12);rod('Screwdriver grip',(x,-.028,.018),(x,.049,.018),.009,M['orange'] if i==0 else M['dark'],16)
 # Small parts dish, no spilled geometry.
 cube('Fastener dish',(.20,.066,.017),(.14,.12,.024),M['dark'],.012)
 for i in range(4):bolt('Loose fastener',(.163+(i%2)*.045,.04+(i//2)*.043,.032),r=.006)
 text('Mat mark','SERVICE / ASSEMBLY',(0,-.153,.009),.014,M['paper'],rotation=(0,0,0))
