"""Shape the Fab torch around the existing staff contact and build the closed flame proxy."""
import json
import math
import os
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

root = Path(os.environ["FPS_PROJECT_ROOT"])
family = root / "SourceAssets/WoodenTorch20261122"
source = family / "HearthWrapR7"
out = source / "Export"
profile = json.loads((root / "SourceAssets/ApprenticeStaff20260927/ArmSupportV13/grip-surfaces.json").read_text())
radii = profile["variants"]["false"]["radii"]
tau = math.tau
bpy.ops.wm.open_mainfile(filepath=str(family / "StaffGripR6/HandheldTorch_StaffGrip.blend"))
torch = next(o for o in bpy.context.scene.objects if o.type == "MESH")
mesh = torch.data
layers = {m.name:i for i,m in enumerate(mesh.materials)}
lo, hi = 16.446, 32.119
head_base, head_height = 22.7, 14.0

def smooth(a,b,x):
    t = min(1.,max(0.,(x-a)/(b-a)))
    return t*t*(3.-2.*t)

def staff_radius(z,a):
    iz = min(len(radii)-1.001, max(0.,(32.+z-profile["z"][0])/(profile["z"][1]-profile["z"][0])))
    ia = a % tau / tau * profile["angle_count"]
    k, j = int(iz), int(ia)
    n = (j+1)%profile["angle_count"]
    v,w = iz-k, ia-j
    return (1-v)*((1-w)*radii[k][j]+w*radii[k][n])+v*((1-w)*radii[k+1][j]+w*radii[k+1][n])

bm = bmesh.new()
bm.from_mesh(mesh)
for level in (-14.,-9.,-6.8,-5.9,5.9,6.8,8.8,11.,13.5,16.,18.,21.,24.,27.,30.):
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                           plane_co=(0,0,level/100.),plane_no=(0,0,1),dist=1e-7)
bm.to_mesh(mesh)
bm.free()
wood = {v for p in mesh.polygons if p.material_index == layers["Wood"] for v in p.vertices}
for v in mesh.vertices:
    x,y,z = v.co*100.
    a = math.atan2(y,x)
    r = math.hypot(x,y)
    t = (z-lo)/(hi-lo)
    if v.index in wood:
        # Recess the core under the leather; taper gradually into a longer carved neck.
        if r > .8:
            target = (2.77 - .74*smooth(6.,12.,z) + .58*smooth(12.,18.,z)
                      - .74*smooth(-6.,-17.65,z))
            irregular = .045*math.sin(3*a+.12*z)+.035*math.sin(5*a-.18*z)
            fade = smooth(-9.,-5.5,z)*(1.-smooth(5.5,8.,z))
            target -= .23*fade
            x,y = (target+irregular)*math.cos(a),(target+irregular)*math.sin(a)
        if z <= -6.: z = -6.+(z+6.)*.84
        elif z >= lo: z = head_base+t*head_height
        else: z += (head_base-lo)*smooth(6.6,lo,z)
    else:
        swell = 1.14+.28*math.sin(math.pi*max(0.,min(1.,t)))+.035*math.sin(a*3.+t*3.)
        x,y = x*swell+.22*t*t, y*swell-.13*t
        z = head_base+t*head_height+.18*math.sin(3*a+.4)*smooth(.55,1.,t)
    v.co = Vector((x,y,z))*.01
mesh.update()

# Keep the donor's wood grain and cloth UVs. Tint by physical height in the private materials.
def tint(part,z,a):
    if part == "Wood":
        char=smooth(head_base-5.,head_base+2.,z)
        return tuple(v*(1.-char)+b*char for v,b in zip((.88,.77,.64),(.16,.10,.075)))
    burn = smooth(head_base+2.,head_base+head_height-.5,z+.7*math.sin(a*3.))
    base,top = ((.69,.49,.31),(.16,.095,.068)) if part=="Cloth" else ((.53,.38,.24),(.21,.14,.09))
    return tuple(v*(1.-burn)+b*burn for v,b in zip(base,top))
