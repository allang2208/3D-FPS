"""Build the two surveyed limestone exposures and the working-yard assemblies. Distances are metres."""
from pathlib import Path
import math
import os
import random
import re
import bpy
import bmesh
from mathutils import Vector, noise
from mathutils.bvhtree import BVHTree

root=Path(__file__).resolve().parents[3]
out=root/"SourceAssets/HillsQuarryCutYard/Approach"
out.mkdir(parents=True,exist_ok=True)
stations=[tuple(float(n)/100 for n in row.split(",")) for row in re.findall(
    r"\{([\s\d,.-]+)\}",(root/"Source/FPSGAME/WorldGeneration/TemperateQuarryBanks.inl").read_text())]
rng=random.Random(9017)
bpy.ops.wm.read_factory_settings(use_empty=True)
slots={s:bpy.data.materials.new(s) for s in ("Bedded","Tooled","Riven","Oak","Iron","Rope","Blank")}
def ease(a,b,x):
    f=min(1,max(0,(x-a)/(b-a)))
    return f*f*(3-2*f)
def section(y):
    i=next((j for j in range(1,len(stations)-1) if y<=stations[j][0]),len(stations)-1)
    a,b=stations[i-1:i+1]; t=ease(a[0],b[0],y)
    return [v+(w-v)*t for v,w in zip(a,b)]
def field(y,z,key):
    return noise.noise(Vector((y,z,key)),noise_basis='PERLIN_ORIGINAL')

def save_obj(obj,name):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(out/(name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False)
    bpy.data.objects.remove(obj,do_unlink=True)

# Surveyed release pockets. The same rows place the parent and grade the fan in UE.
def rockfalls():
    path=root/"Source/FPSGAME/WorldGeneration/TemperateQuarryRockfalls.inl"
    out=[]
    for line in path.read_text().splitlines():
        if not line.startswith("QUARRY_FALL("):continue
        v=line[len("QUARRY_FALL("):-1].split(",")
        index=int(v[0]); cy=float(v[3])/100.
        bottom,top,width,recess=(float(t)/100 for t in v[15:19])
        # A different set of intersecting planes releases each piece. The points
        # are in wall elevation; their outline is retained by the two hero blocks.
        r=random.Random(1187+index)
        profile=[(-1.,-.38),(-.63,-.94),(.26,-1.),(.91,-.58),(1.,.31),(.38,1.),(-.44,.87),(-.94,.41)]
        profile=[((u+r.uniform(-.09,.09))*width,(z+r.uniform(-.10,.10))*(top-bottom)*.5) for u,z in profile]
        planes=[]
        for (u,z),(v2,z2) in zip(profile,profile[1:]+profile[:1]):
            a,b=-(z2-z),v2-u;length=math.hypot(a,b)
            planes.append((a/length,b/length,-(a*u+b*z)/length))
        out.append(dict(id=index,kind=v[1],west=float(v[2])<0,cy=cy,mid=.5*(bottom+top),
                        width=width,depth=recess,rake=float(v[19]),profile=profile,planes=planes))
    return out

falls=rockfalls()

# Soil survives in pockets behind the lip. Leave the worked bay and the fresh
# upper slip open, and put the taller growth inland of the dry fringe.
# wall, chainage, half-length, depth of soil, mature hazels, fringe clumps
rim_pockets=(
    ('west',-20.4,3.6,2.8,3,14),('west',-11.5,4.1,3.9,4,20),
    ('west',3.2,2.5,2.5,1,12),('west',12.2,3.7,3.4,3,19),
    ('west',30.1,4.8,3.0,3,20),('west',39.0,2.7,2.3,1,11),
    ('east',-19.9,4.6,3.7,3,21),('east',-6.9,2.8,2.2,1,13),
    ('east',9.8,4.9,3.8,3,23),('east',29.6,3.2,2.5,2,16))
rim_rows=[]
rim_only=os.environ.get('QUARRY_RIM_ONLY')=='1'

def survey_rim(name,mesh):
    west=name=='SM_QuarryWestWorkingFace'
    side='west' if west else 'east'
    direction=-1 if west else 1
    tree=BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],
                               [p.vertices[:] for p in mesh.polygons],all_triangles=True)
    def support(x,y):
        point,normal,_,_=tree.ray_cast((x,-y,60.),(0,0,-1),100.)
        return point.z if point is not None and normal.z>.69 else None
    for index,(wall,center,half_length,soil,shrubs,tufts) in enumerate(rim_pockets):
        if wall!=side:continue
        r=random.Random(42113+index)
        for i in range(shrubs+tufts):
            woody=i<shrubs
            u=r.uniform(-.78,.78) if woody else r.uniform(-1.,1.)
            y=center+u*half_length
            _,w,e,wh,eh,_,floor=section(y)
            toe,lift=(w,wh) if west else (e,eh)
            lip=None
            for step in range(42):
                d=-2.+.22*step
                z=support(toe+direction*d,y)
                if z is not None and z>floor+.84*lift:
                    lip=d
                    break
            if lip is None:continue
            width=soil*math.sqrt(max(.05,1-u*u))
            setback=r.uniform(.53,1.)*width+.55 if woody else r.uniform(.03,.64)*width
            x=toe+direction*(lip+setback)
            z=support(x,y)
            if z is None:continue
            kind=r.choice(('HazelA','HazelC')) if woody else r.choice(('Turf','Turf','DryStem'))
            span=(r.uniform(1.8,3.5) if i==0 else r.uniform(.65,1.85)) if woody else r.uniform(.48,1.12)
            rim_rows.append(f'    {{{kind},{x*100:.1f},{y*100:.1f},{z*100:.1f},{r.uniform(-180,180):.1f},{span*100:.1f}}},')


