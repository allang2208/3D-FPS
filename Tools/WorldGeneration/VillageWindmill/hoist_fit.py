"""Fixed loft and brake fittings in the local metre coordinates of each master."""
import math

import bpy
from mathutils import Matrix, Vector

import milling
from millkit import PALETTE, beam, box, cyl, mesh, torus


def radial_section(name, center, profile, angles, axis, material):
    """Sweep a closed radial profile, capping the ends of each split housing."""
    points = []
    faces = []
    width = len(profile)
    for i, angle in enumerate(angles):
        c, s = math.cos(angle), math.sin(angle)
        for r, h in profile:
            offset = (h, r*c, r*s) if axis == "X" else (r*c, r*s, h)
            points.append(tuple(Vector(center) + Vector(offset)))
        if i:
            for j in range(width):
                k = (j+1) % width
                faces.append(((i-1)*width+j, i*width+j, i*width+k, (i-1)*width+k))
    # Profiles run from the bore to the outside along the bottom face.
    faces.append(tuple(range(width)))
    faces.append(tuple(reversed(range(len(points)-width, len(points)))))
    return mesh(name, points, faces, material)


def loft_guide():
    # The iron journal spans Z 5.73–5.99 m in the tower. Both bush halves
    # sit inside that journal length, with their flange seated on the deck.
    for side in (-1, 1):
        mid = math.pi if side < 0 else 0.
        angles = [mid + (i/48-.5)*(math.pi-.024) for i in range(49)]
        radial_section("Split loft guide stave", (0, 0, 0),
                       [(.142,-.117),(.162,-.117),(.162,.033),(.142,.033)],
                       angles, "Z", "endgrain")
        radial_section("Flanged split iron guide", (0, 0, 0),
                       [(.162,-.121),(.193,-.121),(.193,0),(.303,0),
                        (.303,.018),(.197,.018),(.197,.037),(.162,.037)],
                       angles, "Z", "iron")
        # The existing joist runs along X, centred on Y=.05. Both studs
        # pass through the deck and uncut joist, outside the .235 m opening.
        x = side*.260
        box("Guide backing plate under joist", (x,.05,-.338), (.062,.144,.012), "iron", .002)
        for y in (.006,.094):
            cyl("Guide through stud", (x,y,-.361), (x,y,.032), .008, "iron", 16)
            cyl("Guide square head", (x,y,.018), (x,y,.031), .020, "iron", 4)
            cyl("Guide stud nut", (x,y,-.356), (x,y,-.344), .016, "iron", 6)


def brake_hangers():
    # A06 is 64.1 cm below the brake-wheel axis. The oak sheers sit
    # .331 m above A06 and have .230 m depth at this wheel station.
    rail_bottom = -.641 + .331 - .230/2
    for name, sign in (("Dead end cap mounting foot",1),("Lever bracket foot",-1)):
        foot = bpy.data.objects[name]
        corners = [foot.matrix_world @ Vector(p) for p in foot.bound_box]
        x = sum(p.x for p in corners)/8
        y = sum(p.y for p in corners)/8
        z = min(p.z for p in corners)
        rail = sign*1.70
        box("Brake foot saddle", (x,y,z-.020), (.214,.332,.040), "iron", .004)
        box("Brake hanger under sheer", (rail,y,rail_bottom-.016),
            (.256,.374,.032), "iron", .003)
        # Two offset cheeks straddle the moving linkage. Each bends outboard
        # below the brake track before rising to the two bolts in the sheer.
        for yy in (y-.125,y+.125):
            knee = (rail,yy,z+.204)
            beam("Bent brake hanger lower arm", (x,yy,z-.020), knee, .069,.052,"iron")
            beam("Brake hanger riser", knee, (rail,yy,rail_bottom-.016), .069,.052,"iron")
            cyl("Sheer hanger bolt", (rail,yy,rail_bottom-.043),
                (rail,yy,rail_bottom+.238), .011,"iron",16)
            cyl("Sheer hanger top washer", (rail,yy,rail_bottom+.230),
                (rail,yy,rail_bottom+.237), .027,"iron",16)
            cyl("Sheer hanger square nut", (rail,yy,rail_bottom+.237),
                (rail,yy,rail_bottom+.252), .021,"iron",4)
            cyl("Brake foot bolt head", (x,yy,z-.052), (x,yy,z-.039), .020,"iron",6)


def journal_stands():
    moving = ("Journal hanger", "Hanger clamping band", "Split journal box",
              "Iron journal bushing", "Through bearing clamp", "Hanger diagonal",
              "Brace heel cap", "Cap drawbore")
    old_fork = ("Sheave outrigger", "Forged pulley cheek", "Pulley strap rivet",
                "Fixed pulley spindle", "Pin locking washer", "Pin cross wedge")
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(old_fork):
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        if not obj.name.startswith(moving):
            continue
        corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
        sign = 1 if sum(p.x for p in corners) > 0 else -1
        trim = 0.
        if obj.name.startswith("Iron journal bushing"):
            # Original inner lips at ±.293; rotating left collar at -.295,
            # right ratchet at +.315. Shorten the inboard lip only. The
            # .042 bore keeps its running clearance on the .039 axle.
            trim = .005
        elif sign > 0 and obj.name.startswith(("Journal hanger","Through bearing clamp")):
            trim = .006
        if trim:
            shift = obj.matrix_world.to_3x3().inverted() @ Vector((sign*trim,0,0))
            for v in obj.data.vertices:
                if (obj.matrix_world @ v.co).x * sign < .30:
                    v.co += shift
        if sign > 0:
            obj.location.x += .020
    # Neck down the pin at the pawl face while retaining the original thick
    # hinge seat in the hanger. The rotating teeth clear the smaller end.
    pin = bpy.data.objects["Pawl hinge"]
    bpy.data.objects.remove(pin, do_unlink=True)
    cyl("Pawl hinge tenon", (.290,-.017,-.719),(.323,-.017,-.719),.006,"iron",24)
    cyl("Pawl hinge shoulder", (.323,-.017,-.719),(.444,-.017,-.719),.013,"iron",24)
    # The released master has the nose inside a tooth. Rotate on its
    # original pin until the nose rests against the stationary tooth flank.
    pawl = bpy.data.objects["Drop pawl"]
    hinge = Matrix.Translation((0,-.017,-.719))
    pawl.matrix_world = hinge @ Matrix.Rotation(math.radians(-23),4,"X") @ hinge.inverted() @ pawl.matrix_world


