"""星潮之核: precise forged crescents, rune rail, six-spoke cradle and blue optics."""
import bpy,bmesh,types,math,json,sys,random,ast
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;FAMILY=P.parent
source=(FAMILY/'FinalTollHammerHeadV2/author_model.py').read_text('utf-8')
m=types.ModuleType('star_tide_tools');m.__file__=str(P/'author_model.py')
exec(compile(source,'<surface_tools>','exec'),m.__dict__)
m.initialize();bpy.context.preferences.filepaths.save_version=0
sys.path.insert(0,str(FAMILY/'HeadRunePBRV3'))
from surface_authoring import refine_metal
for mat in (m.STEEL,m.SILVER):refine_metal(mat)
C=Vector((0,0,-.080));R=.0405;optics=[];internals=[];rng=random.Random(20261024)
navy=m.simple_material('AUTHOR_DeepBlue_Enamel',(.009,.024,.055),.24,.21)
np=navy.node_tree.nodes.get('Principled BSDF');np.inputs['Coat Weight'].default_value=.48
refine_metal(navy)
def luminous(name,color,power,rough=.22):
    mat=m.simple_material(name,color,0.,rough);p=mat.node_tree.nodes.get('Principled BSDF')
    p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=power
    return mat
energy=luminous('M_StarTide_Rune',(.007,.19,.92),1.6)
glass=m.simple_material('M_StarTide_Glass',(.012,.095,.34),0.,.055)
p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Transmission Weight'].default_value=.97;p.inputs['IOR'].default_value=1.44;p.inputs['Coat Weight'].default_value=.45
gem=m.simple_material('M_StarTide_Gem',(.004,.065,.28),.28,.075)
p=gem.node_tree.nodes.get('Principled BSDF');p.inputs['Coat Weight'].default_value=.6;p.inputs['Emission Color'].default_value=(.003,.10,.42,1);p.inputs['Emission Strength'].default_value=.7
core=luminous('M_StarTide_Core',(.20,.58,1.),4.)
volume=m.simple_material('M_StarTide_Volume',(.002,.02,.12),0.,.3)
p=volume.node_tree.nodes.get('Principled BSDF');p.inputs['Transmission Weight'].default_value=.94;p.inputs['Alpha'].default_value=.1
filament=luminous('M_StarTide_Filaments',(.025,.42,1.),3.)
sparks=luminous('M_StarTide_Particles',(.18,.52,1.),3.)

def catmull(keys,t):
    f=max(0.,min(.999999,t))*(len(keys)-1);i=int(f);s=f-i
    a=Vector(keys[max(i-1,0)]);b=Vector(keys[i]);c=Vector(keys[min(i+1,len(keys)-1)]);d=Vector(keys[min(i+2,len(keys)-1)])
    return .5*(2*b+(-a+c)*s+(2*a-5*b+4*c-d)*s*s+(-a+3*b-3*c+d)*s*s*s)

def frame_at(path,t,radial=False,closed=False):
    p=Vector(path(t));lo=(t-.0003)%1 if closed else max(0,t-.0003);hi=(t+.0003)%1 if closed else min(1,t+.0003)
    tangent=(Vector(path(hi))-Vector(path(lo))).normalized()
    n=(p-C).normalized() if radial else Vector((0,-1,0))
    n=(n-tangent*n.dot(tangent)).normalized();u=tangent.cross(n).normalized()
    return p,u,n

