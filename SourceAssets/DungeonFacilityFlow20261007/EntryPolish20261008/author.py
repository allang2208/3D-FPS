"""Local entrance lamps and mechanical detail, metres, no render or gameplay."""
from pathlib import Path
import sys, math, json, hashlib, random
import bpy, bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parent; FLOW=ROOT.parent; PROJECT=FLOW.parents[1]
OUT=ROOT/'Authored'; OUT.mkdir(parents=True,exist_ok=True)
BASE='/Game/Dungeons/FacilityFlow20261007/EntryPolish20261008'
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts'))
import geometry as g
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonRoomShells20260922/Scripts'))
import room_detail_geometry as damage
ROLES=json.loads((PROJECT/'SourceAssets/DungeonReceptionHall20261006/Config/materials.json').read_text('utf8'))
ROLES['Aggregate']=dict(ROLES['Concrete'],existing_ue_path='/Game/Dungeons/WallUpgrade20260924/Materials/MI_BrokenConcrete',uv_meters_override=.65)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'; bpy.context.scene.unit_settings.scale_length=1
g.ROOM='EntryPolish'; mats={}
for role,r in ROLES.items():
    m=bpy.data.materials.new('EP_'+role);m.diffuse_color=(*r['basecolor_linear'],1);mats[role]=m