def fractured_surface(name,verts,faces,material_ids,colors,smooth):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces);mesh.update()
    for key in ('Bedded','Tooled','Riven'):mesh.materials.append(slots[key])
    color=mesh.color_attributes.new(name='RockWeather',type='BYTE_COLOR',domain='POINT')
    for item,value in zip(color.data,colors):item.color=value
    uv=mesh.uv_layers.new(name='SurfaceMetres')
    for p,slot in zip(mesh.polygons,material_ids):
        p.material_index=slot
        n=p.normal
        # Preserve metre scale on backward-facing fracture cheeks and sloping caps too.
        mode=max(range(3),key=lambda i:abs(n[i]))
        for loop in p.loop_indices:
            x,y,z=mesh.vertices[mesh.loops[loop].vertex_index].co
            uv.data[loop].uv=((-.46*y,.46*z),(.46*x,.46*z),(.46*x,-.46*y))[mode]
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update()
    for f in bm.faces:f.smooth=smooth
    for e in bm.edges:
        e.smooth=e.is_manifold and e.calc_face_angle()<math.radians(27) and e.link_faces[0].material_index==e.link_faces[1].material_index
    bm.to_mesh(mesh);bm.free()
    if smooth:survey_rim(name,mesh)
    if rim_only:
        bpy.data.meshes.remove(mesh)
        return
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    save_obj(obj,name)


def facet(u,v):
    # Linear interpolation over rock facets. Broad planes meet at real arrises.
    i,j=math.floor(u),math.floor(v)
    a,b=u-i,v-j
    def corner(x,y):
        k=(x*73856093 ^ y*19349663)&0xffffffff
        k=((k^(k>>16))*2246822519)&0xffffffff
        return (k&65535)/32767.5-1.
    z00,z11=corner(i,j),corner(i+1,j+1)
    if a>b:return (1-a)*z00+(a-b)*corner(i+1,j)+b*z11
    return (1-b)*z00+(b-a)*corner(i,j+1)+a*z11


def detached_block(s):
    # The socket outline becomes the outline of the fallen slab, with its rear
    # bedding face turned upward. An inset perimeter breaks the exposed arris.
    verts=[];faces=[];mats=[];cols=[]
    outline=s['profile']
    def add_ring(scale,level):
        ids=[]
        for i,(u,v) in enumerate(outline):
            ids.append(len(verts))
            z=s['depth']*level+.08*facet(u*.9,v*.7)+.07*u-.045*v
            verts.append((scale*u,-scale*v,z))
            cols.append((.75 if level<.1 else .08,.05,.13+.10*(i%3),1.))
        return ids
    base=add_ring(.82,-.20);mid=add_ring(1.,.37);cap=add_ring(.90,.93)
    for lower,upper,slot in ((base,mid,0),(mid,cap,2)):
        for i in range(len(cap)):
            j=(i+1)%len(cap);faces.append((lower[i],lower[j],upper[j],upper[i]));mats.append(slot)
    faces.append(tuple(reversed(base)));mats.append(0)
    crown=len(verts);verts.append((.19,-.13,s['depth']*1.05));cols.append((.01,0,.08,1.))
    for i in range(len(cap)):
        faces.append((cap[i],cap[(i+1)%len(cap)],crown));mats.append(2 if i not in (0,7) else 0)
    fractured_surface('SM_Quarry'+s['kind'],verts,faces,mats,cols,False)