# Inset face is 0.6 mm below the outer silver arris. Closed sidewalls and rear
# bevels keep the silhouettes solid from first- and third-person views.
CROSS=[(-.8,-.0013),(.8,-.0013),(1,-.0008),(1,.0008),(.85,.0015),(.72,.0015),(.72,.0009),(-.72,.0009),(-.72,.0015),(-.85,.0015),(-1,.0008),(-1,-.0008)]
def ribbon(name,path,width,radial=False,count=161,closed=False,face_mat=navy):
    def point(t,x,d):
        p,u,n=frame_at(path,t,radial,closed);return p+u*x+n*d
    verts=[];den=count if closed else count-1
    for j in range(count):
        t=j/den;w=width(t)
        verts += [point(t,x*w,d) for x,d in CROSS]
    sides=len(CROSS);faces=[] if closed else [tuple(reversed(range(sides)))]
    for j in range(count if closed else count-1):
        for k in range(sides):faces.append((j*sides+k,j*sides+(k+1)%sides,((j+1)%count)*sides+(k+1)%sides,((j+1)%count)*sides+k))
    if not closed:faces.append(tuple((count-1)*sides+k for k in range(sides)))
    obj=m.solid(name,verts,faces,m.SILVER);obj.data.materials.append(face_mat)
    offset=0 if closed else 1
    for poly in obj.data.polygons:
        if offset<=poly.index<offset+(count if closed else count-1)*sides and (poly.index-offset)%sides==6:poly.material_index=1
    return obj,point

def cut_runes(obj,name,loops):
    # Closed tubular loops have no overlapping end caps; this avoids the
    # deleted-body boolean failure of the original violet authoring attempt.
    cutters=[]
    for i,points in enumerate(loops):
        pts=[Vector(v) for v in points[:-1]];verts=[];faces=[];sides=8
        for j,p in enumerate(pts):
            t=(pts[(j+1)%len(pts)]-pts[(j-1)%len(pts)]).normalized();h=Vector((0,0,1)) if abs(t.z)<.9 else Vector((0,1,0))
            u=t.cross(h).normalized();v=t.cross(u).normalized()
            verts += [p+.00034*(u*math.cos(k*math.tau/sides)+v*math.sin(k*math.tau/sides)) for k in range(sides)]
        for j in range(len(pts)):
            for k in range(sides):faces.append((j*sides+k,j*sides+(k+1)%sides,((j+1)%len(pts))*sides+(k+1)%sides,((j+1)%len(pts))*sides+k))
        m.solid(name+'_closed_cut_'+str(i),verts,faces,m.BLACK,group=cutters)
    cutter=m.join_group(cutters,name+'_rune_cutters');m.activate(obj)
    mod=obj.modifiers.new('True inset engraved channels','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.use_self=True;mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)

GLYPHS=[[(0,-1),(.7,-.18),(0,1),(-.7,.18),(0,-1)],
        [(-.65,-.8),(.65,-.5),(.4,.4),(-.4,.8),(-.65,-.8)],
        [(0,-1),(.65,-.1),(.24,.25),(0,1),(-.65,.1),(-.24,-.25),(0,-1)],
        [(-.65,-.6),(.15,-1),(.65,.6),(-.15,1),(-.65,-.6)]]
def decorated_ribbon(obj,point,width,label,ts,dt=.024):
    loops=[]
    for i,t in enumerate(ts):
        shape=GLYPHS[i%len(GLYPHS)];scale=min(.0018,width(t)*.37)
        loops.append([point(t+y*dt,x*scale,.00102) for x,y in shape])
        m.stroke(label+'_blue_inlay',[point(t+y*dt,x*scale,.00082) for x,y in shape],.000145,energy,8,m.ENERGY)
    cut_runes(obj,label,loops)
    for side in (-1,1):
        m.stroke(label+'_fine_chasing',[point(.02+.96*j/140,side*width(.02+.96*j/140)*.81,.00163) for j in range(141)],.00016,m.SILVER,6)

# Original connection plane and local pivot are retained, independent of the
# ornamental silhouette. All authored dimensions are metres.
factory=bpy.data.objects['SM_RuneboundWarhammer_pommel_factory']
collar=factory.copy();collar.data=factory.data.copy();m.BUILD.objects.link(collar)
collar.name='Retained_factory_interface_2mm';collar.hide_render=False;collar.hide_set(False);collar.location=(0,0,0)
bm=bmesh.new();bm.from_mesh(collar.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,-.002),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z+.002)<.00001 for v in e.verts)]
if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
bm.to_mesh(collar.data);bm.free();m.PARTS.append(collar)

