"""Carve two table implements in centimetres and export their three authored LODs."""
from bisect import bisect_right
from math import cos, pi, sin, tau
from pathlib import Path

import bpy


OUT = Path(__file__).resolve().parents[4] / 'SourceAssets/HillsVillageTavern/EatingUtensils'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0


def wood_material():
    mat = bpy.data.materials.new('EatingWood')
    mat.use_nodes = True
    tree = mat.node_tree
    shader = tree.nodes.get('Principled BSDF')
    for suffix, socket in [('Color','Base Color'),('Roughness','Roughness'),('Normal','Normal')]:
        tex = tree.nodes.new('ShaderNodeTexImage')
        image = bpy.data.images.load(str(OUT/('T_TavernEatingWood_'+suffix+'.png')))
        image.filepath = '//'+image.name
        tex.image = image
        if suffix != 'Color':
            image.colorspace_settings.name = 'Non-Color'
        output = tex.outputs['Color']
        if suffix == 'Normal':
            flip = tree.nodes.new('ShaderNodeVectorMath')
            flip.operation = 'MULTIPLY_ADD'
            flip.inputs[1].default_value = (1,-1,1)
            flip.inputs[2].default_value = (0,1,0)
            tree.links.new(output,flip.inputs[0])
            normal = tree.nodes.new('ShaderNodeNormalMap')
            tree.links.new(flip.outputs[0],normal.inputs['Color'])
            output = normal.outputs[0]
        tree.links.new(output,shader.inputs[socket])
    return mat


class Carving:
    def __init__(self):
        self.vertices, self.faces, self.uv = [], [], []

    def tube(self, rings, uv):
        rows, sides = len(rings), len(rings[0])
        first = len(self.vertices)
        for ring in rings:
            self.vertices.extend(ring)
        def idx(row, side):
            return first + row*sides + (side%sides)
        for i in range(rows-1):
            for j in range(sides):
                corners = [(i,j),(i,j+1),(i+1,j+1),(i+1,j)]
                self.faces.append([idx(a,b) for a,b in corners])
                self.uv.append([uv(a,b,j) for a,b in corners])
        for row in (0, rows-1):
            order = list(range(sides))
            if row == 0:
                order.reverse()
            self.faces.append([idx(row,k) for k in order])
            cy = sum(v[1] for v in rings[row])/sides
            cz = sum(v[2] for v in rings[row])/sides
            self.uv.append([(.50+(rings[row][k][1]-cy)/2.4,
                             .0215+.043*(rings[row][k][2]-cz)/.8) for k in order])

    def mesh(self, name, material):
        # The support contacts and plan-view centre define the placement pivot.
        low = [min(v[axis] for v in self.vertices) for axis in range(3)]
        high = [max(v[axis] for v in self.vertices) for axis in range(3)]
        pivot = ((low[0]+high[0])/2,(low[1]+high[1])/2,low[2])
        points = [tuple((p[i]-pivot[i])/100 for i in range(3)) for p in self.vertices]
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(points, [], self.faces)
        mesh.update()
        layer = mesh.uv_layers.new(name='EatingWoodUV')
        for polygon, coords in zip(mesh.polygons,self.uv):
            polygon.use_smooth = len(coords)==4
            for loop, uv in zip(polygon.loop_indices,coords):
                layer.data[loop].uv = uv
        mesh.materials.append(material)
        obj = bpy.data.objects.new(name,mesh)
        bpy.context.collection.objects.link(obj)
        obj.modifiers.new('Cut faces into triangles','TRIANGULATE')
        dimensions = tuple(round(b-a,3) for a,b in zip(low,high))
        return obj, dimensions


def sample_shape(table, x):
    """Shape-preserving cubic interpolation for the silhouette and the hollow."""
    xs = [p[0] for p in table]
    i = min(len(xs)-2, max(0,bisect_right(xs,x)-1))
    dist = xs[i+1]-xs[i]
    t = (x-xs[i])/dist
    def slope(k,n):
        a,b = max(0,k-1),min(k+1,len(xs)-1)
        left = (table[k][n]-table[a][n])/(xs[k]-xs[a]) if a<k else None
        right = (table[b][n]-table[k][n])/(xs[b]-xs[k]) if k<b else None
        if left is None: return right
        if right is None: return left
        if left*right<=0: return 0.
        return 2*left*right/(left+right)
    return [(1+2*t)*(1-t)**2 * table[i][n] + t*(1-t)**2*dist*slope(i,n)
            + t*t*(3-2*t)*table[i+1][n] - t*t*(1-t)*dist*slope(i+1,n)
            for n in range(1,len(table[0]))]


