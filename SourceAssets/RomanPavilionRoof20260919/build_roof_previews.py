"""Three editable roof candidates on the exported, installed pavilion.

Run with Blender 5.1 in background mode. Produces model renders, not UE screenshots.
No game assets, palette, collision or level are changed.
"""
import bpy
import math
import json
import sys
import random
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).parent
OUT = ROOT/'previews'
OUT.mkdir(exist_ok=True)
TAU = math.tau
DEG = math.pi/180
VARIANTS = ('A_Laurel','B_Verdigris','C_Celestial')


def material(name, color, metallic=0., roughness=.4, second=None, scale=5.):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    n=m.node_tree.nodes; links=m.node_tree.links
    p=n.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metallic
    p.inputs['Roughness'].default_value=roughness
    if second:
        noise=n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=scale
        noise.inputs['Detail'].default_value=3.
        ramp=n.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position=.24; ramp.color_ramp.elements[0].color=(*color,1)
        ramp.color_ramp.elements[1].position=.77; ramp.color_ramp.elements[1].color=(*second,1)
        links.new(noise.outputs['Fac'],ramp.inputs[0]); links.new(ramp.outputs['Color'],p.inputs['Base Color'])
        bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.12; bump.inputs['Distance'].default_value=.008
        links.new(noise.outputs['Fac'],bump.inputs['Height']); links.new(bump.outputs['Normal'],p.inputs['Normal'])
    return m


def mesh(name,vertices,faces,mat):
    data=bpy.data.meshes.new(name)
    data.from_pydata(vertices,[],faces); data.update()
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    for p in data.polygons:p.use_smooth=True
    return obj


def curves(name, paths, radius, mat, cyclic=False):
    data=bpy.data.curves.new(name,'CURVE'); data.dimensions='3D'
    data.bevel_depth=radius; data.bevel_resolution=2; data.resolution_u=1
    data.use_fill_caps=True
    for path in paths:
        s=data.splines.new('POLY'); s.points.add(len(path)-1)
        for p,co in zip(s.points,path):p.co=(*co,1)
        s.use_cyclic_u=cyclic
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def lathe(name,profile,mat,segments=96):
    vertices=[]; faces=[]
    for r,z in profile:
        for k in range(segments):
            a=TAU*k/segments; vertices.append((r*math.cos(a),r*math.sin(a),z))
    for j in range(len(profile)-1):
        for k in range(segments):
            a=j*segments+k; b=j*segments+(k+1)%segments
            faces.append((a,b,b+segments,a+segments))
    return mesh(name,vertices,faces,mat)


def torus(name,r,z,tube,mat,rotation=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=r,minor_radius=tube,major_segments=96,minor_segments=10,location=(0,0,z))
    obj=bpy.context.object; obj.name=name; obj.data.materials.append(mat)
    if rotation:obj.rotation_euler=rotation
    for p in obj.data.polygons:p.use_smooth=True
    return obj


def sphere(name,center,scale,mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=24,location=center)
    obj=bpy.context.object; obj.name=name; obj.scale=scale; obj.data.materials.append(mat)
    for p in obj.data.polygons:p.use_smooth=True
    return obj


def surface(phi,theta,lift=.025):
    """Follow the existing three inset rings, not a replacement smooth dome."""
    p=phi*DEG; a=theta*DEG
    inset=0.
    if 58<=phi<=74:inset=-.05*sum(phi<=v+1.e-6 for v in (74,66,58))
    elif 48<phi<58:inset=-.15*(phi-48)/10
    r=4*math.sin(p)+inset
    normal=Vector((math.sin(p)*math.cos(a),math.sin(p)*math.sin(a),math.cos(p)))
    return Vector((r*math.cos(a),r*math.sin(a),3.6+4*math.cos(p)))+normal*lift


def frame(phi,theta):
    a=theta*DEG; p=phi*DEG
    n=Vector((math.sin(p)*math.cos(a),math.sin(p)*math.sin(a),math.cos(p)))
    right=Vector((-math.sin(a),math.cos(a),0))
    up=Vector((-math.cos(p)*math.cos(a),-math.cos(p)*math.sin(a),math.sin(p)))
    return right,up,n