def hex_loft(name,sections,mat):
    verts=[(r*math.cos(math.tau*i/6),r*math.sin(math.tau*i/6),z) for r,z in sections for i in range(6)]
    faces=[tuple(reversed(range(6))),tuple((len(sections)-1)*6+i for i in range(6))]
    for j in range(len(sections)-1):
        for i in range(6):faces.append((j*6+i,j*6+(i+1)%6,(j+1)*6+(i+1)%6,(j+1)*6+i))
    return m.solid(name,verts,faces,mat,.0004,5)
hex_loft('Stepped_hexagonal_neck',[(.019,-.002),(.0208,-.005),(.0208,-.009),(.0196,-.011),(.0202,-.027),(.024,-.030),(.024,-.033)],m.STEEL)
for name,sections in [('Upper_silver_step',[(.0208,-.005),(.0214,-.006),(.0214,-.008),(.0208,-.009)]),('Lower_silver_step',[(.0202,-.026),(.0246,-.029),(.0246,-.031),(.024,-.032)])]:hex_loft(name,sections,m.SILVER)
for i in range(6):
    a=math.tau*(i+.5)/6;radial=Vector((math.cos(a),math.sin(a),0));u=Vector((-math.sin(a),math.cos(a),0))
    f=m.frame(radial*.0176+Vector((0,0,-.018)),radial,u)
    plate=m.strip('Socket_recessed_enamel_panel',f,[(-.0068,-.0063),(.0068,-.0063),(.0063,.0063),(-.0063,.0063)],0,.0009,navy,.00025)
    paths=[]
    for j in range(2):
        y0=-.0032+j*.0064;shape=GLYPHS[(i+j)%4]
        paths.append([m.pt(f,x*.0015,y0+y*.0023,.00102) for x,y in shape])
        m.stroke('Socket_cyan_inlay',[m.pt(f,x*.0015,y0+y*.0023,.00082) for x,y in shape],.00014,energy,8,m.ENERGY)
    cut_runes(plate,'Socket_panel_'+str(i),paths)
    for side in (-1,1):m.stroke('Neck_edge_rib',[m.pt(f,side*.0074,y,.0011) for y in (-.008,.008)],.0005,m.SILVER,8)
    for y in (-.0058,.0058):m.disk('Socket_recessed_fastener',m.frame(m.pt(f,0,y,.001),radial,u),.00065,0,.00025,m.SILVER,20)

upper=[(-.010,0,-.024),(-.024,-.001,-.036),(-.040,-.002,-.049),(-.050,-.002,-.067),(-.051,-.004,-.086),(-.043,-.012,-.102)]
lower=[(.010,0,-.137),(.027,.001,-.124),(.043,-.001,-.109),(.050,-.003,-.091),(.048,-.006,-.074),(.040,-.015,-.056)]
for index,keys in enumerate((upper,lower)):
    path=lambda t,keys=keys:catmull(keys,t)
    width=lambda t:.00045+(.0056+.0011*math.sin(t*math.pi*3)**2)*math.sin(math.pi*(.10+.90*t))**.8
    obj,point=ribbon('Layered_crescent_'+str(index),path,width,count=193)
    decorated_ribbon(obj,point,width,'Crescent_'+str(index),[.14+i*.083 for i in range(9)])
    # Reinforced ends and hand-finished segmented silver edge joints.
    for t in (.20,.48,.74):
        p,u,n=frame_at(path,t);f=m.frame(p,n,u);w=width(t)
        m.strip('Crescent_edge_joint',f,[(-w,-.0011),(w,-.0011),(w*.83,.0011),(-w*.83,.0011)],.00085,.0017,m.SILVER,.00015)

