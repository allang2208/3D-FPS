"""Power-theme precision operator console, authored in metres.

New, independent geometry: the approved Archive DispatchConsole V2 stays intact.
Entry point: ``build_console(g, atlas)``. All visible faces and separate convex
collision primitives belong to (``ConsolePrototype``, ``Machine``). The caller
owns source assembly, placement, export and material assignment. No executable
scene entry point, rendering, UE operations, interaction or tests live here.

Envelope: approximately 2.76 W x 1.04 D x 1.88 H; ground pivot, front -Y.
Materials: existing Paint/Steel/Enamel/Yellow/Rubber and the theme's existing
Ceramic/Dark/Red/Labels. Ceramic supplies the warm ivory instrument inserts.
A sloped folded-sheet hood surrounds a genuine recessed CRT aperture. Visible
bevels, meter ticks/needles, keys, screw slots, louver folds and cable glands are
geometry. No random stains, damage stamps or emissive display are generated.
"""
import math
from mathutils import Vector

KIND = 'Machine'
ATLAS_KEYS = (
    'console_title', 'console_meter_v', 'console_meter_a', 'console_status',
    'console_select', 'console_service', 'console_emergency', 'console_id',
)


def _outline(width, height, radius, steps=4):
    """CCW rounded rectangle, same number of vertices at every radius."""
    w, h = width / 2, height / 2
    r = min(radius, w * .95, h * .95)
    result = []
    for cx, cy, start in ((w-r, h-r, 0), (-w+r, h-r, 90),
                           (-w+r, -h+r, 180), (w-r, -h+r, 270)):
        for i in range(steps + 1):
            a = math.radians(start + i * 90 / steps)
            result.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return result


def _panel(g, c, normal, width, height, depth, mat='Paint', radius=.014,
           edge=.002):
    """Closed sheet/casting with rounded plan corners and real edge bevels."""
    n, u, v = g.basis(normal)
    c = Vector(c)
    e = min(edge, depth * .24, width * .08, height * .08)
    sections = [(-depth/2, width-2*e, height-2*e, max(.0001, radius-e)),
                (-depth/2+e, width, height, radius),
                (depth/2-e, width, height, radius),
                (depth/2, width-2*e, height-2*e, max(.0001, radius-e))]
    vs = []
    for d, w, h, r in sections:
        vs.extend(c + n*d + u*x + v*y for x, y in _outline(w, h, r))
    count = len(vs) // 4
    fs = [tuple(reversed(range(count))), tuple(3*count+i for i in range(count))]
    for k in range(3):
        fs.extend((k*count+i, k*count+(i+1)%count,
                   (k+1)*count+(i+1)%count, (k+1)*count+i)
                  for i in range(count))
    g.poly(KIND, vs, fs, mat)


def _frame(g, c, normal, width, height, inner_width, inner_height, depth,
           mat='Steel', radius=.03, inner_radius=.02):
    """Closed annulus with a real hole, not a dark rectangle on a solid slab."""
    n, u, v = g.basis(normal)
    c = Vector(c)
    loops = []
    # Beveled front outer edge, reveal wall and rear return are one shell.
    for d, w, h, r in ((-depth/2, width, height, radius),
                       (depth/2-.004, width, height, radius),
                       (depth/2, width-.008, height-.008, max(.001, radius-.004)),
                       (depth/2, inner_width, inner_height, inner_radius),
                       (-depth/2, inner_width, inner_height, inner_radius)):
        loops.append([c + n*d + u*x + v*y for x, y in _outline(w, h, r)])
    count = len(loops[0])
    vs = [p for loop in loops for p in loop]
    fs = []
    for k in range(len(loops)):
        kk = (k+1) % len(loops)
        fs.extend((k*count+i, k*count+(i+1)%count,
                   kk*count+(i+1)%count, kk*count+i) for i in range(count))
    g.poly(KIND, vs, fs, mat)