def fork():
    # Keep the two arms clear of the grooved rim and the lifting line.
    for x in (.087,.273):
        beam("Raised oak sheave arm", (x,.06,.024), (x,-.704,.254), .084,.092,"oak")
        beam("Pulley arm knee", (x,-.065,-.056), (x,-.392,.151), .064,.065,"darkwood")
        # Forge the bored eye separately from the flat tang. The eye and
        # tang meet above the pin; its central hole runs through both cheeks.
        plate = [(x-.010,-.691,.229), (x-.010,-.555,.199),
                 (x-.010,-.592,.134), (x-.010,-.668,.134)]
        milling.slab("Pulley cheek tang", plate, (.02,0,0), "iron")
        milling.lathe_x("Pulley cheek eye", [(-.010,.053),(.010,.053),
                        (.010,.021),(-.010,.021)], "iron", (x,-.63,.10))
        for y,z in ((-.604,.192),(-.666,.215)):
            cyl("Pulley cheek through rivet", (x-.047,y,z),(x+.047,y,z),.010,"iron",12)
    cyl("Fixed loft pulley spindle", (.058,-.63,.10),(.304,-.63,.10),.021,"iron",48)
    cyl("Head of pulley spindle", (.055,-.63,.10),(.077,-.63,.10),.035,"iron",20)
    milling.lathe_x("Pulley pin keeper washer", [(-.005,.034),(.005,.034),
                    (.005,.021),(-.005,.021)], "iron", (.289,-.63,.10))
    cyl("Pulley pin cotter", (.299,-.655,.093),(.299,-.605,.107),.004,"iron",10)


def line_and_hook():
    # A .145 m pitch radius seats the rope in C11's concave groove and
    # meets the scanned winding at the outboard side of its final wrap.
    x, r = .18, .145
    drum_y, drum_z = 0., -.90
    guide_y, guide_z = -.63,.10
    angle = math.atan2(drum_y-guide_y, guide_z-drum_z)

    def arc(cx, cy, cz, a, radius=r):
        return Vector((cx, cy+radius*math.cos(a), cz+radius*math.sin(a)))

    # The scanned coil thins outboard of X=.15. Lead its last wrap from
    # the actual rope surface, over the barrel, to the sheave's X plane.
    points = []
    for i in range(91):
        f = i/90
        ease = f*f*(3-2*f)
        points.append(arc(.143+.037*ease,drum_y,drum_z,
                          angle-.88*math.tau*(1-f),.142+.003*ease))
    tangent = arc(x,guide_y,guide_z,angle)
    start = points[-1]
    for i in range(1,121):
        points.append(start.lerp(tangent,i/120))
    for i in range(1,49):
        points.append(arc(x,guide_y,guide_z,angle+(math.pi-angle)*i/48))
    # The fall lies above the centre seam of the shut trapdoors. Finish
    # in a spliced eye and a short iron sack hook drawn up to the sheave.
    y = guide_y-r
    for dy,z in ((0,.078),(0,.064),(-.001,.054),(-.006,.046),
                 (-.012,.037),(-.011,.031),(-.006,.026),(0,.024),
                 (.006,.029),(.008,.036),(.007,.043),(.004,.049),(.003,.059)):
        points.append(Vector((x,y+dy,z)))
    # C07 has no hemp in the old master. Create the canonical export slot
    # if needed, including when the active Blender installation is localized.
    rope = bpy.data.materials.get("Mill / rope")
    if rope is None:
        rope = bpy.data.materials.new("Mill / rope")
        rope.diffuse_color = (*PALETTE["rope"],1.)
    line = milling.tube("Laid hoist fall and spliced eye",points,.0086,rope,12)
    length = 0.
    for i, p in enumerate(points):
        if i:
            length += (p-points[i-1]).length
        for j in range(12):
            v = line.data.vertices[12*i+j]
            twist = 3*math.tau*j/12 - math.tau*length/.031
            v.co = p + (v.co-p)*(.96+.04*math.cos(twist))
    for face in line.data.polygons:
        face.use_smooth = True
    torus("Forged sack hook eye", (x,y,.016),.015,.0045,"iron","Y")
    path = [(0,.019),(-.002,.009),(-.003,-.006),(0,-.018),(.007,-.027),
            (.018,-.030),(.028,-.026),(.036,-.017),(.037,-.005),(.033,.004)]
    centers = [Vector((x+dx,y,z-.017)) for dx,z in path]
    hook = milling.tube("Turned up sack hook", centers, .007, "iron", 12)
    for i,radius in enumerate((.85,1,1,1,1,1,.92,.78,.55,.21)):
        for j in range(12):
            v = hook.data.vertices[12*i+j]
            v.co = centers[i] + (v.co-centers[i])*radius
    for face in hook.data.polygons:
        face.use_smooth = True


def prepare(part):
    if part == "C07":
        bpy.context.view_layer.update()
        journal_stands()
        fork()
        line_and_hook()
    elif part == "B04":
        bpy.context.view_layer.update()
        brake_hangers()
    elif part == "D03":
        loft_guide()