# Solid diagonal orbital rail, with a dark central gutter and two silver bevels.
axis=Vector((.81915,0,.57358));front=Vector((0,-1,0));rail_r=.0436
rail=lambda t:C+rail_r*(axis*math.sin(t*math.tau)+front*math.cos(t*math.tau))
rail_width=lambda t:.00325+.00045*math.cos(t*math.tau*2)**2
rail_obj,rail_point=ribbon('Continuous_diagonal_runic_rail',rail,rail_width,radial=True,count=256,closed=True,face_mat=m.BLACK)
rail_loops=[]
for i in range(32):
    t=(i+.5)/32
    # Sapphire windows sit in actual recessed channels, alternating with tiny
    # angular runes rather than painted bright squares on a flat ribbon.
    loop=[rail_point((t+y*.0032)%1,x*.00115,.00102) for x,y in [(-1,-1),(1,-1),(1,1),(-1,1),(-1,-1)]]
    rail_loops.append(loop)
    for x in (-.0014,.0014):m.stroke('Window_silver_rail',[rail_point((t+y*.0037)%1,x,.00125) for y in (-1,1)],.00015,m.SILVER,6)
    p,u,n=frame_at(rail,t,True,True);f=m.frame(p,n,u)
    m.strip('Inset_sapphire_window',f,[(-.00088,-.00065),(.00088,-.00065),(.00088,.00065),(-.00088,.00065)],.00035,.00092,gem,.00014,optics)
cut_runes(rail_obj,'Orbital_windows',rail_loops)

def jewel_clasp(name,f,sx,sy):
    outline=[(0,sy),(.73*sx,.52*sy),(sx,-.12*sy),(.43*sx,-.65*sy),(0,-sy),(-.43*sx,-.65*sy),(-sx,-.12*sy),(-.73*sx,.52*sy)]
    m.strip(name+'_forged_body',f,outline,-.0016,.0013,m.SILVER,.0003)
    m.strip(name+'_black_gasket',f,[(x*.73,y*.73) for x,y in outline],.0010,.0016,m.BLACK,.00012)
    shape=[(0,sy*.60),(sx*.51,sy*.10),(sx*.34,-sy*.35),(0,-sy*.62),(-sx*.34,-sy*.35),(-sx*.51,sy*.10)]
    verts=[m.pt(f,x*scale,y*scale,d) for scale,d in ((1.,.0014),(.75,.0027),(.28,.0034)) for x,y in shape]
    faces=[tuple(reversed(range(6))),tuple(range(12,18))]
    for j in range(2):
        for k in range(6):faces.append((j*6+k,j*6+(k+1)%6,(j+1)*6+(k+1)%6,(j+1)*6+k))
    obj=m.solid(name+'_six_facet_sapphire',verts,faces,gem,group=optics)
    for poly in obj.data.polygons:poly.use_smooth=False

# Clasps bridge the diagonal rail to the structural crescents outside the orb.
for t in (.22,.72):
    p,u,n=frame_at(rail,t,True,True);f=m.frame(p,n,u)
    jewel_clasp('Orbital_captive_clasp',f,.006,.009)
for i in range(6):
    a=math.tau*(i+.5)/6;radial=Vector((math.cos(a),math.sin(a),0));u=Vector((-math.sin(a),math.cos(a),0))
    jewel_clasp('Socket_corner_seal',m.frame(radial*.021+Vector((0,0,-.031)),radial,u),.0025,.006)

# Six independent solid spokes form an open cradle, with no paper-thin bowl.
for i in range(6):
    a=math.tau*(i+.5)/6;radial=Vector((math.cos(a),math.sin(a),0))
    def path(t,radial=radial):
        r,z=catmull([(.0275,-.110),(.026,-.121),(.018,-.132),(.0105,-.138)],t)
        return radial*r+Vector((0,0,z))
    width=lambda t:.0055*(1-.5*t)
    obj,point=ribbon('Hexagonal_cradle_spoke_'+str(i),path,width,radial=True,count=73)
    decorated_ribbon(obj,point,width,'Cradle_'+str(i),[.22,.46,.70],.058)
for z,r,w in [(-.110,.0275,.0015),(-.137,.0108,.0018)]:
    m.annulus('Cradle_structural_rim',m.frame((0,0,z),(0,0,1),(1,0,0)),r-.0013,r+.0007,-w/2,w/2,m.SILVER,count=96,bevel=.00025)