def _extrude_x(g, outline_yz, x0, x1, mat='Paint', collision=False,
               visible=True):
    """Closed constant-X extrusion; convex outlines can also become UCX."""
    count = len(outline_yz)
    vs = [(x, y, z) for x in (x0, x1) for y, z in outline_yz]
    fs = [tuple(reversed(range(count))), tuple(count+i for i in range(count))]
    fs.extend((i, (i+1)%count, (i+1)%count+count, i+count) for i in range(count))
    if visible:
        g.poly(KIND, vs, fs, mat)
    if collision:
        g.hull(KIND, vs, fs)


def _fold(g, c, normal, width, profile, mat='Paint'):
    """Closed folded sheet strip, extruded along its local horizontal axis."""
    n, u, v = g.basis(normal)
    c = Vector(c)
    count = len(profile)
    vs = [c + u*x + n*d + v*h for x in (-width/2, width/2)
          for d, h in profile]
    fs = [tuple(reversed(range(count))), tuple(count+i for i in range(count))]
    fs.extend((i, (i+1)%count, (i+1)%count+count, i+count) for i in range(count))
    g.poly(KIND, vs, fs, mat)


def _screw(g, c, normal, radius=.006):
    """Low-profile slotted captive screw, sized for instrument sheet metal."""
    n, u, v = g.basis(normal)
    c = Vector(c)
    g.ring(KIND, c+n*.0008, n, radius*1.30, radius*.45, .0016, 'Steel', 16)
    g.lathe(KIND, c+n*.0014, n,
            [(0, radius), (.0020, radius), (.0035, radius*.82)], 'Steel', 16)
    # The screw-slot insert sits 0.1 mm above the head, so it never flickers.
    _panel(g, c+n*.0050, n, radius*1.23, radius*.22, .0005,
           'Dark', radius*.08, .0001)


def _label(g, atlas, c, normal, width, height, key, screws=True):
    """Individual UV-mapped Chinese enamel label, retained in Machine group."""
    n, u, v = g.basis(normal)
    c = Vector(c)
    # Print the sole front of a solid plate; the old 0.1 mm overlay gap flickered.
    g.printed_plate(KIND,c,width,height,key,normal,atlas,depth=.005,margin=.0035)
    if screws:
        for side in (-1, 1):
            _screw(g, c+u*side*(width/2-.012)+n*.0008, n, .0032)


def _face_line(g, c, normal, a, b, thickness=.0014, mat='Dark'):
    n, u, v = g.basis(normal)
    c = Vector(c)
    p, q = c+u*a[0]+v*a[1], c+u*b[0]+v*b[1]
    g.beam(KIND, p, q, thickness, thickness*.60, mat)


_DIGITS = {
    '0': 'abcedf', '1': 'bc', '2': 'abged', '3': 'abgcd',
    '4': 'fgbc', '5': 'afgcd', '6': 'afgecd', '7': 'abc',
    '8': 'abcdefg', '9': 'abfgcd',
}
_SEGMENTS = {
    'a': ((-.34, .5), (.34, .5)), 'b': ((.4, .44), (.4, .06)),
    'c': ((.4, -.06), (.4, -.44)), 'd': ((-.34, -.5), (.34, -.5)),
    'e': ((-.4, -.44), (-.4, -.06)), 'f': ((-.4, .06), (-.4, .44)),
    'g': ((-.34, 0), (.34, 0)),
}


def _digits(g, c, normal, text, height=.014, mat='Dark'):
    """Tiny real stamped scale numerals; no dependency on an extra font atlas."""
    n, u, v = g.basis(normal)
    c = Vector(c)
    step = height * .72
    for index, digit in enumerate(text):
        center = c + u*(index-(len(text)-1)/2)*step
        for key in _DIGITS[digit]:
            a, b = _SEGMENTS[key]
            _face_line(g, center, n, (a[0]*height*.7, a[1]*height),
                       (b[0]*height*.7, b[1]*height), height*.065, mat)