HARD='PassageHardware'; GLOW='PassageDiffusers'
def oval(kind,origin,normal,width,height,depth,mat):
    n=Vector(normal).normalized(); u=Vector((n.y,-n.x,0)); z=Vector((0,0,1)); p=Vector(origin)
    count=64
    points=[p+n*d+u*(width*.5*math.cos(i*math.tau/count))+z*(height*.5*math.sin(i*math.tau/count)) for d in (0,depth) for i in range(count)]
    faces=[tuple(reversed(range(count))),tuple(range(count,count*2))]+[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    g.poly(kind,points,faces,mat,smooth=[False,False]+[True]*count)
    return n,u,z

# Two bulkheads in the previously unlit flared end, fitted to the sloping walls.
for side in (-1,1):
    n=Vector((-side,.95/3,0)).normalized()
    wall=Vector((side*2.07,10.8,3.05))
    p=wall+n*.012
    n,u,z=oval(HARD,p,n,.36,.52,.042,'Teal')
    oval(HARD,p+n*.043,n,.307,.451,.012,'Rubber')
    oval(GLOW,p+n*.057,n,.278,.411,.028,'Glow')
    # Rolled rim, rounded steel guard and separate captive screws.
    rim=[p+n*.089+u*(.151*math.cos(i*math.tau/64))+z*(.216*math.sin(i*math.tau/64)) for i in range(65)]
    g.tube(HARD,rim,.009,'Steel',10)
    for dz in (-.125,0,.125):
        span=.143*math.sqrt(1-(dz/.209)**2)
        ps=[p+u*(span*(2*i/12-1))+z*dz+n*(.088+.026*math.sin(math.pi*i/12)) for i in range(13)]
        g.tube(HARD,ps,.006,'Steel',10)
    for du in (-.064,.064):
        span=.209*math.sqrt(1-(du/.143)**2)
        ps=[p+u*du+z*(span*(2*i/16-1))+n*(.088+.030*math.sin(math.pi*i/16)) for i in range(17)]
        g.tube(HARD,ps,.006,'Steel',10)
    for dz in (-.237,.237):g.bolt(HARD,p+n*.042+z*dz,n,.010)
    # Real conduit route from the service pipe level to the bottom of the lamp.
    pipe=Vector((side*2.065,10.79,2.25))
    g.rounded_pipe(HARD,[pipe,pipe+n*.065,Vector((p.x,p.y,2.50))+n*.065,Vector((p.x,p.y,2.80))+n*.027],.012,'Enamel',16)
    for zz in (2.48,2.70):
        c=Vector((p.x,p.y,zz))+n*.029
        g.ring(HARD,c,(0,0,1),.020,.012,.022,'Steel',24)

# An additional ceiling strip before the ceiling rises; no hanging obstruction.
g.box(HARD,(0,8.35,2.716),(.96,.245,.138),'Teal')
g.box(HARD,(0,8.35,2.641),(.896,.191,.028),'Rubber')
g.box(GLOW,(0,8.35,2.620),(.853,.151,.020),'Glow')
for x in (-.405,.405):
    g.box(HARD,(x,8.35,2.606),(.014,.199,.016),'Steel')
    for y in (8.26,8.44):g.bolt(HARD,(x,y,2.601),(0,0,-1),.008)
g.rounded_pipe(HARD,[(-1.47,8.35,2.30),(-1.47,8.35,2.752),(-.46,8.35,2.752)],.012,'Enamel',16)

# Proper backing pads, clamps and couplings on the existing pipes.
for side in (-1,1):
    for yy in (2.8,5.8,8.4,10.3,11.35):
        flare=max(0,yy-9);wallx=1.5+flare*.95/3
        px=1.45 if not flare else 1.45+max(0,yy-8.8)*.93/3.05
        tangent=Vector((side*.95/3 if flare else 0,1,0)).normalized()
        normal=Vector((-side, .95/3 if flare else 0,0)).normalized()
        yaw=math.atan2(tangent.y,tangent.x)-math.pi/2
        g.box(HARD,(side*(wallx-.008),yy,2.25),(.024,.19,.22),'Teal',yaw)
        g.ring(HARD,(side*px,yy,2.25),tangent,.060,.047,.040,'Steel',32)
        for dz in (-.082,.082):g.bolt(HARD,Vector((side*(wallx-.024),yy,2.25+dz)),normal,.009)
    for yy in (4.20,7.80):
        for d in (-.043,.043):g.ring(HARD,(side*1.45,yy+d,2.25),(0,1,0),.058,.044,.025,'Steel',32)
        g.ring(HARD,(side*1.45,yy,2.25),(0,1,0),.053,.044,.060,'Enamel',32)

# Replace the single flat threshold, so its surface cannot fight a duplicate.
# Tops are raised by only 14 mm and bevel back to the supporting floor.
cx,cy=-18.8,-16.65
xs=(-1.60,1.60)
profile=[(-.35,.002),(.35,.002),(.29,.014),(-.29,.014)]
vs=[(cx+x,cy+y,z) for x in xs for y,z in profile]
g.poly('BreachThreshold',vs,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'Steel')
for i in range(41):
    for dy in (-.15,.15):
        g.box('BreachThreshold',(cx-1.48+i*.074,cy+dy,.016),(.047,.006,.005),'Steel',math.radians(40 if dy<0 else -40))
for x in (-1.48,-.74,0,.74,1.48):
    for y in (-.255,.255):
        g.cylinder('BreachThreshold',(cx+x,cy+y,.014),(cx+x,cy+y,.020),.010,'Dark',16)
for x in (-1.55,1.55):g.box('BreachThreshold',(cx+x,cy,.016),(.033,.45,.004),'Yellow')

# Small embedded aggregate in the existing fractured cut, not flat overlays.
r=random.Random(108081); damage.setup(dict(poly=g.poly))
def noise(t,phase):return .041*math.sin(t*13.7+phase)+.017*math.sin(t*38.9-phase)+.009*math.sin(t*83.1+phase*2)
def side_edge(z,right=False):
    phase=2.9 if right else .4;sign=-1 if right else 1
    return (7.85 if right else 3.15)+sign*(.065*math.sin(z*4.3+phase)+.10*math.sin(z*1.8+phase)+noise(z,phase))
for right in (False,True):
    sign=-1 if right else 1
    for i in range(56):
        z=r.uniform(.08,3.42);x=-24.3+side_edge(z,right)-sign*.012
        damage.chunk((x,-16.66+r.uniform(-.12,.12),z),(r.uniform(.016,.052),r.uniform(.022,.050),r.uniform(.02,.065)),r,'Aggregate','BreachAggregate')
lx,rx=side_edge(3.55),side_edge(3.55,True)
for i in range(44):
    t=r.uniform(.02,.98);x=-24.3+lx+(rx-lx)*t
    z=3.55+math.sin(t*math.pi)*(.065*math.sin(t*56*.32)+.06)+noise(t*3.6,1.7)*math.sin(t*math.pi)
    damage.chunk((x,-16.66+r.uniform(-.12,.12),z+.012),(r.uniform(.025,.065),r.uniform(.024,.055),r.uniform(.018,.050)),r,'Aggregate','BreachAggregate')

threshold_only='--threshold-only' in sys.argv
records=[m for m in json.loads((ROOT/'geometry.json').read_text('utf8'))['meshes'] if m['kind']!='BreachThreshold'] if threshold_only else []
for (_,kind),data in g.G.items():
    if threshold_only and kind!='BreachThreshold':continue
    name='SM_EntryPolish_'+kind+('_V3' if kind=='BreachThreshold' else '_UV2');mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    order=list(dict.fromkeys(data['m']))
    for role in order:mesh.materials.append(mats[role])
    uv=mesh.uv_layers.new(name='UVMap');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
    for face,role,coords,smooth in zip(mesh.polygons,data['m'],data['uv'],data['smooth']):
        face.material_index=order.index(role);face.use_smooth=smooth
        axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(face.normal[a]))]
        scale=ROLES[role].get('uv_meters_override',ROLES[role].get('uv_meters',1))
        for j,li in enumerate(face.loop_indices):
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=coords[j] if coords else (p[axes[0]]/scale,p[axes[1]]/scale)
            age.data[li].color=(.09+.10*math.exp(-max(0,p.z)/.3),0,0,1)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    if kind not in ('BreachAggregate','BreachThreshold'):
        bevel=obj.modifiers.new('Small manufactured edge radii','BEVEL');bevel.width=.0015;bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(35);bevel.use_clamp_overlap=True
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    # Bevel interpolation can collapse UVs on the thin rib ends. Author UVs on
    # the finished triangles, including bevel faces, using each material's scale.
    # Local projections avoid submillimetre UV precision loss far from the pivot.
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.dissolve_degenerate(bm,dist=0.0000005,edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    obj.data.update();uv=obj.data.uv_layers.active
    for face in obj.data.polygons:
        axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(face.normal[a]))]
        role=order[face.material_index];scale=ROLES[role].get('uv_meters_override',ROLES[role].get('uv_meters',1))
        center=face.center
        offset=[math.floor(center[a]/scale) for a in axes]
        for li in face.loop_indices:
            p=obj.data.vertices[obj.data.loops[li].vertex_index].co
            uv.data[li].uv=(p[axes[0]]/scale-offset[0],p[axes[1]]/scale-offset[1])
    obj.data.calc_tangents(uvmap=uv.name)
    fbx=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
    records.append(dict(name=name,kind=kind,mesh=BASE+'/Meshes/'+name,fbx=str(fbx),sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),materials={'EP_'+role:ROLES[role]['existing_ue_path'] for role in order},collision=False,nanite=kind!='PassageDiffusers',cast_shadow=kind!='PassageDiffusers',triangles=len(obj.data.polygons)))
    print('ENTRY_POLISH_EXPORTED',kind,len(obj.data.polygons),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('EntryThresholdV3.blend' if threshold_only else 'EntryPolish.blend')))
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records),indent=2),encoding='utf8')
