"""Turn a usable thrown bowl, fracture its wall, and dress one with barley pottage.
All shaping dimensions are in centimetres. Exported origins are at the foot ring."""
import math
import random
from pathlib import Path

import bpy

OUT = Path(__file__).resolve().parents[4] / "SourceAssets/HillsVillageTavern/DiningBowls"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
with bpy.data.libraries.load(str(OUT.parent / "Service/TaproomService.blend"), link=False) as (src, dst):
    dst.materials = ["Clay", "HoneyGlaze", "AshGlaze"]
mats = {m.name: m for m in dst.materials}
food = bpy.data.materials.new("Pottage")
food.use_nodes = True
color_node = food.node_tree.nodes.new("ShaderNodeVertexColor")
color_node.layer_name = "FoodSurface"
shader = food.node_tree.nodes.get("Principled BSDF")
food.node_tree.links.new(color_node.outputs["Color"], shader.inputs["Base Color"])
food.node_tree.links.new(color_node.outputs["Alpha"], shader.inputs["Roughness"])
mats[food.name] = food
TAU = math.tau
POT = (1, 1, 1, 1)


class Body:
    def __init__(self):
        self.points, self.lookup, self.faces, self.data = [], {}, [], []

    def face(self, points, uv, slot, smooth=True, colors=None):
        ids, coords, rgba = [], [], []
        for p, coord, color in zip(points, uv, colors or [POT] * len(points)):
            key = tuple(round(v, 6) for v in p)
            if key not in self.lookup:
                self.lookup[key] = len(self.points)
                self.points.append(tuple(v / 100 for v in p))
            index = self.lookup[key]
            if index not in ids:
                ids.append(index)
                coords.append(coord)
                rgba.append(color)
        if len(ids) >= 3:
            self.faces.append(ids)
            self.data.append((slot, smooth, coords, rgba))

    def make(self, name):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.points, [], self.faces)
        mesh.update()
        names = list(dict.fromkeys(d[0] for d in self.data))
        for s in names:
            mesh.materials.append(mats[s])
        uv = mesh.uv_layers.new(name="CraftUV")
        colors = mesh.color_attributes.new(name="FoodSurface", type="FLOAT_COLOR", domain="CORNER") if "Pottage" in names else None
        for poly, (slot, smooth, coords, rgba) in zip(mesh.polygons, self.data):
            poly.material_index = names.index(slot)
            poly.use_smooth = smooth
            for loop, coord, color in zip(poly.loop_indices, coords, rgba):
                uv.data[loop].uv = coord
                if colors:
                    colors.data[loop].color = color
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.modifiers.new("Export triangles", "TRIANGULATE")
        return obj


FLOOR = 1.34
SHOULDER = 6.84
# Outer and inner radii of the wheel-thrown wall at the same height.
WALL = [(FLOOR, 5.15, 3.80), (1.65, 5.53, 4.60), (2.05, 5.97, 5.21),
        (2.65, 6.58, 5.90), (3.33, 7.12, 6.52), (4.15, 7.70, 7.12),
        (4.95, 8.18, 7.63), (5.64, 8.54, 8.00), (6.24, 8.83, 8.31),
        (6.52, 8.94, 8.46), (6.67, 9.04, 8.53), (SHOULDER, 9.13, 8.60)]