def paint(data, shades):
    c=data.color_attributes.new(name="FuelTint",type="BYTE_COLOR",domain="CORNER")
    for p in data.polygons:
        for j in p.loop_indices: c.data[j].color=(*shades(p,j),1.)
    data.color_attributes.active_color=c
def old_color(poly,loop):
    p=mesh.vertices[mesh.loops[loop].vertex_index].co*100.
    return tint(mesh.materials[poly.material_index].name,p.z,math.atan2(p.y,p.x))
paint(mesh,old_color)

def surface(name, verts, faces, uvs, color, mat):
    m=bpy.data.meshes.new(name)
    m.from_pydata([tuple(v*.01 for v in p) for p in verts],[],faces)
    m.materials.append(mat)
    m.update()
    uv=m.uv_layers.new(name="UVMap")
    for p in m.polygons:
        p.use_smooth=True
        for l,coord in zip(p.loop_indices,uvs[p.index]): uv.data[l].uv=coord
    paint(m,lambda p,j:color[m.loops[j].vertex_index])
    o=bpy.data.objects.new(name,m)
    bpy.context.collection.objects.link(o)
    return o

# A low-relief leather wrap follows the measured staff shaft. The creases go inward.
leather=bpy.data.materials.new("Leather");leather.use_nodes=True
nodes=leather.node_tree.nodes;links=leather.node_tree.links
bs=next(n for n in nodes if n.type=="BSDF_PRINCIPLED");bs.inputs["Roughness"].default_value=.74
texdir=root/"SourceAssets/CommonHammerGrips20261014/BuildV1/Textures"
tx=nodes.new("ShaderNodeTexImage");tx.image=bpy.data.images.load(str(texdir/"T_HammerGrip_Leather_BaseColor.png"))
tx.image.pack();links.new(tx.outputs["Color"],bs.inputs["Base Color"])
verts=[];faces=[];uvs=[];colors=[]
around,turns=48,4
courses=[(t,v) for t in range(turns) for v in (0.,.055,.15,.45,.84,.955)]+[(turns,0.)]
for i,(turn,v) in enumerate(courses):
    for j in range(around):
        a=tau*j/around
        h=(turn+v)/turns
        z=-6.60+13.20*h
        groove=(h*turns-j/around+.06*math.sin(a*2.))%1.
        seam=math.exp(-(min(groove,1.-groove)/.11)**2)
        ends=smooth(0.,.07,h)*smooth(1.,.93,h)
        rad=staff_radius(z,a)-.048*seam-.23*(1.-ends)
        verts.append((rad*math.cos(a),rad*math.sin(a),z))
        colors.append(tuple(k*(1.-.29*seam) for k in (.88,.76,.64)))
        if i:
            k=(j+1)%around;faces.append(((i-1)*around+j,(i-1)*around+k,i*around+k,i*around+j))
            y0=(courses[i-1][0]+courses[i-1][1])/turns
            uvs.append(((j/around,y0),((j+1)/around,y0),((j+1)/around,h),(j/around,h)))
sleeve=surface("PalmWrap",verts,faces,uvs,colors,leather)

# Project a bevelled loose edge onto the actual asymmetric cloth, using its own UV chart.
mesh.calc_loop_triangles()
tris=[tri for tri in mesh.loop_triangles if tri.material_index==layers["Cloth"]]
coords=[v.co*100 for v in mesh.vertices]
tree=BVHTree.FromPolygons(coords,[list(t.vertices) for t in tris],all_triangles=True)
uvlayer=mesh.uv_layers.active.data
def cloth_point(a,z):
    d=Vector((math.cos(a),math.sin(a),0))
    p,n,idx,_=tree.ray_cast(Vector((0,0,z))+d*11,-d,12)
    if p is None: raise ValueError("Missing fabric under seam")
    t=tris[idx]; v=[coords[k] for k in t.vertices]
    uv=geometry.barycentric_transform(p,*v,*[uvlayer[k].uv.to_3d() for k in t.loops])
    return p,d,uv.xy