class Relief:
    def __init__(self):self.v=[];self.f=[]
    def leaf(self,center,axis,normal,length,width,depth):
        center=Vector(center); axis=Vector(axis).normalized(); normal=Vector(normal).normalized()
        across=normal.cross(axis).normalized(); start=len(self.v); n=10
        for i in range(n+1):
            t=i/n; w=math.sin(math.pi*t)**.85
            for side in (-1,0,1):
                q=center+axis*(t-.5)*length+across*side*width*w
                q+=normal*(depth*w*(1-abs(side)*.78))
                self.v.append(tuple(q))
        for i in range(n):
            for j in range(2):
                k=start+i*3+j;self.f.append((k,k+1,k+4,k+3))
    def star(self,center,right,up,normal,size,depth=.025):
        start=len(self.v); center=Vector(center)
        self.v.append(tuple(center+normal*depth))
        for i in range(16):
            a=TAU*i/16;r=size if i%2==0 else size*.3
            self.v.append(tuple(center+right*math.sin(a)*r+up*math.cos(a)*r))
        for i in range(16):self.f.append((start,start+1+(i+1)%16,start+1+i))
    def finish(self,name,mat):return mesh(name,self.v,self.f,mat)


def import_pavilion(stone,roof):
    bpy.ops.import_scene.fbx(filepath=str(ROOT/'pavilion_reference.fbx'),use_custom_normals=True)
    objects=[o for o in bpy.context.selected_objects if o.type=='MESH']
    for obj in objects[:]:
        if obj.name.startswith(('UCX_','UBX_','USP_','UCP_')):
            bpy.data.objects.remove(obj,do_unlink=True);objects.remove(obj)
    # Normalize exported units once. Source geometry and all column placements stay intact.
    coords=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    width=max(v.x for v in coords)-min(v.x for v in coords)
    unit=9.6/width
    for obj in objects:
        bpy.context.view_layer.objects.active=obj
        obj.select_set(True)
        obj.scale*=unit; obj.location*=unit
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        obj.name='ExistingPavilion__'+obj.name
        obj.data.materials.clear();obj.data.materials.append(stone);obj.data.materials.append(roof)
        for face in obj.data.polygons:
            c=face.center; radial=Vector((c.x,c.y,c.z-3.6))
            face.material_index=1 if c.z>=3.598 and face.normal.dot(radial)>.2 else 0
        obj.select_set(False)
    print('PAVILION_SOURCE_IMPORTED dimensions scaled to 9.6m',flush=True)


def ribs(count,mat,radius=.025):
    phis=sorted(set([4+i*.5 for i in range(173)]+[v+e for v in (58,66,74) for e in (-.05,.05)]))
    return curves('Dome_meridian_mouldings',[[surface(p,k*360/count,.038) for p in phis] for k in range(count)],radius,mat)


def rings(mat,angles=(58.15,66.15,74.15,88.5)):
    for p in angles:
        points=[surface(p,k*360/160,.032) for k in range(160)]
        curves('Existing_ledge_trim', [points], .019, mat,True)


def pinecone(stone,gold):
    lathe('Finial_stone_plinth',[(0,7.56),(.5,7.56),(.5,7.66),(.4,7.72),(.29,7.78),(.29,7.9),(0,7.9)],stone)
    torus('Finial_collar',.3,7.89,.023,gold)
    sphere('Pinecone_core',(0,0,8.34),(.31,.31,.5),stone)
    leaves=Relief()
    for row in range(9):
        z=7.94+row*.09
        rr=.305*math.sqrt(max(.02,1-((z-8.34)/.50)**2))
        for k in range(12):
            a=TAU*(k+.5*(row%2))/12
            n=Vector((math.cos(a),math.sin(a),.24)).normalized()
            axis=Vector((-.12*math.cos(a),-.12*math.sin(a),1))
            leaves.leaf((rr*math.cos(a),rr*math.sin(a),z),axis,n,.18,.074,.027)
    leaves.finish('Pinecone_overlapping_scales',stone)
    sphere('Pinecone_tip',(0,0,8.82),(.055,.055,.105),gold)