def _meter(g, c, normal, radius=.151, needle_degrees=65):
    n, u, v = g.basis(normal)
    c = Vector(c)
    # Five physically stepped rings rather than a texture of a dial.
    g.ring(KIND, c+n*.004, n, radius*1.035, radius*.80, .012, 'Rubber', 48)
    g.ring(KIND, c+n*.013, n, radius, radius*.825, .022, 'Steel', 64)
    g.ring(KIND, c+n*.026, n, radius*.947, radius*.855, .009, 'Paint', 64)
    g.ring(KIND, c+n*.031, n, radius*.875, radius*.838, .004, 'Steel', 64)
    g.lathe(KIND, c+n*.011, n, [(0, radius*.838), (.004, radius*.838)],
            'Ceramic', 64)
    face = c+n*.016
    for i in range(41):
        a = math.radians(210-i*6)
        outer = radius*.744
        inner = radius*(.616 if i%5 == 0 else .674)
        _face_line(g, face, n, (inner*math.cos(a), inner*math.sin(a)),
                   (outer*math.cos(a), outer*math.sin(a)),
                   .0024 if i%5 == 0 else .00125)
    for index, text in enumerate(('0', '25', '50', '75', '100')):
        a = math.radians(210-index*60)
        at = face + (u*math.cos(a)+v*math.sin(a))*radius*.49
        _digits(g, at, n, text, .014)
    # Short red danger arc occupies only the upper end of the scale.
    for i in range(6):
        a, b = math.radians(-30+i*3), math.radians(-27+i*3)
        _face_line(g, face, n, (radius*.781*math.cos(a), radius*.781*math.sin(a)),
                   (radius*.781*math.cos(b), radius*.781*math.sin(b)), .0023, 'Red')
    a = math.radians(needle_degrees)
    tip = face+n*.004 + (u*math.cos(a)+v*math.sin(a))*radius*.704
    tail = face+n*.004 - (u*math.cos(a)+v*math.sin(a))*radius*.125
    g.beam(KIND, tail, tip, .0032, .0019, 'Red')
    g.lathe(KIND, face+n*.003, n, [(0, .0085), (.0045, .0070)], 'Steel', 24)
    for side in (-1, 1):
        _screw(g, c+u*side*radius*.925+n*.027, n, .0035)
    # The glass is represented by its held edge; no opaque disk hides the scale.


def _selector(g, c, normal, angle=0, large=False):
    n, u, v = g.basis(normal)
    c = Vector(c)
    r = .043 if large else .032
    g.ring(KIND, c+n*.004, n, r*1.22, r*.70, .012, 'Steel', 32)
    g.lathe(KIND, c+n*.012, n,
            [(0, r), (.021, r*.96), (.027, r*.81)], 'Rubber', 32)
    direction = u*math.sin(angle)+v*math.cos(angle)
    # Tactile bar bridges the cap; the pointer has actual 3-D relief.
    g.beam(KIND, c+n*.041-direction*r*.73,
           c+n*.041+direction*r*.73, .014, .014, 'Dark')
    g.beam(KIND, c+n*.049+direction*r*.18,
           c+n*.049+direction*r*.65, .0033, .0015, 'Ceramic')
    for a in (-.8, 0, .8):
        dd=u*math.sin(a)+v*math.cos(a)
        g.beam(KIND, c+n*.009+dd*r*1.35,
               c+n*.009+dd*r*1.58, .0025, .002, 'Ceramic')


def _button(g, c, normal, mat='Ceramic', width=.083, height=.059):
    n, u, v = g.basis(normal)
    c = Vector(c)
    _panel(g, c+n*.003, n, width+.013, height+.013, .008,
           'Rubber', .009, .001)
    _frame(g, c+n*.010, n, width+.007, height+.007,
           width-.004, height-.004, .011, 'Steel', .008, .006)
    _panel(g, c+n*.018, n, width-.013, height-.013, .018,
           mat, .007, .0025)
    # Small dark identification dash occupies just the upper edge of each cap.
    _panel(g, c+n*.0277+v*height*.17, n, width*.24, .0022, .0007,
           'Dark', .0004, .0001)


