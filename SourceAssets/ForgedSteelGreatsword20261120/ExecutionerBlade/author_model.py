"""Build the game blade on the fitted hilt and transfer the original forged-steel atlas."""
from pathlib import Path
import json
import math
import bpy

here = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(here.parent / 'Integration/ForgedSteelGreatsword_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version = 0
stock = bpy.data.objects['SM_ForgedSteelGreatsword_Blade_V1']
source = stock.data
points = [v.co.copy() for v in source.vertices]
z0, z1 = min(v.z for v in points), max(v.z for v in points)
span = z1 - z0

def source_section(z):
    crossings = []
    for edge in source.edges:
        a,b = (points[i] for i in edge.vertices)
        if (a.z < z) != (b.z < z):
            crossings.append(a.lerp(b, (z-a.z)/(b.z-a.z)))
    lo,hi = min(p.x for p in crossings),max(p.x for p in crossings)
    return (lo+hi)/2,(hi-lo)/2,(min(p.y for p in crossings)+max(p.y for p in crossings))/2

def smooth_ramp(value):
    value = max(0., min(1., value))
    return value * value * (3. - 2. * value)


# The blade seats behind the centre shield and follows the rise of the guard wings.
seat_z = z0 + .000002
mount_x, _, mount_y = source_section(seat_z)
blade_span = span * 1.22
seat_bottom_z = -.0145
seat_top_z = z0 + .115
seat_first_t = (seat_bottom_z - z0) / blade_span


# The long recessed fuller closes before the two continuous bevels meet at the point.
half_xs = [0, .040, .080, .127, .163, .202, .235, .263, .285, .302, .32,
           .36, .47, .55, .62, .73, .82, .86, .92, .955, .975, .990, .997, 1]
xs = [-s for s in reversed(half_xs[1:])] + half_xs
levels = sorted(set([i/64 for i in range(64)] +
                    [seat_first_t*i/6 for i in range(1,7)] + [.003, .009, .019, .039, .056, .086,
                     .105, .118, .77, .785, .801, .815, .830, .84, .855, .875, .915, .97]))
verts,params,faces,surfaces = [],[],[],[]
def profile(s,t,side):
    blend = smooth_ramp((z0 + t*blade_span - seat_bottom_z) / (seat_top_z - seat_bottom_z))
    along_blade = (t-seat_first_t)/(1.-seat_first_t)
    radius = .065 - .0235*along_blade
    tip_t = max(0., (t-.84)/.16)
    # Ease into the converging edges and keep the final facets straight.
    taper = 1.-(tip_t*tip_t/.48 if tip_t<.24 else tip_t-.12)/.88
    radius *= taper
    a = abs(s)
    z = z0+blade_span*t
    z += .0084*a*a*(1.-smooth_ramp((t-seat_first_t)/(.05-seat_first_t)))
    thick = span*(.0054-.0012*t)
    face = min(1., (.09+.91*min(1.,(1.-a)/.16)))
    # Below the cap the sides of the recess converge into a rounded termination.
    end = min(1.,max(0.,(.830-t)/.06))
    opening = .23*math.sqrt(end*(2.-end))
    hollow = min(1.,max(0.,(opening-a)/.075))
    hollow *= hollow*(3.-2.*hollow)
    d = thick*(face-.59*hollow*min(1.,end*5))
    d = (d + (thick*(1.-.92*a)-d)*smooth_ramp((t-.815)/.10))*taper
    # Carry the bevels and the central recess through the old module split.
    # The wider shoulders sit down into the thinner metal of the wings.
    # At the centre there is enough relief to cover the fitted guard's hidden cap.
    seat_depth = .0043 + .0105*(1.-smooth_ramp((a-.13)/.33))
    seat_depth -= .0023*(1.-smooth_ramp(a/.14))
    seat_depth *= 1.-.86*smooth_ramp((a-.84)/.16)
    depth = seat_depth + (d-seat_depth)*blend
    return mount_x+radius*s,mount_y+side*depth,z

def panel(idx, side, surface):
    faces.append(idx)
    surfaces.append((side, surface))

rows = {}
for side in (-1,1):
    grid = []
    for t in levels:
        row = []
        for s in xs:
            row.append(len(verts))
            verts.append(profile(s,t,side))
            params.append((s,t))
        grid.append(row)
    rows[side] = grid
    for bottom,top in zip(grid,grid[1:]):
        for i in range(len(xs)-1):
            quad = (bottom[i],bottom[i+1],top[i+1],top[i])
            panel(quad if side<0 else quad[::-1],side,'blade')
front,back = rows[-1],rows[1]
for j in range(len(levels)-1):
    panel((front[j][0],front[j+1][0],back[j+1][0],back[j][0]),-1,'edge')
    panel((front[j][-1],back[j][-1],back[j+1][-1],front[j+1][-1]),1,'edge')
for i in range(len(xs)-1):
    panel((front[0][i],back[0][i],back[0][i+1],front[0][i+1]),-1,'cap')

# A single vertex at the point avoids a flat cap and coincident triangles.
point = len(verts)
verts.append((mount_x, mount_y, z0+blade_span))
params.append((0., 1.))
for side, row in ((-1,front[-1]),(1,back[-1])):
    for left,right in zip(row,row[1:]):
        panel((left,right,point) if side<0 else (right,left,point),side,'blade')
panel((front[-1][0],point,back[-1][0]),-1,'edge')
panel((front[-1][-1],back[-1][-1],point),1,'edge')

name = 'SM_ForgedSteelGreatsword_ExecutionerBlade'
mesh = bpy.data.meshes.new(name)
mesh.from_pydata(verts,[],faces)
mesh.materials.append(source.materials[0])
mesh.update()
uv = mesh.uv_layers.new(name='UVMap').data
# Use the interior of a single, neutral factory steel island. Atlas pixel X
# runs along this island's grinding direction; Y runs across the blade.
def texel_stops(parameters, start, end, step):
    # Closely spaced rings and bevel loops still need distinct, representable
    # UVs after the default mesh import packs UV0 into 16-bit floats.
    first, last = parameters[0], parameters[-1]
    stops = {}
    previous = start - step
    for i, value in enumerate(parameters):
        ideal = start + round((end - start) * (value - first) / ((last - first) * step)) * step
        upper = end - (len(parameters) - 1 - i) * step
        previous = min(upper, max(previous + step, ideal))
        stops[value] = previous
    return stops


# Put the only turn in the grain at an existing mid-blade ring. Both sides
# of it evaluate to exactly the same texel. The guard junction has no turn.
lower = [t for t in levels if t <= .5]
upper = [-t for t in reversed(levels + [1.]) if t >= .5]
length_px = texel_stops(lower, 1848, 2080, 2)
length_px.update({-t: x for t, x in texel_stops(upper, 1848, 2080, 2).items()})
width_px = texel_stops(xs, 2222, 2274, 1)
back_indices = {i for row in back for i in row}

for face, (side, surface) in zip(mesh.polygons, surfaces):
    face.use_smooth = surface == 'blade'
    for loop_index in face.loop_indices:
        index = mesh.loops[loop_index].vertex_index
        s, t = params[index]
        x, y = length_px[t], width_px[s]
        on_back = index in back_indices
        if surface == 'cap':
            x = 1852 if on_back else 1848
        elif surface == 'edge':
            # Preserve the edge's local tone at both sides of the strip.
            if index == point:
                y = width_px[float(side)] - side
            y += (2 if s < 0. else -2) if on_back else 0
        uv[loop_index].uv = (x / 4096., 1. - y / 4096.)

blade = bpy.data.objects.new(name,mesh)
bpy.context.scene.collection.objects.link(blade)
blade.matrix_world = stock.matrix_world.copy()
for obj in list(bpy.context.scene.objects):
    if obj != blade:
        bpy.data.objects.remove(obj,do_unlink=True)
blade.select_set(True)
bpy.context.view_layer.objects.active = blade
bpy.ops.wm.save_as_mainfile(filepath=str(here/'ExecutionerBlade.blend'))
bpy.ops.export_scene.fbx(filepath=str(here/(name+'.fbx')),use_selection=True,object_types={'MESH'},
                         axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,
                         mesh_smooth_type='FACE',use_tspace=True,use_triangles=True)

# The exact point drives the existing visual-tip and rune placement data.
tip = mesh.vertices[point].co
tip_cm = [round(tip.x*100, 5), round(-tip.y*100, 5), round(tip.z*100, 5)]
(here/'exports.json').write_text(json.dumps({'visual_tip_cm': tip_cm}, indent=2)+'\n', encoding='utf-8')
