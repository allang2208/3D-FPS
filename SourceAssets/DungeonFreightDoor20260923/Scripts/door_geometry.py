"""Freight shutter, articulated security grille and wall control station, metres."""
import math
from pathlib import Path
import bpy
from mathutils import Vector

BASE='/Game/Dungeons/FreightDoor20260923'
FINISHES={
    'FreightCoat':(.13,.17,.125), 'FreightTrack':(.28,.30,.29),
    'FreightGate':(.095,.12,.10), 'FreightPanel':(.32,.34,.275),
    'FreightRubber':(.014,.018,.016), 'FreightAmber':(.8,.22,.028),
    'FreightLegend':(.74,.70,.54), 'FreightPlate':(.022,.031,.029),
    'FreightWarning':(.54,.34,.055),
}


def build(h, split=False):
    for key,color in FINISHES.items():
        h['MAPPING'][key]=BASE+'/Materials/M_'+key
        if key not in h['MATS']:
            mat=bpy.data.materials.new('RS_'+key)
            mat.diffuse_color=(*color,1)
            h['MATS'][key]=mat
    kind='DoorLeaf' if split else 'Lift'
    box,poly,tube=h['box'],h['poly'],h['tube']
    detail=h['detail']
    def b(center,size,mat='FreightCoat'):
        box(kind,center,size,mat)
    def pipe(points,r,mat='FreightTrack',sides=32):
        tube(kind,points,r,mat,sides)
    def ring(p,outer,inner,length,mat='FreightTrack'):
        detail.ring(p,(0,-1,0),outer,inner,length,mat,32,kind)
    def bolt(x,y,z,r=.007):
        ring((x,y,z),r*1.4,r*.42,.002)
        # Independent hex head plus a recessed screwdriver slot.
        vs=[]
        for yy in (y-.004,y-.001):
            vs.extend((x+r*math.cos(i*math.tau/6),yy,z+r*math.sin(i*math.tau/6)) for i in range(6))
        fs=[tuple(range(6)),tuple(reversed(range(6,12)))]
        fs += [(i,i+6,(i+1)%6+6,(i+1)%6) for i in range(6)]
        poly(kind,vs,fs,'FreightTrack')
        b((x,y-.0044,z),(r*1.2,.0007,r*.20),'FreightPlate')
    def flat_link(a,c,width=.021,depth=.008):
        a,c=Vector(a),Vector(c);axis=(c-a).normalized()
        side=Vector((axis.z,0,-axis.x));normal=Vector((0,1,0))
        vs=[tuple(p+side*s*width/2+normal*t*depth/2)
            for p in (a,c) for s,t in ((-1,-1),(1,-1),(1,1),(-1,1))]
        poly(kind,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'FreightGate')
    def text_label(text,x,y,z,size,mat='FreightLegend'):
        curve=bpy.data.curves.new('freight_stamped_legend','FONT')
        curve.body=text;curve.size=size;curve.align_x='CENTER';curve.align_y='CENTER'
        curve.extrude=.00015;curve.resolution_u=4
        obj=bpy.data.objects.new('freight_stamped_legend',curve)
        bpy.context.scene.collection.objects.link(obj)
        obj.location=(x,y,z);obj.rotation_euler=(math.pi/2,0,0)
        bpy.context.view_layer.update()
        mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        transform=obj.matrix_world.copy()
        poly(kind,[tuple(transform@v.co) for v in mesh.vertices],[tuple(f.vertices) for f in mesh.polygons],mat)
        bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh);bpy.data.curves.remove(curve)
    def icon_arrow(x,y,z,up):
        d=1 if up else -1
        points=[(x,z+d*.009),(x+.007,z-d*.001),(x+.0025,z-d*.001),
                (x+.0025,z-d*.009),(x-.0025,z-d*.009),(x-.0025,z-d*.001),(x-.007,z-d*.001)]
        # Thin printed arrow on the flush rubber actuator face.
        verts=[(xx,y,zz) for xx,zz in points]
        area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))
        face=tuple(range(len(verts))) if area>0 else tuple(reversed(range(len(verts))))
        poly(kind,verts,[face],'FreightLegend')

    # Recess liner terminates at the room wall; the visible curtain sits in front.
    b((9,17.856,2.155),(4.65,.040,3.11),'FreightRubber')
    if split:kind='DoorFrame'
    # True C-channel jambs, replaceable rubbing strips, feet and anchoring bolts.
    for x,sgn in ((6.60,-1),(11.40,1)):
        b((x+sgn*.075,17.745,2.175),(.020,.26,3.15))
        for y in (17.62,17.865):
            b((x,y,2.175),(.17,.020,3.15))
        b((x-sgn*.058,17.655,2.175),(.026,.038,3.12),'FreightTrack')
        b((x,17.735,.612),(.25,.29,.024),'FreightTrack')
        for z in (.80,1.55,2.30,3.08,3.64):
            bolt(x,17.603,z,.010)
        for z in (.90,2.94):
            b((x+sgn*.045,17.695,z),(.07,.19,.025),'FreightTrack')
    # Folded head cover, inspection seam, fascia fasteners and access latch.
    fascia_y=17.291 if split else 17.571
    if not split:b((9,17.725,3.84),(5.0,.28,.23))
    b((9,fascia_y,3.845),(4.81,.012,.172),'FreightPanel')
    for x in (6.72,7.82,10.18,11.28):
        for z in (3.789,3.904):bolt(x,fascia_y-.010,z,.006)
    b((9,fascia_y-.013,3.845),(1.18,.011,.122),'FreightPlate')
    text_label('VAULT  01' if split else 'FREIGHT  02',9,fascia_y-.021,3.849,.078)
    if split:kind='DoorLeaf'
    # Each 14.4 cm curtain lath has a pressed crown, return lip and shadow groove.
    section=[(17.790,-.067),(17.764,-.060),(17.736,-.043),(17.724,-.025),
             (17.724,.024),(17.738,.043),(17.773,.055),(17.790,.065)]
    if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(section,section[1:]+section[:1]))<0:
        section.reverse()
    for i in range(21):
        z=.69+i*.144
        n=len(section)
        vs=[(x,y,z+zz) for x in (6.71,11.29) for y,zz in section]
        fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        fs += [(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        poly(kind,vs,fs,'FreightCoat')
        for x in (6.745,11.255):
            bolt(x,17.719,z,.005)
    # Bottom seal and modest threshold; floor level remains 0.6 m.
    b((9,17.738,.640),(4.59,.082,.030),'FreightRubber')
    if split:kind='DoorFrame'
    b((9,17.65,.608),(4.77,.39,.016),'FreightTrack')
    for x in (6.78,7.9,10.1,11.22):
        pipe([(x,17.53,.616),(x,17.53,.620)],.009,'FreightTrack',24)
    # A separate front security grille with real pin joints and roller tracks.
    for z in (.689,3.604):
        b((9,17.545,z),(4.68,.104,.036),'FreightGate')
        b((9,17.488,z),(4.68,.010,.050),'FreightTrack')
    if split:kind='DoorLeaf'
    left,right=6.76,11.24
    for i in range(13):
        x=left+(right-left)*i/12
        b((x,17.55,2.142),(.021,.022,2.875),'FreightGate')
        for z in (.714,3.577):
            ring((x,17.544,z),.026,.009,.016)
            pipe([(x,17.524,z),(x,17.492,z)],.008,'FreightTrack',20)
    for i in range(12):
        x0=left+(right-left)*i/12;x1=left+(right-left)*(i+1)/12
        for tier in range(3):
            z0=.725+tier*.945;z1=z0+.945
            flat_link((x0,17.520,z0),(x1,17.520,z1))
            flat_link((x0,17.503,z1),(x1,17.503,z0))
            bolt((x0+x1)/2,17.492,(z0+z1)/2,.006)
        for z in (.725,1.670,2.615,3.56):bolt(x0,17.491,z,.005)
    # Central lock stile, striker, key escutcheon and a bent pull handle.
    b((9,17.480,2.13),(.064,.032,2.86),'FreightGate')
    b((9,17.453,1.77),(.15,.022,.35),'FreightPanel')
    for z in (1.623,1.917):bolt(9,17.438,z,.006)
    ring((9,17.432,1.82),.022,.010,.011)
    pipe([(9,17.429,1.82),(9,17.420,1.82)],.010,'FreightPlate',24)
    b((9,17.416,1.82),(.0025,.002,.011),'FreightTrack')
    from rail_geometry import rounded
    pipe(rounded([(8.95,17.436,1.67),(8.95,17.36,1.67),
                  (8.95,17.36,1.87),(8.95,17.436,1.87)],.025),.012)
    if split:kind='DoorFrame'
    for x in (6.36,11.64):
        b((x,17.765,.83),(.20,.22,.42),'FreightRubber')
        b((x,17.645,.83),(.16,.018,.29),'FreightTrack')
        for z in (.73,.93):bolt(x,17.632,z,.008)

    # Wall control station: rear mount, enclosure, gasket, face, drip hood and screws.
    x=12.05
    b((x,17.872,1.755),(.265,.012,.47),'FreightTrack')
    b((x,17.810,1.755),(.245,.112,.435),'FreightCoat')
    b((x,17.749,1.755),(.251,.011,.441),'FreightRubber')
    b((x,17.738,1.755),(.247,.012,.437),'FreightPanel')
    b((x,17.767,1.991),(.290,.205,.010),'FreightCoat')
    b((x,17.668,1.977),(.290,.008,.026),'FreightCoat')
    for dx in (-.101,.101):
        for z in (1.557,1.953):bolt(x+dx,17.728,z,.005)
    # Amber pilot has a physical recessed socket and bezel; restrained emissive.
    ring((x,17.719,1.895),.025,.018,.019)
    pipe([(x,17.718,1.895),(x,17.706,1.895)],.0175,'FreightAmber',40)
    text_label('POWER',x,17.730,1.851,.018,'FreightPlate')
    for z,up in ((1.786,True),(1.681,False)):
        ring((x,17.717,z),.033,.025,.024)
        ring((x,17.701,z),.026,.023,.010,'FreightRubber')
        pipe([(x,17.711,z),(x,17.690,z)],.0225,'FreightRubber',40)
        icon_arrow(x,17.688,z,up)
    b((x,17.729,1.598),(.15,.003,.027),'FreightPlate')
    text_label('SERVICE',x,17.726,1.599,.018)
    # Gland and rigid conduit contact the back wall and enter the header housing.
    detail.ring((x,17.824,1.52),(0,0,1),.021,.013,.034,'FreightTrack',24,kind)
    route=[(x,17.824,1.503),(x,17.824,1.40),(12.30,17.845,1.40),
           (12.30,17.845,4.10),(11.12,17.845,4.10),(11.12,17.78,3.963)]
    pipe(rounded(route,.065),.013,'FreightCoat',24)
    for z in (1.62,2.52,3.47):
        b((12.30,17.872,z),(.075,.012,.045),'FreightTrack')
        # Strap hugs the conduit, screws terminate on the mounting plate.
        pipe([(12.265,17.862,z),(12.275,17.828,z),(12.325,17.828,z),(12.335,17.862,z)],.0035)
        for dx in (-.028,.028):bolt(12.30+dx,17.860,z,.004)
    # Limited hazard marking on the frame feet; no floor decal across the route.
    for x in (6.60,11.40):
        b((x,17.600,.96),(.104,.002,.24),'FreightWarning')
        for z in (.88,.96,1.04):
            flat_link((x-.043,17.597,z-.020),(x+.043,17.597,z+.020),.018,.002)


def export_lift(h, kind='Lift', name='SM_RS_FreightTransfer_Lift'):
    """Dedicated compact export with real edge radii and localized material masks."""
    g=h['GROUPS'][kind];names=list(dict.fromkeys(g['m']))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    for key in names:mesh.materials.append(h['MATS'][key])
    uv=mesh.uv_layers.new(name='UVMap')
    age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
    for face,mat,authored,smooth in zip(mesh.polygons,g['m'],g['uv'],g['smooth']):
        face.material_index=names.index(mat);face.use_smooth=smooth
        axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
        for corner,li in enumerate(face.loop_indices):
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=authored[corner] if authored is not None else (co[dims[0]]/.8,co[dims[1]]/.8)
            joint=math.exp(-((co.z-.625)/.30)**2)
            foot=math.exp(-max(0,co.z-.6)*3.0)
            patch=.5+.5*math.sin(co.x*17.3+co.z*23.7)*math.cos(co.z*4.1)
            # R: sheltered dirt, G: exposed rubbed steel, B: localized corrosion.
            grime=.10+.30*foot+.14*joint
            edge=.04
            if mat=='FreightCoat':
                edge=.16 if abs(face.normal.z)>.5 else .035
            if mat=='FreightTrack':edge=.38
            if mat=='FreightPanel':grime=.07;edge=.04
            rust=(.10+.55*foot+.17*joint)*patch
            age.data[li].color=(min(.65,grime),edge,min(.8,rust),1)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bevel=obj.modifiers.new('Formed steel and enclosure edge radii','BEVEL')
    bevel.width=.0012;bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=.62
    bevel.harden_normals=True;bpy.ops.object.modifier_apply(modifier=bevel.name)
    normal=obj.modifiers.new('Weighted manufactured faces','WEIGHTED_NORMAL')
    normal.keep_sharp=True;normal.weight=25;bpy.ops.object.modifier_apply(modifier=normal.name)
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    path=h['OUT']/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    h['RECORDS'].append(dict(name=name,room=h['ROOM']['id'],kind=kind,fbx=str(path),
        origin_m=h['ROOM']['origin_m'],materials={'RS_'+n:h['MAPPING'][n] for n in names},collision=True))
    obj.location=h['ROOM']['origin_m']
    return obj