def bank(west):
    name='SM_QuarryWestWorkingFace' if west else 'SM_QuarryEastLifts'
    lo,hi=(-26.,47.) if west else (-28.,40.)
    sign=-1 if west else 1
    verts=[];faces=[];mats=[];cols=[]
    def vertex(x,y,z,color):
        verts.append((x,-y,z));cols.append(color);return len(verts)-1
    # Horizons are measured against one geological datum in metres. Two beds are
    # traceable across the wall; thin lenses pinch out within individual bays.
    # elevation, exposure start/end, seam width/depth, local dip, ramp length
    beds=((-1.7,-27,3,.13,.13,.035,3.8),(1.3,-25,15,.12,.18,-.035,4.1),
          (2.19,-18,3,.065,.10,.042,2.4),(4.83,-30,47,.17,.28,-.016,5.0),
          (6.05,-6,26,.085,.16,.031,3.5),(8.92,-31,48,.12,.24,.017,3.3),
          (9.40,-9,5,.07,.11,-.024,2.8),(12.57,-20,36,.15,.23,-.036,4.7),
          (15.75,7,44,.11,.19,.054,3.2),(17.26,23,46,.07,.12,-.018,3.8))
    # Chainage, cross-joint rake, vertical throw, displaced face plane, declination.
    faults=((-23,.31,.65,.29,-.06),(-15.7,-.22,-1.18,-.55,.08),(-12.4,.35,.35,.23,.04),
            (-6.5,.18,1.35,.52,-.08),(.80,-.30,-.42,-.58,.09),(8.9,.41,-1.04,.38,.06),
            (15.4,-.37,1.64,-.43,-.11),(22.9,.24,-1.28,.66,.09),
            (27.5,-.12,.68,-.64,-.06),(35.9,.35,-.93,.29,.10),(41.,-.23,.51,-.24,-.04)) if west else (
            (-25,-.30,1.15,.44,.07),(-18,.20,-.60,-.33,-.06),(-13.8,.47,-1.42,.48,.09),
            (-4.,-.26,1.75,-.58,-.07),(1.4,-.39,-.41,.25,.04),(9.,.28,-.94,-.35,-.08),
            (17.8,-.23,1.49,.67,.11),(24.2,.16,-1.15,-.47,-.08),(34.8,.37,.60,.35,.07))
    rings=[];previous_roles=[]
    ny=math.ceil((hi-lo)/.145);nz=100
    for j in range(ny+1):
        y=lo+(hi-lo)*j/ny
        _,w,e,wh,eh,_,floor=section(y)
        toe,lift=(w,wh) if west else (e,eh)
        nearby=[s for s in falls if s['west']==west and abs(s['cy']-y)<s['width']+4.]
        ends=1.-ease(0,4.9,min(y-lo,hi-y))
        rim=.95*lift+.28*facet(y*.26,.42)+.18*field(y*.36,.25,8)
        # Where the upper key has fallen, the skyline also steps down.
        if west:rim-=.75*ease(20.6,22.4,y)*(1.-ease(24.,27.1,y))
        layers=[]
        for base,first,last,width,recess,dip,feather in beds:
            strength=ease(first,first+feather,y)*(1-ease(last-feather,last,y))
            if strength:
                level=base+(.094+dip)*y+.15*facet(y*.105,base*.32)
                layers.append((level,width,recess*strength))
        indices=[];roles=[]
        for k in range(nz+1):
            t=k/nz;z=-.72+(rim+.72)*t;world_z=floor+z
            throw=shift=joint=tilt=0.;joint_stain=0.
            for cy,rake,step,lean,dip in faults:
                d=y-cy-rake*(z-.49*lift)-.12*facet(z*.45,.11*cy)
                # Resolve an inclined fracture cheek across several mesh samples.
                # A hard switch in dip creates a row of saw teeth on grazing views.
                transition=ease(-.34,.34,d)
                throw+=step*transition;shift+=lean*transition
                joint+=.29*(1-ease(.05,.58,abs(d)))
                joint_stain=max(joint_stain,1-ease(.12,.69,abs(d)))
                tilt+=(dip-tilt)*transition
            depth=-.72+.72*t+.55*shift+tilt*(z-.44*lift)
            depth+=.48*facet(y*.28+z*.075,z*.32)+.16*facet(y*.69-z*.12,z*.78)+.065*field(y*1.4,z*1.6,7)
            if not west:
                # Remnants of the abandoned lift survive on only two stretches.
                terrace=max(ease(-26,-19,y)*(1-ease(-10,-5,y)),ease(6,11,y)*(1-ease(24,31,y)))
                depth+=terrace*(1.07*ease(.37,.45,t)+.86*ease(.68,.77,t))
            seam=0.
            for h,width,recess in layers:
                d=world_z-throw-h
                # The two sides expose separate bed ends at the slip surface.
                recess*=1.-.94*joint_stain
                seam+=recess*max(0.,1.-abs(d)/width)
                depth+=recess*.77*ease(-width,.06,d)*(1-ease(.24,1.23,d))
            depth+=seam+joint
            # Three faces of the excavated bay stop at different bench heights.
            heel=2.52+.91*ease(-3.1,-2.65,y)-.63*ease(3.8,4.22,y)
            brow=9.65-1.34*ease(-.3,.04,y)+.75*ease(5.2,5.7,y)
            left=-7.52+.18*z; right=9.55-.11*z
            bay=ease(left,left+.54,y)*(1-ease(right-.63,right,y))*ease(heel,heel+.30,z)*(1-ease(brow-.35,brow,z)) if west else 0.
            fresh=0.
            for s in nearby:
                v=z-s['mid'];u=y-s['cy']-s['rake']*v
                edge=min(a*u+b*v+c for a,b,c in s['planes'])
                removed=ease(-.15,.29,edge)
                if removed:
                    depth+=removed*s['depth']*(.95+.19*u/s['width']-.09*v/s['width'])
                    fresh=max(fresh,removed)
            worked=1.40+.65*ease(-2.65,-2.42,y)+.41*ease(3.85,4.19,y)+.042*facet(y*.78,z*.75)+.045*(z-5.)
            depth=(1-bay)*depth+bay*worked
            # Close the ends inside the host ridge; the toe in front of it stays put.
            depth+=10.6*ends
            moist=1-ease(.04,1.35+.38*field(y*.52,0,2),z)
            lichen=ease(.72,.99,t)*ease(-.23,.44,field(y*.33,z*.31,1))
            tool_run=ease(-4.8,-4.25,y)*(1.-ease(2.15,2.7,y))*ease(3.2,4.1,z)*(1.-ease(7.1,8.,z))
            lichen=(1.-bay)*lichen+bay*tool_run
            stain=min(1.,.57*joint_stain+.47*ease(-.1,.57,field(y*.23+z*.038,z*.07,9))+.64*seam)
            indices.append(vertex(toe+sign*depth,y,floor+z,(moist,lichen,stain*(1-.84*fresh)*(1-.8*bay),1)))
            roles.append(1 if bay>.60 else 2 if fresh>.51 else 0)
        for d in (4.7,7.,10.,15.4):
            depth=max(depth+.12,d)
            zz=floor+rim+.13*field(y*.43,depth*.55,9)-.082*max(0.,depth-6.)
            indices.append(vertex(toe+sign*depth,y,zz,(0,.64,.12,1)));roles.append(0)
        indices.append(vertex(toe+sign*(depth+.12),y,floor-1.,(1,0,0,1)));roles.append(0)
        if rings:
            prev=rings[-1]
            for k in range(len(indices)):
                kk=(k+1)%len(indices)
                faces.append((prev[k],prev[kk],indices[kk],indices[k]))
                # The same chipped outline controls the mesh and the material boundary.
                mats.append(roles[k] if k<nz and roles[k] in (roles[kk],previous_roles[k]) else 0)
        rings.append(indices);previous_roles=roles
    faces.extend([tuple(reversed(rings[0])),tuple(rings[-1])]);mats.extend((0,0))
    fractured_surface(name,verts,faces,mats,cols,True)