def interpolate(rows, x):
    for (x0, y0), (x1, y1) in zip(rows, rows[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * max(0, (x - x0) / (x1 - x0))
    return rows[-1][1]


def radius(z, inside):
    return interpolate([(row[0], row[2 if inside else 1]) for row in WALL], z)


def thrown(a, r, z):
    rr = r * (1 + .005 * math.cos(2*a+.2) + .0025 * math.sin(3*a-.18*z))
    rise = (z / SHOULDER) ** 1.7 * (.045 * math.sin(3*a+.7) + .018 * math.cos(5*a))
    return (rr * math.cos(a), rr * math.sin(a), z + rise)


def wheel_face(body, samples, slot, smooth=True):
    body.face([thrown(a, r, z) for a, r, z in samples],
              [(a / TAU * 2.5, (z + .22*r)/14) for a, r, z in samples], slot, smooth)


def limit(a):
    # The impact removes a broad scallop and two smaller adjacent flakes down one side.
    profile = [(0,SHOULDER),(.12,6.77),(.20,6.05),(.31,5.88),(.39,4.79),
               (.52,4.64),(.62,3.91),(.77,3.43),(.83,2.69),(.91,2.82),
               (1.04,2.32),(1.14,2.53),(1.21,2.46),(1.31,3.26),(1.42,3.00),
               (1.53,3.71),(1.68,3.98),(1.79,4.54),(1.95,4.70),(2.05,5.80),
               (2.17,5.68),(2.25,6.15),(2.33,6.31),(2.40,SHOULDER)]
    p = (a + .65) % TAU
    return interpolate(profile, p)


def clip_strip(a0, a1, low, high, ceiling0, ceiling1):
    boundary = [(a0,low), (a1,low), (a1,high), (a0,high)]
    def distance(point):
        a,z = point
        return ceiling0 + (ceiling1-ceiling0) * (a-a0)/(a1-a0) - z
    kept = []
    for previous, current in zip(boundary[-1:]+boundary[:-1], boundary):
        d0,d1 = distance(previous),distance(current)
        if (d0 >= 0) != (d1 >= 0):
            t = d0/(d0-d1)
            kept.append(tuple(x+t*(y-x) for x,y in zip(previous,current)))
        if d1 >= 0:
            kept.append(current)
    return kept


def bowl(body, segments, broken):
    # The recessed underside meets the table only along the flat, unglazed foot.
    lower = [(0,.38),(2.96,.38),(3.09,.33),(3.20,.09),(3.29,0),
             (3.63,0),(3.72,.09),(3.76,.24),(3.69,.42),(3.70,.54),
             (3.87,.62),(4.21,.73),(4.60,.91),(4.90,1.12),(5.15,FLOOR)]
    inside = [(3.80,FLOOR),(3.36,1.24),(2.80,1.16),(2.10,1.12),(1.1,1.10),(0,1.10)]
    heights = sorted(set([r[0] for r in WALL]+[1.90,4.82,4.91,5.36,5.50,5.73,5.82]))

    def slip_line(a, z, internal):
        # A pair of pale trailing lines just under the outside lip, interrupted at the break.
        if internal:
            return "HoneyGlaze"
        if z < 1.90:
            return "Clay"
        if 4.82 < z < 4.91 or 5.36 < z < 5.50:
            return "AshGlaze"
        return "HoneyGlaze"

    def crown_point(a, z, j):
        t = j / 4
        r = radius(z,False)*(1-t) + radius(z,True)*t
        fullness = max(0, 1 - (SHOULDER-z)/.12)
        r += fullness * .09 * math.sin(TAU*t)
        z += fullness * .28 * math.sin(math.pi*t)
        z += (1-fullness) * math.sin(math.pi*t)*(.033*math.sin(39*a)+.046*math.cos(22*a))
        return (a,r,z)

    angles = [i * TAU / segments for i in range(segments+1)]
    for a,b in zip(angles, angles[1:]):
        for profile,slot in [(lower,"Clay"),(inside,"HoneyGlaze")]:
            for (r,z),(s,h) in zip(profile,profile[1:]):
                wheel_face(body, [(a,r,z),(b,r,z),(b,s,h),(a,s,h)],slot)
        za,zb = (limit(a),limit(b)) if broken else (SHOULDER,SHOULDER)
        for lo,hi in zip(heights,heights[1:]):
            patch = clip_strip(a,b,lo,hi,za,zb)
            if len(patch) < 3:
                continue
            for internal in (False,True):
                samples = [(u,radius(h,internal),h) for u,h in patch]
                wheel_face(body,samples[::-1] if internal else samples,slip_line(a,(lo+hi)/2,internal))
        # Split the cap where the crack crosses profile rows. Matching rim vertices keep
        # each fracture side continuous with both walls even on steep jagged segments.
        cuts = [0.,1.]
        if abs(zb-za)>1e-6:
            cuts += [(h-za)/(zb-za) for h in heights if min(za,zb)<h<max(za,zb)]
        cuts.sort()
        for t0,t1 in zip(cuts,cuts[1:]):
            u,v = a+t0*(b-a), a+t1*(b-a)
            h,k = za+t0*(zb-za), za+t1*(zb-za)
            intact = min(h,k)>SHOULDER-.015
            for j in range(4):
                wheel_face(body,[crown_point(u,h,j),crown_point(v,k,j),crown_point(v,k,j+1),
                                 crown_point(u,h,j+1)],"HoneyGlaze" if intact else "Clay",intact)


def ingredient(body, points, colors, smooth=True):
    body.face(points,[(x/12+.5,y/12+.5) for x,y,z in points],"Pottage",smooth,colors)


LIQUID = 4.92


def broth(body, n):
    rim = radius(LIQUID,True)
    steps = 9
    def surface(a, j):
        f = j/steps
        x,y,_ = thrown(a,(rim+.045)*f,LIQUID)
        wave = .55*math.sin(2.3*x+.9*y)+.45*math.cos(1.2*x-1.8*y)
        z = LIQUID + .011*wave + .038*f**13
        shade = 1 + .105*math.sin(1.05*x+math.cos(1.18*y))+.035*wave
        return (x,y,z),(.18*shade,.066*shade,.015*shade,.245+.035*wave)
    for j in range(steps):
        for i in range(n):
            a,b = TAU*i/n,TAU*(i+1)/n
            ring = [surface(a,j),surface(a,j+1),surface(b,j+1),surface(b,j)]
            ingredient(body,[v[0] for v in ring],[v[1] for v in ring])


def carrot(body,x,y,yaw,size,tilt,n,seed):
    # A knife-cut half-round, the inner vascular core subtly paler than its outer flesh.
    outline = [(math.cos(math.pi*i/n), math.sin(math.pi*i/n)-.30) for i in range(n+1)]
    outline += [(-.47,-.31),(.28,-.285)]
    def point(i,scale,height):
        u,v = outline[i]
        noise = 1+.033*math.sin(3*u+4*v+seed)
        a,b = u*size*scale*noise, v*size*scale*noise
        return (x+math.cos(yaw)*a-math.sin(yaw)*b,
                y+math.sin(yaw)*a+math.cos(yaw)*b,LIQUID+height+tilt*a)
    def color(i,s,top):
        value = .92+.07*math.cos(i*2.7+seed)+.05*math.sin(i*.7+s*1.8)
        rgb = (.59,.168,.022) if top and s<.48 else ((.52,.105,.010) if top else (.355,.068,.008))
        return (*[c*value for c in rgb],.39 if top else .34)
    layers = [(1,-.27),(1,.12),(.965,.19),(.84,.202),(.46,.206),(.34,.207),(0,.209)]
    for q,((s,z),(ss,zz)) in enumerate(zip(layers,layers[1:])):
        for i in range(len(outline)):
            k=(i+1)%len(outline)
            coords=[(i,s,z),(k,s,z),(k,ss,zz),(i,ss,zz)]
            ingredient(body,[point(*v) for v in coords],[color(i,s,q>=2) for i,s,_ in coords],q>0)


def grain(body,x,y,yaw,size,seed,n):
    radii=[(0,-1),(.72,-.74),(.97,-.29),(1,.16),(.88,.55),(.56,.85),(0,1)]
    def point(a,ring):
        r,l=radii[ring]
        along=l*size
        cross=math.cos(a)*r*.44*size
        fold = max(0.,math.sin(a)) * max(0.,1-abs(math.cos(a))/.31)**2
        high=(math.sin(a)-.32*fold)*r*.37*size
        val=(.93+.05*math.cos(a+seed)+.045*l)*(1-.37*fold)
        return ((x+math.cos(yaw)*along-math.sin(yaw)*cross,y+math.sin(yaw)*along+math.cos(yaw)*cross,
                 LIQUID+.035+high+.11*along),(.47*val,.31*val,.133*val,.36))
    for j in range(len(radii)-1):
        for i in range(n):
            a,b=TAU*i/n,TAU*(i+1)/n
            batch=[point(a,j),point(b,j),point(b,j+1),point(a,j+1)]
            ingredient(body,[p for p,c in batch],[c for p,c in batch])


def pottage(body,n):
    broth(body,max(24,n//2))
    rng = random.Random(322)
    chunks = [(2.42,-2.2,.76,1.27,.19),(-2.78,1.47,2.1,1.09,-.13),(.41,3.99,-.84,.87,.17),
              (4.21,1.16,2.87,.80,-.21)]
    occupied = [(x,y,s*.91) for x,y,_,s,_ in chunks]
    for i,(x,y,a,s,t) in enumerate(chunks):
        carrot(body,x,y,a,s,t,max(7,n//7),i)
    for _ in range(190):
        if len(occupied) >= 34:
            break
        phi,d=rng.uniform(0,TAU),6.6*math.sqrt(rng.random())
        x,y=d*math.cos(phi),d*math.sin(phi)
        if any(math.hypot(x-u,y-v)<r+.30 for u,v,r in occupied):
            continue
        s=rng.uniform(.27,.43)
        grain(body,x,y,rng.uniform(0,TAU),s,phi,12 if n>=48 else 8)
        occupied.append((x,y,s*.85))
    # A few softened leek slivers lying partly submerged, with a shallow fold along the leaf.
    for (x,y,a,l) in [(-4.1,-1.65,-.3,1.25),(.14,-3.36,1.27,.92),(2.09,2.20,.11,1.12),
                      (-.6,1.27,-.89,.73),(-3.86,3.54,2.64,.66)]:
        def leaf(t,d):
            off=.18*math.sin(t*math.pi)+d*(.025+.105*math.sin(t*math.pi))
            along=(t-.5)*l
            return (x+math.cos(a)*along-math.sin(a)*off,y+math.sin(a)*along+math.cos(a)*off,
                    LIQUID+.068*math.sin(t*math.pi)+.025*(1-abs(d))-.012)
        for j in range(4):
            for d in (-1,0):
                coords=[(j/4,d),((j+1)/4,d),((j+1)/4,d+1),(j/4,d+1)]
                ingredient(body,[leaf(*p) for p in coords],
                           [(.074+.056*(1-abs(e)),.114+.046*(1-abs(e)),.027,.36) for t,e in coords])


for i,(name,broken,served) in enumerate([("EatingBowl",False,False),("BrokenBowl",True,False),("StewBowl",False,True)]):
    name = "SM_Tavern"+name
    group = bpy.data.objects.new(name+"_LODs",None)
    group["fbx_type"]="LodGroup"
    bpy.context.collection.objects.link(group)
    meshes = []
    for level,n in enumerate((96,48,24)):
        body = Body()
        bowl(body,n,broken)
        if served:
            pottage(body,n)
        mesh = body.make(name+"_LOD"+str(level))
        mesh.parent = group
        meshes.append(mesh)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [group]+meshes:
        obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+".fbx")),use_selection=True,object_types={"EMPTY","MESH"},
                             axis_forward="-Y",axis_up="Z",mesh_smooth_type="FACE",use_tspace=True,
                             colors_type="LINEAR",bake_anim=False,use_custom_props=True,add_leaf_bones=False)
    group.location.x=i*.23
    for mesh in meshes[1:]:
        mesh.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"TavernDiningBowls.blend"))