def variant_a(stone,gold):
    ribs(12,stone,.042);rings(gold)
    leaves=Relief();stems=[]
    for k in range(12):
        a=k*30+15
        stems.append([surface(p,a+math.sin(p*.1)*.45,.048) for p in range(30,86)])
        for i in range(11):
            p=34+i*4.5
            right,up,n=frame(p,a)
            for side in (-1,1):
                c=surface(p,a,.04)+right*side*.085
                leaves.leaf(c,(up*.52+right*side*.80),n,.29,.074,.055)
    curves('Laurel_branch_stems',stems,.016,gold)
    leaves.finish('Carved_laurel_pairs',stone)
    wave=[]
    for offset in (0,math.pi):
        wave.append([surface(84+.85*math.sin(TAU*i/720*36+offset),i*.5,.041) for i in range(720)])
    curves('Guilloche_base_border',wave,.018,gold,True)
    pinecone(stone,gold)


def floral_crown(gold,bronze):
    lathe('Floral_finial_pedestal',[(0,7.56),(.52,7.56),(.52,7.66),(.38,7.72),(.25,7.81),(.27,7.94),(.43,8.13),(.46,8.22),(.42,8.26),(.3,8.17),(.17,7.91),(0,7.91)],bronze)
    for r,z in ((.51,7.66),(.28,7.92),(.455,8.23)):torus('Crown_gilt_moulding',r,z,.026,gold)
    flowers=Relief();paths=[]
    for k in range(10):
        a=k*TAU/10
        pts=[]
        for i in range(26):
            t=i/25; r=.31+.28*math.sin(t*math.pi*.8)
            pts.append(Vector((r*math.cos(a),r*math.sin(a),8.08+t*.70)))
        paths.append(pts)
        for j in range(3):
            t=.25+j*.22;r=.31+.28*math.sin(t*math.pi*.8)
            c=Vector((r*math.cos(a),r*math.sin(a),8.08+t*.7))
            normal=Vector((math.cos(a),math.sin(a),.1))
            for side in (-1,1):
                tangent=Vector((-math.sin(a)*side*.65,math.cos(a)*side*.65,1))
                flowers.leaf(c,tangent,normal,.25,.085,.05)
    curves('Crown_palmette_spines',paths,.026,gold)
    flowers.finish('Crown_acanthus_petals',gold)
    sphere('Crown_centre_bud',(0,0,8.43),(.20,.20,.40),bronze)
    torus('Crown_bud_collar',.19,8.39,.018,gold)


def variant_b(gold,bronze):
    ribs(16,gold,.026);rings(gold)
    paths=[]
    for row,p in enumerate(range(18,88,5)):
        count=max(16,int(2*math.pi*4*math.sin(p*DEG)/.49))
        for k in range(count):
            theta=(k+.5*(row%2))*360/count
            path=[]
            for i in range(19):
                q=-math.pi/2+math.pi*i/18
                path.append(surface(p+2.35*math.cos(q),theta+180/count*math.sin(q),.046))
            paths.append(path)
    curves('Overlapping_scalloped_copper_tiles',paths,.0105,bronze)
    floral_crown(gold,bronze)


def celestial_finial(gold,blue):
    lathe('Armillary_pedestal',[(0,7.56),(.44,7.56),(.44,7.68),(.3,7.73),(.2,7.86),(.11,7.9),(.08,8.1),(0,8.1)],gold)
    z=8.46
    torus('Armillary_equator',.58,z,.026,gold)
    torus('Armillary_meridian',.62,z,.026,gold,(math.pi/2,0,0))
    torus('Armillary_oblique_ecliptic',.66,z,.04,gold,(57*DEG,22*DEG,30*DEG))
    torus('Armillary_second_meridian',.62,z,.019,gold,(math.pi/2,0,math.pi/2))
    sphere('Celestial_central_globe',(0,0,z),(.19,.19,.19),blue)
    curves('Polar_axis',[[(0,0,7.92),(0,0,9.15)]],.027,gold)
    s=Relief();s.star(Vector((0,0,9.18)),Vector((1,0,0)),Vector((0,0,1)),Vector((0,-1,0)),.13,.025)
    s.finish('Polar_star',gold)
    for i in range(24):
        a=i*TAU/24
        sphere('Zodiac_index',(math.cos(a)*.585,math.sin(a)*.585,z),(.028,.028,.028),gold)