verts=[];faces=[];uvs=[];colors=[];mapped=[]
for i in range(133):
    u=i/132.
    a=.32+tau*2.16*u
    z=head_base+1.0+u*(head_height-2.6)+.23*math.sin(3*a+.5*u)
    end=smooth(0,.045,u)*smooth(1.,.955,u)
    for j,(dz,relief,shade) in enumerate(((-.25,-.025,.55),(-.14,.12,.70),(.015,.21,.88),(.23,.10,1.),(.52,-.04,1.))):
        p,d,uv=cloth_point(a,z+dz)
        p+=d*(relief*end-.025*(1.-end))
        verts.append(tuple(p));mapped.append(tuple(uv));colors.append(tuple(c*shade for c in tint("Cloth",p.z,a)))
        if i and j:
            f=((i-1)*5+j-1,i*5+j-1,i*5+j,(i-1)*5+j)
            faces.append(f)
            # Do not interpolate across separate atlas islands at the seam.
            uu=[mapped[n] for n in f]
            if max(math.dist(uu[0],p) for p in uu)>.18:
                x,y=uu[0];uu=[(x,y),(x+.002,y),(x+.002,y+.002),(x,y+.002)]
            uvs.append(uu)
hem=surface("OverlappingLinen",verts,faces,uvs,colors,mesh.materials[layers["Cloth"]])
contours=[]
for offset in (.8,3,6,9,12,13.4):
    rr=[cloth_point(i*tau/32,head_base+offset)[0].xy.length for i in range(32)]
    contours.append([offset,round(min(rr),3),round(max(rr),3)])

bpy.ops.object.select_all(action="DESELECT")
for o in (torch,sleeve,hem):o.select_set(True)
bpy.context.view_layer.objects.active=torch
bpy.ops.object.join()
torch.name=torch.data.name="SM_WrappedHearthTorch"
bpy.context.preferences.filepaths.save_version=0
# Match the packed editable material colors to the imported vertex tint.
for mat in torch.data.materials:
    bs=next(n for n in mat.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
    old=bs.inputs["Base Color"].links[0].from_socket
    mix=mat.node_tree.nodes.new("ShaderNodeMixRGB");mix.blend_type="MULTIPLY";mix.inputs[0].default_value=1
    vc=mat.node_tree.nodes.new("ShaderNodeVertexColor");vc.layer_name="FuelTint"
    mat.node_tree.links.new(old,mix.inputs[1]);mat.node_tree.links.new(vc.outputs["Color"],mix.inputs[2])
    mat.node_tree.links.new(mix.outputs[0],bs.inputs["Base Color"])
def export(obj):
    bpy.ops.object.select_all(action="DESELECT");obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(out/(obj.name+".fbx")),use_selection=True,object_types={"MESH"},
                            apply_unit_scale=True,bake_anim=False,axis_forward="-Y",axis_up="Z",mesh_smooth_type="FACE",
                            use_triangles=True,path_mode="STRIP",colors_type="SRGB")
export(torch)
# The flame is sampled along each camera ray up to solid scene depth. Only the exit face is drawn.
bpy.ops.mesh.primitive_cube_add(size=1)
proxy=bpy.context.object
proxy.name=proxy.data.name="SM_HearthFlameVolume"
for v in proxy.data.vertices:v.co=Vector((v.co.x*.33,v.co.y*.33,v.co.z*.425+.1925))
proxy.data.flip_normals()
export(proxy)
proxy.hide_render=True;proxy.hide_set(True)
torch.select_set(True);bpy.context.view_layer.objects.active=torch
bpy.ops.wm.save_as_mainfile(filepath=str(source/"WrappedHearthTorch.blend"))
zs=[v.co.z*100 for v in torch.data.vertices]
fit={"length_cm":max(zs)-min(zs),"grip_cm":[0,0,0],"flame_cm":[0,0,head_base-.4],"head_height_cm":head_height,
     "grip_diameter_cm":round(2*staff_radius(0,0),2),"head_contour_cm":contours}
(out/"fit.json").write_text(json.dumps(fit,indent=2),encoding="utf8")
print("TORCH_AUTHORED",fit)