def sections(stations, stride):
    result = []
    for a,b in zip(stations,stations[1:]):
        count = max(1,round((b-a)/stride))
        result.extend(a+(b-a)*i/count for i in range(count))
    return result+[stations[-1]]


def chopsticks(lod):
    carving = Carving()
    sides = (32,16,8)[lod]
    # x, grip radius, flat-sided fraction. Two shallow incisions below the butt.
    profile = [
        (0,.23,.99),(.04,.295,.99),(.12,.337,.99),(.29,.344,.99),
        (1.04,.345,.99),(1.09,.331,.99),(1.15,.301,.99),(1.21,.331,.99),(1.26,.345,.99),
        (1.53,.345,.99),(1.58,.328,.99),(1.64,.303,.99),(1.70,.331,.99),(1.76,.345,.99),
        (3.3,.343,.95),(6.5,.329,.84),(10,.294,.73),(13.9,.249,.47),
        (17.5,.203,.15),(20.6,.167,0.),(22.22,.151,0.),(22.71,.144,0.),
        (22.83,.127,0.),(22.90,.086,0.),(22.93,.042,0.)]
    stations = [p[0] for p in profile]
    if lod==2:
        stations = [0,.12,.29,3.3,6.5,10,13.9,17.5,20.6,22.71,22.90,22.93]
    for stick in range(2):
        rows = sections(stations,(1.,1.8,3.2)[lod])
        rings, radii = [], []
        for x in rows:
            r, flat = sample_shape(profile,x)
            t = x/profile[-1][0]
            roll = (-.075,.277)[stick] + .048*sin(2*t+stick)
            centre_y = (-1 if stick==0 else 1)*(1.23-.75*t) + .064*sin(4*t+stick)
            ring=[]
            for j in range(sides):
                a = tau*j/sides
                c, s = cos(a),sin(a)
                octagon = min(1/max(abs(s),abs(c)),1.58/(abs(c)+abs(s)))
                # Facets become almost circular in the final quarter. Hand planing
                # leaves subtle variation between opposite sides and between sticks.
                grain = 1+.013*sin(3*a+1.8*t+stick)+.007*cos(5*a-2*t)
                radius = r*(1+flat*(octagon-1))*grain
                y, z = radius*c, radius*s*(.965+.019*stick)
                ring.append((x-11.465+(.14 if stick else -.14),centre_y+y*cos(roll)-z*sin(roll),
                             y*sin(roll)+z*cos(roll)))
            rings.append(ring)
            radii.append(-min(v[2] for v in ring))
        # Rest each rigid stick on its lowest support line. Both sides of the
        # balance point carry the weight even though the grip and tips differ.
        balance = 8.7
        lo,hi = -.08,.08
        for _ in range(36):
            tilt = (lo+hi)/2
            left = max(r-tilt*(x-balance) for x,r in zip(rows,radii) if x<=balance)
            right = max(r-tilt*(x-balance) for x,r in zip(rows,radii) if x>=balance)
            if right>left: lo = tilt
            else: hi = tilt
        lift = max(r-tilt*(x-balance) for x,r in zip(rows,radii))
        rings=[[(x,y,z+lift+tilt*(xx-balance)) for x,y,z in ring] for ring,xx in zip(rings,rows)]
        band = (.043,.219)[stick]
        def uv(row, col, face_col):
            return (.035+.93*rows[row]/22.93, band + .176*(.05+.90*col/sides))
        carving.tube(rings,uv)
    return carving