def variant_c(gold,blue):
    ribs(12,gold,.024);rings(gold)
    stars=Relief();paths=[]
    for k in range(12):
        a=k*30+15
        # Same four-star medallion in each architectural bay.
        coords=[(31,a-2.5),(43,a+4),(56,a-3),(69,a+3)]
        line=[]
        for (p0,t0),(p1,t1) in zip(coords,coords[1:]):
            for i in range(25):
                f=i/24
                line.append(surface(p0+(p1-p0)*f,t0+(t1-t0)*f,.049))
        paths.append(line)
        for j,(p,t) in enumerate(coords):
            right,up,n=frame(p,t)
            stars.star(surface(p,t,.059),right,up,n,.10 if j%2 else .16,.032)
        right,up,n=frame(81,a)
        stars.star(surface(81,a,.058),right,up,n,.18,.036)
    curves('Constellation_inlay',paths,.008,gold)
    stars.finish('Eight_point_star_rosettes',gold)
    # Geometric key border around the dome skirt.
    paths=[]
    for k in range(60):
        a=k*6
        paths.append([surface(p,a+t,.041) for p,t in [(87.5,0),(83.8,0),(83.8,4.5),(86.5,4.5),(86.5,2),(85,2)]])
    curves('Classical_key_border',paths,.015,gold)
    celestial_finial(gold,blue)


def variant_c2(gold,stone):
    """Stable, spatially varied small constellations, with a few isolated stars."""
    rng=random.Random(20260919)
    ribs(12,gold,.024);rings(gold)
    stars=Relief();paths=[];placed=[];groups=[]
    def add_star(p,t,size,angle):
        right,up,n=frame(p,t)
        rr=right*math.cos(angle)+up*math.sin(angle)
        uu=up*math.cos(angle)-right*math.sin(angle)
        center=surface(p,t,.051)
        stars.star(center,rr,uu,n,size,.025)
        placed.append(center)
    def connection(a,b):
        p0,t0=a;p1,t1=b
        path=[surface(p0+(p1-p0)*i/40,t0+(t1-t0)*i/40,.043) for i in range(41)]
        paths.append(path)
    for k in range(12):
        count=rng.randint(3,6)
        centre_p=rng.uniform(40,61);centre_t=k*30+rng.uniform(11,19)
        spread_p=rng.uniform(11,18);spread_t=rng.uniform(5,8)
        pts=[]
        for attempt in range(200):
            p=rng.uniform(centre_p-spread_p,centre_p+spread_p)
            t=rng.uniform(centre_t-spread_t,centre_t+spread_t)
            point=surface(p,t)
            if any((point-surface(pp,tt)).length<.42 for pp,tt in pts):continue
            pts.append((p,t))
            if len(pts)==count:break
        # Short spanning branches, not a repeated vertical zig-zag.
        linked={0};edges=[]
        while len(linked)<len(pts):
            _,a,b=min(((surface(*pts[a])-surface(*pts[b])).length,a,b)
                      for a in linked for b in range(len(pts)) if b not in linked)
            linked.add(b);edges.append((a,b));connection(pts[a],pts[b])
        for j,(p,t) in enumerate(pts):
            size=rng.uniform(.115,.175) if j==0 else rng.uniform(.065,.115)
            add_star(p,t,size,rng.uniform(0,math.pi/4))
        groups.append({'points_phi_theta':pts,'edges':edges})
    scattered=[]
    for attempt in range(350):
        p=rng.uniform(21,81);t=rng.uniform(0,360)
        if min(t%30,30-t%30)<3:continue
        point=surface(p,t,.051)
        if any((point-other).length<.40 for other in placed):continue
        size=rng.uniform(.032,.074)
        add_star(p,t,size,rng.uniform(0,math.pi/4));scattered.append((p,t,size))
        if len(scattered)==22:break
    curves('C2_Varied_constellation_inlay',paths,.008,gold)
    stars.finish('C2_Random_star_rosettes',gold)
    border=[]
    for k in range(60):
        a=k*6
        border.append([surface(p,a+t,.041) for p,t in [(87.5,0),(83.8,0),(83.8,4.5),(86.5,4.5),(86.5,2),(85,2)]])
    curves('Classical_key_border',border,.015,gold)
    celestial_finial(gold,stone)
    (ROOT/'C2_constellations.json').write_text(json.dumps({'seed':20260919,'groups':groups,'scattered_stars':scattered},indent=2))