def _hinge(g, c):
    c = Vector(c)
    for side in (-1, 1):
        _panel(g, c+Vector((side*.018, 0, 0)), (0,-1,0), .027, .088,
               .007, 'Steel', .003, .001)
        for dz in (-.030, .030):
            _screw(g, c+Vector((side*.019, -.0048, dz)), (0,-1,0), .0038)
    for i in range(3):
        lo = c+Vector((0, -.0075, -.044+i*.030))
        g.cylinder(KIND, lo, lo+Vector((0,0,.027)), .0085, 'Steel', 20)
    for dz in (-.046, .046):
        g.lathe(KIND, c+Vector((0,-.0075,dz)), (0,0,1),
                [(0,.010),(.002,.010)], 'Steel', 20)


def _louver(g, c, normal, width=.46, height=.30, count=8):
    n, u, v = g.basis(normal)
    c = Vector(c)
    _panel(g, c-n*.025, n, width-.014, height-.014, .006,
           'Dark', .009, .001)
    _frame(g, c, n, width+.018, height+.018, width-.015, height-.015,
           .014, 'Steel', .014, .008)
    pitch = (height-.023)/count
    for i in range(count):
        cc=c+v*((i-(count-1)/2)*pitch)
        # Folded Z section, 2.4 mm sheet, genuine open slots between the blades.
        _fold(g, cc, n, width-.033,
              [(-.012,-.009),(.004,-.007),(.012,.010),(.012,.014),
               (.0095,.014),(.0095,.0105),(.002,-.0045),(-.012,-.0065)],
              'Paint')
    for x in (-1,1):
        for y in (-1,1):
            _screw(g, c+u*x*(width/2-.007)+v*y*(height/2-.005)+n*.008,
                   n, .0035)


def _crt(g, c, normal):
    n, u, v = g.basis(normal)
    c = Vector(c)
    # Clear hole in the front plate; a deep reveal surrounds the glass.
    _frame(g, c+n*.003, n, .996, .596, .849, .462, .018,
           'Rubber', .054, .041)
    _frame(g, c+n*.019, n, .962, .565, .827, .442, .050,
           'Ceramic', .049, .037)
    _frame(g, c-n*.006, n, .830, .445, .786, .403, .065,
           'Dark', .038, .027)
    # Slightly bulged, fully closed low-poly CRT glass with a rounded outline.
    outer = _outline(.784, .401, .032, 6)
    count = len(outer)
    vs = []
    for depth, scale in ((-.049,1),(-.041,1),(-.030,.66),(-.025,.26)):
        vs.extend(c+n*depth+u*x*scale+v*y*scale for x,y in outer)
    fs = [tuple(reversed(range(count))), tuple(3*count+i for i in range(count))]
    for k in range(3):
        fs.extend((k*count+i,k*count+(i+1)%count,
                   (k+1)*count+(i+1)%count,(k+1)*count+i) for i in range(count))
    g.poly(KIND, vs, fs, 'Enamel', smooth=[False,False]+[True]*(3*count))
    # Heavy visor, lower metal lip and visible retaining screws.
    _panel(g, c+v*.286+n*.033, n, .933, .033, .051,
           'Paint', .009, .003)
    for x in (-.459,.459):
        for y in (-.243,.243):
            _screw(g, c+u*x+v*y+n*.044, n, .0045)
    # Six square service keys under the CRT, each seated in a dark socket.
    for i in range(6):
        _button(g, c+u*((i-2.5)*.116)-v*.334+n*.002, n,
                'Ceramic' if i<5 else 'Yellow', .073, .037)