hex_loft('Six_sided_rounded_terminal',[(.0105,-.138),(.009,-.142),(.004,-.147),(.002,-.148)],m.STEEL)
for i in range(6):
    a=math.tau*(i+.5)/6;r=Vector((math.cos(a),math.sin(a),0));u=Vector((-math.sin(a),math.cos(a),0))
    f=m.frame(r*.0067+Vector((0,0,-.143)),r+Vector((0,0,-.6)),u)
    m.stroke('Heel_radial_blue_sigils',[m.pt(f,x,y,.0003) for x,y in [(-.0012,.0012),(0,.0025),(.0012,.0012),(0,-.002)]],.00014,energy,8,m.ENERGY)

def sphere(name,r,mat,group,segments=128,rings=96):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,radius=r,location=C)
    obj=bpy.context.object;obj.name=name;obj.data.materials.append(mat)
    for face in obj.data.polygons:face.use_smooth=True
    group.append(obj);return obj
sphere('Seamless_sapphire_crystal',R,glass,optics,160,112)
sphere('Blue_tidal_nebula_proxy',R*.966,volume,internals,80,56)
sphere('Star_tide_luminous_heart',.0035,core,internals,64,48)
for k in range(4):
    pts=[]
    for j in range(241):
        t=j/240;a=t*math.tau*1.65+(k%2)*math.pi
        r=(.012+.009*math.sin(math.pi*t))*(1. if k<2 else .78)
        q=Vector((r*math.cos(a),r*math.sin(a),.060*(t-.5)))
        q=Matrix.Rotation(.24 if k<2 else 1.08,3,'Y')@q
        pts.append(C+q)
    obj=m.stroke('Double_helical_mana_current_'+str(k),pts,.00014 if k<2 else .000085,filament,8,internals)
    uv=obj.data.uv_layers.new(name='UVMap')
    for poly in obj.data.polygons:
        for loop in poly.loop_indices:
            idx=obj.data.loops[loop].vertex_index;uv.data[loop].uv=(idx//8/240,idx%8/8)
for i in range(48):
    p=Vector((rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(-1,1))).normalized()*rng.uniform(.009,.034)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=rng.uniform(.00009,.00024),location=C+p)
    obj=bpy.context.object;obj.name='Contained_blue_star_'+str(i);obj.data.materials.append(sparks)
    color=obj.data.color_attributes.new(name='Color',type='BYTE_COLOR',domain='CORNER');seed=rng.random()
    for entry in color.data:entry.color=(seed,.5,.5,1)
    internals.append(obj)

bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'StarTideCore_Construction.blend'))
metal=m.join_group(m.PARTS,'StarTide_ForgedSurface');m.unwrap(metal)
start=source.index('def bake_maps(');end=source.index('\ndef finalize(',start)
bake=source[start:end].replace('T_FinalToll_','T_StarTide_').replace('M_FinalToll_PBR_Surface','M_StarTide_Metal')
exec(compile(bake,'<star_tide_4k_bake>','exec'),m.__dict__);m.bake_maps(metal)
runes=m.join_group(m.ENERGY,'StarTide_EngravedInlays');m.unwrap(runes)
final=m.join_group([metal,runes]+optics+internals,'SM_Runebound_StarTideCore_V1');final.location=(0,0,0)
final['display_name']='星潮之核';final['mount_offset_cm']=[0,0,-8.5]
for obj in list(bpy.context.scene.objects):
    if obj!=final:bpy.data.objects.remove(obj,do_unlink=True)
m.activate(final)
fbx=P/'Export'/(final.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='COPY',embed_textures=False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'StarTideCore_Editable.blend'))
final.data.calc_loop_triangles()
(P/'production_receipt.json').write_text(json.dumps({'name':'星潮之核','mesh':final.name,'fbx':str(fbx),'source':str(P/'StarTideCore_Editable.blend'),'triangles':len(final.data.loop_triangles),'materials':[mat.name for mat in final.data.materials],'pbr_resolution':4096,'normal_convention':'OpenGL tangent; flip green in UE','orb_center_cm':[0,0,-8.0],'orb_radius_cm':4.05,'mount_offset_cm':[0,0,-8.5],'interface':'native upper 2mm and original pivot retained','visual_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('STAR_TIDE_CORE_MODELED_AND_EXPORTED',flush=True)