def variant_c3(gold,stone):
    """Different connected star maps, centred on a shared dome latitude."""
    rng=random.Random(2026091903)
    ribs(12,gold,.024);rings(gold,(74.15,88.5))
    stars=Relief();paths=[];groups=[]
    for k in range(12):
        # A loose closed figure, an interior junction and two outside branches.
        # Normalising each envelope aligns the composition while retaining its shape.
        count=rng.choice((5,6,7))
        phase=rng.uniform(-.3,.3)
        raw=[]
        for j in range(count):
            a=TAU*j/count+phase+rng.uniform(-.13,.13)
            r=rng.uniform(.76,1.05)
            raw.append((math.cos(a)*r,math.sin(a)*r))
        edges=[(j,(j+1)%count) for j in range(count)]
        raw.append((rng.uniform(-.2,.2),rng.uniform(-.18,.18)))
        junction=rng.randrange(count)
        edges.extend(((count,junction),(count,(junction+count//2)%count)))
        for side in (-1,1):
            anchor=max(range(count),key=lambda j:raw[j][1]*side)
            x,y=raw[anchor]
            edges.append((anchor,len(raw)))
            raw.append((x+rng.uniform(-.32,.32),y+side*rng.uniform(.55,.8)))
        xmin=min(x for x,y in raw);xmax=max(x for x,y in raw)
        ymin=min(y for x,y in raw);ymax=max(y for x,y in raw)
        centre_p=45.;centre_t=k*30+15.
        pts=[(centre_p+28*((y-ymin)/(ymax-ymin)-.5),
              centre_t+17.6*((x-xmin)/(xmax-xmin)-.5)) for x,y in raw]
        for a,b in edges:
            p0,t0=pts[a];p1,t1=pts[b]
            # Short arcs need fewer length segments than the long C2 branches.
            steps=max(6,math.ceil(max(abs(p1-p0),abs(t1-t0))/1.2))
            paths.append([surface(p0+(p1-p0)*i/steps,t0+(t1-t0)*i/steps,.043)
                          for i in range(steps+1)])
        for j,(p,t) in enumerate(pts):
            right,up,n=frame(p,t);angle=rng.uniform(0,math.pi/4)
            rr=right*math.cos(angle)+up*math.sin(angle)
            uu=up*math.cos(angle)-right*math.sin(angle)
            size=rng.uniform(.11,.14) if j==count else rng.uniform(.060,.091)
            stars.star(surface(p,t,.051),rr,uu,n,size,.025)
        groups.append({'centre_phi_theta':[centre_p,centre_t],
                       'points_phi_theta':pts,'edges':edges})
    curves('C3_Connected_constellation_inlay',paths,.008,gold)
    stars.finish('C3_Grouped_star_rosettes',gold)
    border=[]
    for k in range(60):
        a=k*6
        border.append([surface(p,a+t,.041) for p,t in [(87.5,0),(83.8,0),(83.8,4.5),(86.5,4.5),(86.5,2),(85,2)]])
    curves('Classical_key_border',border,.015,gold)
    celestial_finial(gold,stone)
    (ROOT/'C3_constellations.json').write_text(json.dumps({
        'seed':2026091903,'centre_phi':45.,'ring_phi':[74.15,88.5],
        'groups':groups,'scattered_stars':[]},indent=2))


def variant_c4(gold,stone):
    """Reproduce real sky-chart figures instead of procedural closed shapes."""
    data=json.loads((ROOT/'C4_constellations.json').read_text(encoding='utf-8'))
    ribs(12,gold,.024);rings(gold,tuple(data['ring_phi']))
    stars=Relief();paths=[]
    for group in data['groups']:
        xy=group['local_xy_m'];theta=group['centre_phi_theta'][1]
        def to_dome(x,y,lift):
            phi=45.-y/(4*DEG)
            azimuth=theta+x/(4*math.sin(phi*DEG)*DEG)
            return surface(phi,azimuth,lift)
        for a,b in group['edges']:
            x0,y0=xy[a];x1,y1=xy[b]
            steps=max(4,math.ceil(math.hypot(x1-x0,y1-y0)/.055))
            fractions=[i/steps for i in range(steps+1)]
            # Follow the existing stone ledges without sinking a line into a step.
            if abs(y1-y0)>1.e-8:
                for phi in (58.,66.,74.):
                    for epsilon in (-.03,.03):
                        f=((45.-phi-epsilon)*4*DEG-y0)/(y1-y0)
                        if 0<f<1:fractions.append(f)
            paths.append([to_dome(x0+(x1-x0)*f,y0+(y1-y0)*f,.043)
                          for f in sorted(fractions)])
        for i,(p,t) in enumerate(group['points_phi_theta']):
            right,up,n=frame(p,t)
            stars.star(surface(p,t,.051),right,up,n,group['star_radius_m'][i],.018)
    curves('C4_Real_constellation_lines',paths,.0065,gold)
    stars.finish('C4_Real_constellation_stars',gold)
    border=[]
    for k in range(60):
        a=k*6
        border.append([surface(p,a+t,.041) for p,t in [(87.5,0),(83.8,0),(83.8,4.5),(86.5,4.5),(86.5,2),(85,2)]])
    curves('Classical_key_border',border,.015,gold)
    celestial_finial(gold,stone)


def export_decor(prefix='C2'):
    """Export only additions; the UE assembly retains the original stone mesh."""
    originals=[o for o in bpy.context.scene.objects if not o.name.startswith('ExistingPavilion__') and o.type in ('CURVE','MESH')]
    for kind in ('GoldDecor','WhiteGlobe'):
        copies=[]
        for source in originals:
            is_white=source.name=='Celestial_central_globe'
            if is_white != (kind=='WhiteGlobe'):continue
            obj=source.copy();obj.data=source.data.copy();bpy.context.collection.objects.link(obj)
            if obj.type=='CURVE':obj.data.bevel_resolution=1
            copies.append(obj)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in copies:obj.select_set(True)
        bpy.context.view_layer.objects.active=copies[0]
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.join()
        joined=bpy.context.object;joined.name=prefix+'_'+kind
        coords=[joined.matrix_world@v.co for v in joined.data.vertices]
        bounds=[[min(v[i] for v in coords),max(v[i] for v in coords)] for i in range(3)]
        (ROOT/f'{prefix}_{kind}_bounds.json').write_text(json.dumps({'bounds_m':bounds}))
        bpy.ops.export_scene.fbx(filepath=str(ROOT/f'{prefix}_{kind}.fbx'),use_selection=True,
            object_types={'MESH'},add_leaf_bones=False,bake_anim=False,apply_unit_scale=True,
            axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
        bpy.data.objects.remove(joined,do_unlink=True)


def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def studio():
    scene=bpy.context.scene
    floor=material('Studio_warm_grey',(.135,.155,.16),roughness=.8)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.045))
    bpy.context.object.name='Preview_only_floor';bpy.context.object.data.materials.append(floor)
    world=bpy.data.worlds.new('Studio_environment');scene.world=world;world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.27,.32,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.45
    for name,loc,power,size,color in [('Key',(-6,-9,15),2600,8,(1.,.91,.77)),('Fill',(8,-4,10),1700,7,(.77,.88,1.)),('Rim',(1,8,14),3000,6,(1.,.95,.86))]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc;aim(obj,(0,0,4))
    data=bpy.data.lights.new('Soft_sun','SUN');data.energy=1.1;data.angle=.20
    obj=bpy.data.objects.new('Soft_sun',data);scene.collection.objects.link(obj);obj.rotation_euler=(25*DEG,-28*DEG,-28*DEG)
    camdata=bpy.data.cameras.new('Preview_camera');cam=bpy.data.objects.new('Preview_camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
    camdata.type='ORTHO';camdata.lens=50
    scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True
    scene.cycles.max_bounces=6
    prefs=bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type='OPTIX';prefs.get_devices()
        for dev in prefs.devices:dev.use=dev.type!='CPU'
        if any(dev.use for dev in prefs.devices):scene.cycles.device='GPU'
    except Exception as exc:print('Cycles uses CPU:',exc,flush=True)
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=.35
    scene.render.film_transparent=False
    return scene,cam


def render(scene,cam,stem,view):
    if view=='hero':
        cam.location=(11,-17,12.7);aim(cam,(0,0,4.05));cam.data.ortho_scale=12.6
        scene.render.resolution_x=1536;scene.render.resolution_y=1536
    elif view=='roof':
        cam.location=(8,-12,13.5);aim(cam,(0,0,5.95));cam.data.ortho_scale=9.15
        scene.render.resolution_x=1536;scene.render.resolution_y=1088
    else:
        cam.location=(3.4,-5.8,10.7);aim(cam,(0,0,8.32));cam.data.ortho_scale=2.28
        scene.render.resolution_x=896;scene.render.resolution_y=896
    scene.render.filepath=str(OUT/f'{stem}_{view}.png')
    bpy.ops.render.render(write_still=True)
    print('PREVIEW_RENDERED '+scene.render.filepath,flush=True)


def build(which):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    stone=material('Shared_ivory_marble',(.64,.61,.54),roughness=.43,second=(.82,.79,.70),scale=6.)
    gold=material('Aged_satin_gilt',(.48,.29,.095),metallic=.78,roughness=.31,second=(.69,.47,.19),scale=7.)
    bronze=material('Aged_bronze_edges',(.12,.085,.042),metallic=.7,roughness=.37,second=(.23,.18,.082),scale=12.)
    green=material('Patinated_copper',(.047,.115,.108),metallic=.45,roughness=.44,second=(.15,.29,.25),scale=7.)
    blue=material('Midnight_lapis',(.014,.038,.08),metallic=.20,roughness=.30,second=(.04,.10,.19),scale=9.)
    roof={'A_Laurel':stone,'B_Verdigris':green,'C_Celestial':blue,'C2_WhiteCelestial':stone,'C3_WhiteCelestial':stone,'C4_WhiteCelestial':stone}[which]
    import_pavilion(stone,roof)
    if which=='A_Laurel':variant_a(stone,gold)
    elif which=='B_Verdigris':variant_b(gold,bronze)
    elif which=='C_Celestial':variant_c(gold,blue)
    elif which=='C2_WhiteCelestial':
        variant_c2(gold,stone)
        export_decor('C2')
    elif which=='C3_WhiteCelestial':
        variant_c3(gold,stone)
        export_decor('C3')
    else:
        variant_c4(gold,stone)
        export_decor('C4')
    scene,cam=studio()
    cam.location=(11,-17,12.7);aim(cam,(0,0,4.05));cam.data.ortho_scale=12.6
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/f'{which}.blend'))
    for view in ('hero','roof','finial'):render(scene,cam,which,view)
    (OUT/f'{which}_complete.json').write_text(json.dumps({'variant':which,'renderer':'Blender 5.1 Cycles','ue_integrated':False,'source':'pavilion_reference.fbx','views':['hero','roof','finial']},indent=2))


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    for name in args or VARIANTS:build(name)