# Grain runs continuously through the spatulate grip, raised crank, shoulder,
# asymmetric lip and hollow. Section columns are half-width, edge Z, inside Z,
# and outside Z. The back of the bowl and the grip heel both touch the table.
SPOON = [
    (-8.85,.045,.19,.209,.16),(-8.79,.35,.192,.285,.085),(-8.58,.63,.207,.384,.026),
    (-8.15,.735,.218,.421,.006),(-7.55,.76,.220,.432,0.),(-6.7,.712,.238,.448,.014),
    (-5.25,.603,.32,.519,.102),(-3.4,.489,.458,.65,.241),(-1.65,.403,.654,.859,.412),
    (-.30,.367,.878,1.108,.553),(.65,.39,1.076,1.29,.603),(1.40,.508,1.214,1.354,.585),
    (2.02,.779,1.293,1.31,.472),(2.60,1.19,1.323,1.128,.348),
    (3.40,1.646,1.35,.834,.191),(4.40,2.025,1.352,.508,.06),
    (5.36,2.165,1.329,.311,.004),(5.90,2.171,1.325,.285,0.),
    (6.55,2.097,1.333,.325,.027),(7.20,1.888,1.35,.452,.123),
    (7.82,1.556,1.392,.68,.335),(8.27,1.16,1.438,.959,.617),
    (8.59,.76,1.473,1.203,.917),(8.77,.40,1.489,1.388,1.179),
    (8.84,.16,1.50,1.469,1.36),(8.85,.051,1.50,1.495,1.455)]


def spoon(lod):
    sides = (40,24,12)[lod]
    stations = [p[0] for p in SPOON]
    if lod==2:
        stations = [stations[i] for i in (0,2,4,6,8,10,11,12,14,16,17,19,21,23,25)]
    rows = sections(stations,(.31,.68,1.1)[lod])
    rings=[]
    for x in rows:
        width, edge, top, bottom = sample_shape(SPOON,x)
        basin = max(0., min(1.,(x-1.7)/1.7))
        cy = .082*sin(.7*x)+.05*sin(.38*x+.6)
        ring = []
        for j in range(sides):
            a = tau*j/sides
            c,s = cos(a),sin(a)
            y = cy + width*c*(1+.039*c*basin+.009*sin(1.5*x+.8*a))
            skew = .054*basin*c*(.58+.42*cos(.84*x))
            if j <= sides//2:
                # Draw a softly round lip, turning down to a distinctly concave
                # floor. The handle side of the same continuous surface is crowned.
                if top >= edge:
                    z = edge+(top-edge)*max(0,s)**.82
                else:
                    lip = .115*basin
                    z = edge+lip*max(0,s)-(edge+lip-top)*s*s
            else:
                # A thumb-width area at the lowest station is flattened by wear.
                flat = .11 if x>2 else .17
                q = max(0.,(abs(c)-flat)/(1-flat))
                z = edge-(edge-bottom)*max(0.,1-q*q)**.86
            z += skew * c*c
            ring.append((x,y,z))
        rings.append(ring)
    carving = Carving()
    def uv(row,col,face_col):
        lo,hi = (.395,.7) if face_col < sides//2 else (.7,1.)
        x,y,_ = rings[row][col%sides]
        return (.045+.91*(x+8.85)/17.7, .5*(hi+lo)+(hi-lo)*y/5.45)
    carving.tube(rings,uv)
    return carving


material=wood_material()
for make,name in [(chopsticks,'SM_TavernChopsticks'),(spoon,'SM_TavernWoodSpoon')]:
    root = bpy.data.objects.new(name+'_LODs', None)
    root['fbx_type'] = 'LodGroup'
    bpy.context.collection.objects.link(root)
    for level in range(3):
        obj, dimensions = make(level).mesh(name+'_LOD'+str(level),material)
        obj.parent = root
        if level==0:
            print(name,'cm (X,Y,Z)',dimensions,flush=True)
    bpy.ops.object.select_all(action='DESELECT')
    for item in [root,*root.children]:
        item.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'EMPTY','MESH'},
        axis_forward='Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,
        use_custom_props=True,add_leaf_bones=False,path_mode='STRIP')
    for item in root.children:
        if not item.name.endswith('LOD0'):
            item.hide_set(True)
            item.hide_render = True
    if make is spoon:
        root.location.y = .07
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TavernEatingUtensils.blend'),relative_remap=False)