parts=[]
def part(obj,slot):
    obj.data.materials.append(slots[slot]);parts.append(obj);return obj
def box(pt,dims,slot,rot=0.,bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pt)
    o=bpy.context.object;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    m=o.modifiers.new('worn arris','BEVEL');m.width=bevel;m.segments=2;bpy.ops.object.modifier_apply(modifier=m.name)
    o.rotation_euler.z=rot
    return part(o,slot)
def rod(a,b,r0,r1,slot,n=14):
    a,b=Vector(a),Vector(b);d=b-a
    bpy.ops.mesh.primitive_cone_add(vertices=n,radius1=r0,radius2=r1,depth=d.length,location=(a+b)*.5)
    o=bpy.context.object;o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    return part(o,slot)
def cable(points,r,slot='Rope'):
    for a,b in zip(points,points[1:]):rod(a,b,r,r,slot,8)
def export_parts(name):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
    obj=parts[0]; transform=obj.matrix_world.copy()
    for v in obj.data.vertices:v.co=transform@v.co
    from mathutils import Matrix
    obj.matrix_world=Matrix.Identity(4);obj.data.update()
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    uv=obj.data.uv_layers.active or obj.data.uv_layers.new(name='SurfaceMetres')
    for f in obj.data.polygons:
        axis=max(range(3),key=lambda i:abs(f.normal[i]))
        for j in f.loop_indices:
            x,y,z=obj.data.vertices[obj.data.loops[j].vertex_index].co;uv.data[j].uv=((y,z),(x,z),(x,y))[axis]
    save_obj(obj,name);parts.clear()