def build_console(g, atlas):
    """Append one freestanding precision console; placement belongs to caller."""
    missing = [key for key in ATLAS_KEYS if key not in atlas.get('rects', {})]
    if missing:
        raise KeyError('Console requires atlas keys: '+', '.join(missing))
    g.ROOM = 'ConsolePrototype'
    front = Vector((0,-1,0))

    # Continuous grounded plinth with an inset kick space and attachment feet.
    _panel(g, (0,.010,.078), (0,0,1), 2.62, .772, .156,
           'Dark', .025, .005)
    _panel(g, (0,.005,.157), (0,0,1), 2.684, .822, .042,
           'Paint', .023, .004)
    for x in (-1.18,1.18):
        for y in (-.285,.305):
            _panel(g, (x,y,.018), (0,0,1), .145, .125, .036,
                   'Rubber', .015, .003)
    g.box(None, (0,.010,.080), (2.62,.772,.160), collision=KIND)

    # Lower carcass: folded side plates have real cut-outs around the louvers.
    g.box(KIND, (0,.397,.568), (2.626,.035,.790), 'Paint')
    g.box(KIND, (0,.002,.190), (2.60,.786,.024), 'Steel')
    for side in (-1,1):
        n=Vector((side,0,0))
        x=side*1.331
        # Perimeter closure around the side ventilation aperture.
        _panel(g, (x,-.316,.592), n, .178,.818,.026,'Paint',.008,.002)
        _panel(g, (x,.326,.592), n, .180,.818,.026,'Paint',.008,.002)
        _panel(g, (x,.004,.817), n, .468,.369,.026,'Paint',.007,.002)
        _panel(g, (x,.004,.292), n, .468,.168,.026,'Paint',.007,.002)
        _louver(g, (side*1.348,.004,.508), n,.454,.284,8)
        for y in (-.367,.378):
            for z in (.240,.955):
                _screw(g,(side*1.347,y,z),n,.005)
        # Sheet-metal folded hems line the outer case edges.
        g.box(KIND,(side*1.307,-.395,.585),(.042,.025,.804),'Paint')
        g.box(KIND,(side*1.307,.395,.585),(.042,.025,.804),'Paint')

    # Three separate lower service doors with tight, intentional dark seams.
    for index,x in enumerate((-.891,0,.891)):
        _panel(g,(x,-.406,.574),front,.874,.760,.021,'Dark',.014,.002)
        _panel(g,(x,-.425,.574),front,.854,.742,.025,'Paint',.013,.003)
        _frame(g,(x,-.440,.574),front,.830,.718,.803,.691,.007,
               'Paint',.014,.010)
        for z in (.309,.826):
            _hinge(g,(x-.390,-.445,z))
        # Recessed pull handle and quarter-turn lock, both modelled in depth.
        _panel(g,(x+.306,-.443,.706),front,.088,.183,.008,'Dark',.021,.001)
        _panel(g,(x+.306,-.449,.706),front,.066,.153,.012,'Steel',.018,.002)
        g.tube(KIND,[(x+.306,-.457,.653),(x+.306,-.480,.670),
                     (x+.306,-.480,.739),(x+.306,-.457,.758)],.010,'Dark',12)
        g.lathe(KIND,(x+.306,-.446,.827),front,
                [(0,.017),(.007,.017),(.010,.014)],'Steel',24)
        _panel(g,(x+.306,-.457,.827),front,.003,.020,.001,'Dark',.0005,.0002)
        # Rib/return across the bottom protects the access leaf from boots.
        _panel(g,(x,-.444,.236),front,.796,.033,.010,'Steel',.004,.001)
        if index==1:
            _label(g,atlas,(x,-.445,.537),front,.491,.078,'console_service')
        else:
            # Handed inventory numbers are true stamped geometry.
            _digits(g,(x-.284,-.440,.846),front,str(index+1),.025,'Ceramic')
    g.box(None,(0,-.010,.580),(2.71,.895,.812),collision=KIND)

    # Keyboard shelf: 10.5-degree working rake, double folded front edge.
    da=math.radians(10.5)
    dn=Vector((0,-math.sin(da),math.cos(da)))
    du=Vector((1,0,0));dv=Vector((0,math.cos(da),math.sin(da)))
    dc=Vector((0,-.313,1.040))
    def dpoint(x,y,d=0):
        return dc+du*x+dv*y+dn*d
    _panel(g,dc,dn,2.76,.495,.050,'Paint',.018,.004)
    _fold(g,dpoint(0,-.246,-.002),dn,2.72,
          [(-.018,-.011),(.015,-.011),(.025,-.004),(.025,.013),
           (.020,.013),(.020,-.002),(.012,-.006),(-.018,-.006)],'Steel')
    for x in (-1.31,1.31):
        for y in (-.20,.20):
            _screw(g,dpoint(x,y,.027),dn,.005)
    # Sloping deck is a separate simple convex wedge in the collision group.
    corners=[dpoint(x,y,d) for d in (-.033,.049)
             for x,y in [(-1.38,-.2475),(1.38,-.2475),(1.38,.2475),(-1.38,.2475)]]
    g.hull(KIND,corners,g.FACES)

    # Recessed detachable keyboard well, 61 individual sculpted raised keys.
    kc=dpoint(-.100,-.019,.029)
    _panel(g,kc,dn,1.123,.329,.015,'Rubber',.022,.002)
    _frame(g,kc+dn*.009,dn,1.101,.313,1.058,.271,.014,'Steel',.019,.011)
    for row in range(4):
        for column in range(14):
            x=-.590+column*.0753
            y=.080-row*.056
            key_center=dpoint(x,y,.049)
            _panel(g,key_center,dn,.065,.046,.017,'Ceramic',.004,.0023)
            # Concave-cap impression with a tiny unobtrusive engraved dash.
            if row<3:
                _panel(g,key_center+dn*.0088+dv*.006,dn,.015,.0016,.0004,
                       'Dark',.0003,.00008)
    # Four-function row is offset left/right around a wide space bar.
    for x,width in ((-.559,.105),(-.430,.107),(-.100,.469),(.229,.107),(.359,.107)):
        _panel(g,dpoint(x,-.161,.049),dn,width,.040,.017,'Ceramic',.004,.0023)
    _panel(g,dpoint(-.100,-.215,.035),dn,1.098,.038,.018,'Rubber',.009,.002)

    # Left deck hand switch and ID; right deck five tactile command buttons.
    _label(g,atlas,dpoint(-.985,.142,.029),dn,.468,.056,'console_id')
    _selector(g,dpoint(-1.073,-.065,.027),dn,-.72,True)
    _selector(g,dpoint(-.840,-.065,.027),dn,.72,False)
    _panel(g,dpoint(.867,.002,.029),dn,.650,.272,.014,'Steel',.014,.002)
    for i,mat in enumerate(('Ceramic','Ceramic','Yellow','Yellow','Red')):
        _button(g,dpoint(.625+(i%3)*.208,.064-(i//3)*.119,.039),dn,mat,.130,.071)
    # The last position is a guarded rotary switch, not an extra colored block.
    _selector(g,dpoint(1.041,-.055,.039),dn,0,False)
    for side in (-1,1):
        _panel(g,dpoint(.867+side*.292,0,.040),dn,.013,.220,.020,
               'Paint',.003,.001)

    # Closed folded hood. The front fascia is assembled around the CRT hole.
    angle=math.radians(18)
    n=Vector((0,-math.cos(angle),math.sin(angle)))
    u=Vector((1,0,0));v=Vector((0,math.sin(angle),math.cos(angle)))
    center=Vector((0,-.023,1.477))
    def point(x,y,d=0):
        return center+u*x+v*y+n*d
    hood_outline=[(-.156,1.078),(.415,1.078),(.415,1.858),
                  (.119,1.877),(.099,1.864),(-.155,1.097)]
    for side in (-1,1):
        _extrude_x(g,hood_outline,side*1.342-.016,side*1.342+.016,'Paint')
        # Thin darker edge return follows the sloped side, no fake wear scatter.
        g.beam(KIND,point(side*1.349,-.393,.007),
               point(side*1.349,.393,.007),.018,.021,'Steel')
    g.box(KIND,(0,.408,1.475),(2.665,.022,.752),'Paint')
    _panel(g,(0,.255,1.861),(0,0,1),2.728,.320,.023,'Paint',.016,.003)
    g.box(KIND,(0,.111,1.082),(2.672,.579,.027),'Paint')
    # Two side fascia sheets; center strips leave a deep 0.83 x 0.45 CRT opening.
    _panel(g,point(-.918,0),n,.850,.794,.018,'Paint',.010,.002)
    _panel(g,point(.918,0),n,.850,.794,.018,'Paint',.010,.002)
    _panel(g,point(0,.351),n,.989,.094,.018,'Paint',.008,.002)
    _panel(g,point(0,-.348),n,.989,.101,.018,'Paint',.008,.002)
    # Small outer return strips close the reveal in front of the hood shell.
    for x in (-.510,.510):
        _panel(g,point(x,.004),n,.029,.604,.019,'Paint',.005,.001)
    # Convex hood collision intentionally excludes tiny controls and screws.
    _extrude_x(g,[(-.174,1.071),(.427,1.071),(.427,1.881),
                  (.095,1.881),(-.174,1.114)],-1.369,1.369,
               collision=True,visible=False)

    # Paired analog meters: ivory dials, 41 ticks, five numeric stations, needles.
    for x,key,needle in ((-1.112,'console_meter_v',73),(-.734,'console_meter_a',126)):
        _meter(g,point(x,.121,.013),n,.151,needle)
        _label(g,atlas,point(x,.333,.012),n,.309,.050,key,screws=False)
        _selector(g,point(x,-.165,.013),n,-.72 if x<-.9 else .72)
    _label(g,atlas,point(-.922,-.314,.012),n,.660,.061,'console_select')

    # Central inactive CRT, recessed into the sheet metal, plus header plate.
    _crt(g,point(0,.007,.004),n)
    _label(g,atlas,point(0,.355,.015),n,.839,.054,'console_title')

    # Sixteen discrete pushbutton sockets, insulated key caps and number tags.
    _panel(g,point(.916,.085,.014),n,.732,.454,.009,'Dark',.014,.0015)
    for row in range(4):
        for column in range(4):
            x=.635+column*.181
            y=.252-row*.107
            mat='Yellow' if (row+column)%5 == 0 else 'Ceramic'
            _button(g,point(x,y,.022),n,mat,.100,.065)
            _digits(g,point(x,y-.044,.0235),n,str(row*4+column+1),.010,'Ceramic')
    _label(g,atlas,point(.916,.353,.013),n,.699,.051,'console_status')
    # Mushroom emergency stop: concentric yellow escutcheon and ribbed red cap.
    ec=point(1.160,-.285,.014)
    g.lathe(KIND,ec,n,[(0,.056),(.007,.056)],'Yellow',40)
    g.lathe(KIND,ec+n*.007,n,[(0,.032),(.025,.032)],'Steel',32)
    g.lathe(KIND,ec+n*.027,n,[(0,.043),(.005,.050),(.027,.050),(.034,.041)],'Red',48)
    for i in range(18):
        a=i*math.tau/18
        a0=ec+n*.035+(u*math.cos(a)+v*math.sin(a))*.0505
        a1=ec+n*.052+(u*math.cos(a)+v*math.sin(a))*.0505
        g.beam(KIND,a0,a1,.0021,.0018,'Red')
    _label(g,atlas,point(.811,-.285,.015),n,.440,.063,'console_emergency')
    # Recessed machine screws pin each removable fascia quadrant.
    for x in (-1.310,-.526,.526,1.310):
        for y in (-.373,.373):
            _screw(g,point(x,y,.012),n,.0048)

    # Rear service plates and restrained cable routing remain within footprint.
    for x in (-.885,0,.885):
        _panel(g,(x,.427,1.453),(0,1,0),.818,.603,.011,'Paint',.013,.0015)
        for dx in (-.364,.364):
            for z in (1.190,1.718):
                _screw(g,(x+dx,.434,z),(0,1,0),.0045)
    for index,x in enumerate((-.320,-.160,0,.160)):
        c=Vector((x,.415,.254))
        ax=Vector((0,1,0))
        g.lathe(KIND,c,ax,[(0,.022),(.008,.022),(.012,.018),(.027,.018)],
                'Steel',12)
        g.lathe(KIND,c+ax*.026,ax,[(0,.015),(.011,.015),(.016,.011)],
                'Rubber',16)
        g.tube(KIND,[(x,.457,.254),(x,.457,.170),
                     (x,.448,.097),(x+.052,.424,.069),
                     (x+.154,.380,.069)],.009,'Rubber',12)
    for x in (-.22,.14):
        _panel(g,(x,.430,.147),(0,1,0),.284,.026,.010,'Steel',.004,.001)
        for dx in (-.118,.118):
            _screw(g,(x+dx,.436,.147),(0,1,0),.0035)