def footing(x,y,width,turn):
    # A cropped stone shoe with a broad buried heel and a level timber bearing.
    corners=((-1,-.52),(-.60,-.98),(.43,-.84),(.92,-.39),(.83,.72),(.29,.93),(-.78,.79))
    verts=[];faces=[];size=width*.63
    for scale,z in ((.95,-.06),(1.,.09),(.84,.25)):
        for a,b in corners:
            u=(a+rng.uniform(-.07,.07))*size*scale
            v=(b+rng.uniform(-.07,.07))*size*.83*scale
            verts.append((x+u*math.cos(turn)-v*math.sin(turn),y+u*math.sin(turn)+v*math.cos(turn),z+rng.uniform(-.025,.025)))
    n=len(corners)
    faces.append(tuple(reversed(range(n))))
    for row in (0,n):
        for i in range(n):
            j=(i+1)%n
            faces.append((row+i,row+j,row+n+j,row+n+i))
    faces.append(tuple(range(n*2,n*3)))
    mesh=bpy.data.meshes.new('Split foundation')
    mesh.from_pydata(verts,[],faces);mesh.update()
    col=mesh.color_attributes.new(name='RockWeather',type='BYTE_COLOR',domain='POINT')
    for i,v in enumerate(col.data):v.color=(.55 if i<n else .08,0.,.18+.15*(i%3),1.)
    obj=bpy.data.objects.new('Split foundation',mesh);bpy.context.collection.objects.link(obj);part(obj,'Bedded')
    box((x,y,.267),(width*.72,width*.58,.10),'Oak',turn,.013)

def drum_rope():
    # One hemp line runs from a wrap across the drum to the mast.
    verts=[];faces=[];count=16*20
    for i in range(count+1):
        f=i/count;a=2*math.pi*i/20
        x=.195-1.055*f
        radius=.293+.004*math.sin(2*math.pi*f*2.4)
        for j in range(6):
            b=2*math.pi*j/6
            r=radius+.030*math.cos(b)
            verts.append((x+.030*math.sin(b),-.72+r*math.sin(a),.94+r*math.cos(a)))
        if i:
            for j in range(6):
                k=(j+1)%6
                faces.append(((i-1)*6+j,(i-1)*6+k,i*6+k,i*6+j))
    faces.extend((tuple(reversed(range(6))),tuple(range(count*6,count*6+6))))
    mesh=bpy.data.meshes.new('Wound hemp');mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new('Wound hemp',mesh);bpy.context.collection.objects.link(obj);part(obj,'Rope')

def derrick():
    # A raking jib in silhouette, with stays carried to separate buried anchor stones.
    for x,y,w,turn in ((1.22,-.2,.86,.32),(-.5,1.08,.68,-.48),(1.78,1.17,.76,.67)):
        footing(x,y,w,turn)
    rod((1.22,-.2,.28),(.47,-.12,4.68),.23,.16,'Oak',11)
    rod((1.78,1.17,.28),(.50,-.13,4.23),.16,.105,'Oak',11)
    rod((-.50,1.08,.28),(.52,-.13,4.40),.14,.10,'Oak',11)
    rod((1.08,-.18,3.65),(-2.56,-.34,5.21),.19,.119,'Oak',12)
    rod((1.14,-.2,1.25),(-1.55,-.29,4.75),.14,.108,'Oak',10)
    for x in (-1.02,.33):
        box((x,-.72,.67),(.25,.31,1.28),'Oak',0,.015)
        rod((x,-.72,.80),(x,-.72,.85),.08,.08,'Iron')
    rod((-1.19,-.72,.94),(.58,-.72,.94),.28,.28,'Oak',20)
    for x in (-1.02,.34):rod((x-.04,-.72,.94),(x+.04,-.72,.94),.37,.37,'Iron',20)
    drum_rope()
    rod((.64,-.72,.94),(.64,-.83,1.28),.034,.034,'Iron')
    rod((.64,-.83,1.28),(.88,-.83,1.28),.034,.044,'Oak')
    rod((-2.45,-.45,5.13),(-2.45,-.22,5.13),.185,.185,'Iron',24)
    cable([(-.86,-.72,1.233),(.4,-.18,4.54),(-2.45,-.34,5.27),(-2.52,-.34,1.34)],.029)
    # The split blank hangs just clear of two bearers; the slings meet under its belly.
    for x in (-3.05,-2.02):box((x,-.34,.10),(.22,1.03,.20),'Oak',.05)
    box((-2.55,-.34,.51),(1.46,.73,.53),'Blank',.028,.055)
    for x in (-3.02,-2.10):
        cable([(-2.52,-.34,1.34),(x,-.74,.64),(x,-.74,.245),(x,.05,.245),(x,.05,.64),(-2.52,-.34,1.34)],.026)
    export_parts('SM_QuarryYardDerrick')
def bench():
    for x in (-.78,.81):
        for y in (-.25,.28):rod((x*1.10,y*1.5,.02),(x,y,.76),.072,.091,'Oak',9)
    for y in (-.26,0,.26):box((0,y,.78),(2.17,.25,.12),'Oak',0,.013)
    box((.43,0,.936),(.69,.43,.19),'Blank',-.12,.035)
    for i in range(3):
        x=-.82+i*.21
        rod((x,-.14,.88),(x+.14,.19,.89),.025,.017,'Iron',6)
    rod((-.46,-.32,.90),(-.08,-.16,.92),.033,.036,'Oak',10)
    rod((-.12,-.25,.92),(-.04,-.07,.92),.085,.085,'Iron',8)
    for i in range(3):box((.04,.82+i*.19,.06+i*.025),(1.53-i*.13,.14,.12),'Oak',.1+i*.06,.014)
    export_parts('SM_QuarryDressingBench')

def build():
    if os.environ.get('QUARRY_DERRICK_ONLY')=='1':
        derrick()
        return
    bank(True);bank(False)
    survey_path=root/'Source/FPSGAME/WorldGeneration/TemperateQuarryRim.inl'
    survey_path.write_text('// Generated by author_quarry_approach.py from the rendered cap triangles.\n'
                           '// Species, local X/Y, support Z, yaw and target size (cm).\n'
                           +'\n'.join(rim_rows)+'\n',encoding='utf-8')
    if not rim_only:
        for release in falls:
            if release['kind'] in ('SlipPlate','KeyBlock'):detached_block(release)
        if os.environ.get('QUARRY_WALLS_ONLY')!='1':
            derrick();bench()


build()
