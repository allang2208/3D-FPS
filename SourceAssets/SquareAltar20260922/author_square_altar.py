"""Reconstruct the active gamedev square altar sprite as an editable UE prop.

No rendering or testing. The reference supplies front/top/side identity;
unseen sides repeat the matching symmetric ornament rather than inventing lore.
"""
import bpy
import json
import math
import shutil
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).parent
OUT = HERE / 'Authored'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev')
REFERENCE = SOURCE/'assets/terrain/defense_base.png'
MARBLE = SOURCE/'tools/ai-gen/_main_space_architecture_20260903/structure_review_v12_20260905/material_unify_r14/stone-albedo-raw.png'
shutil.copy2(REFERENCE, HERE/'reference_defense_base.png')
shutil.copy2(MARBLE, OUT/'T_SquareAltar_Marble.png')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1
parts=[]
materials={}


def material(name,color,roughness,metallic=0):
    mat=bpy.data.materials.new(name); mat.use_nodes=True
    p=mat.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=roughness
    p.inputs['Metallic'].default_value=metallic
    mat.diffuse_color=(*color,1)
    materials[name]=mat
    return mat


marble=material('Altar_WhiteMarble',(.87,.86,.83),.31)
edge=material('Altar_PolishedMolding',(.91,.90,.87),.23)
gold=material('Altar_SatinGold',(.67,.43,.15),.27,.92)
gem=material('Altar_BlueSapphire',(.014,.032,.24),.105,.12)
recess=material('Altar_MarbleRecess',(.66,.66,.63),.42)
image=bpy.data.images.load(str(OUT/'T_SquareAltar_Marble.png'))
for mat in (marble,edge,recess):
    n=mat.node_tree.nodes; l=mat.node_tree.links; p=n.get('Principled BSDF')
    uv=n.new('ShaderNodeTexCoord'); tex=n.new('ShaderNodeTexImage'); tex.image=image
    mix=n.new('ShaderNodeMixRGB');mix.inputs[0].default_value=.52
    mix.inputs[1].default_value=mat.diffuse_color
    l.new(uv.outputs['UV'],tex.inputs['Vector']);l.new(tex.outputs['Color'],mix.inputs[2]);l.new(mix.outputs[0],p.inputs['Base Color'])


def mesh(name,vertices,faces,mat,smooth=False):
    data=bpy.data.meshes.new(name+'_Mesh');data.from_pydata(vertices,[],faces);data.update()
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
    data.materials.append(mat)
    for face in data.polygons: face.use_smooth=smooth and len(face.vertices)==4
    parts.append(ob)
    return ob


def box(name,size,loc,mat=marble,bevel=.003):
    x,y,z=size;cx,cy,cz=loc
    vertices=[(cx+dx*x/2,cy+dy*y/2,cz+dz*z/2) for dz in (-1,1) for dx,dy in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    ob=mesh(name,vertices,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
    mod=ob.modifiers.new('Stone_edge_rounding','BEVEL');mod.width=bevel;mod.segments=3
    mod.harden_normals=True
    mod=ob.modifiers.new('Planar_normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    return ob


def frame(name,w,d,z,h,t,mat=marble,bevel=.003):
    # Four bars meet at mitred corners rather than overlapping bright faces.
    outer=[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]
    inner=[(-w/2+t,-d/2+t),(w/2-t,-d/2+t),(w/2-t,d/2-t),(-w/2+t,d/2-t)]
    verts=[(x,y,zz) for zz in (z-h/2,z+h/2) for ring in (outer,inner) for x,y in ring]
    faces=[]
    for i in range(4):
        j=(i+1)%4
        faces.extend([(i,j,j+8,i+8),(i+4,i+12,j+12,j+4),(i+8,j+8,j+12,i+12),(i,i+4,j+4,j)])
    ob=mesh(name,verts,faces,mat)
    mod=ob.modifiers.new('Mitred_molding_bevel','BEVEL');mod.width=bevel;mod.segments=3;mod.harden_normals=True
    normal=ob.modifiers.new('Molding_normals','WEIGHTED_NORMAL');normal.keep_sharp=True
    return ob


def lathe(name,xy,profile,mat=marble,n=64):
    vertices=[(xy[0]+r*math.cos(i*math.tau/n),xy[1]+r*math.sin(i*math.tau/n),z) for z,r in profile for i in range(n)]
    faces=[]
    for j in range(len(profile)-1):
        for i in range(n):
            k=j*n+i; next=j*n+(i+1)%n
            faces.append((k,next,next+n,k+n))
    faces.extend([tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))])
    return mesh(name,vertices,faces,mat,True)


def tube(name,points,radius,mat=gold,sides=7):
    points=[Vector(p) for p in points];vertices=[];faces=[]
    for i,p in enumerate(points):
        tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        reference=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
        u=tangent.cross(reference).normalized();v=tangent.cross(u).normalized()
        for j in range(sides):
            angle=j*math.tau/sides
            vertices.append(tuple(p+radius*(u*math.cos(angle)+v*math.sin(angle))))
    for i in range(len(points)-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+i for i in range(sides))])
    return mesh(name,vertices,faces,mat,True)


def surface_point(face,u,v,depth=0):
    # u horizontal on the current face; v vertical; depth points out of stone.
    if face==0:return (u,-.738-depth,v)
    if face==1:return (.838+depth,u,v)
    if face==2:return (-u,.738+depth,v)
    if face==3:return (-.838-depth,-u,v)
    return (u,v,1.298+depth)


def leaf(name,face,uv,angle,length,width,depth=.006):
    c=Vector(uv);axis=Vector((math.cos(angle),math.sin(angle)));side=Vector((-axis.y,axis.x))
    vertices=[];faces=[]
    for j in range(9):
        t=j/8;center=c+axis*length*t
        w=width*math.sin(math.pi*t)*(.85+.15*math.cos(4*math.pi*t))
        for q in (-1,0,1):
            p=center+side*q*w
            height=depth+.007*math.sin(math.pi*t)*(1-abs(q))
            vertices.append(surface_point(face,p.x,p.y,height))
    for j in range(8):
        for k in range(2):
            a=j*3+k;faces.append((a+3,a+4,a+1,a))
    ob=mesh(name,vertices,faces,gold,True)
    mod=ob.modifiers.new('Cast_leaf_thickness','SOLIDIFY');mod.thickness=.0014
    # A thin raised midrib makes the foliage read as cast metal in side light.
    mid=[surface_point(face,*(c+axis*length*t),depth+.007*math.sin(math.pi*t)+.001) for t in [0,.15,.3,.45,.6,.75,.9,1]]
    tube(name+'_Vein',mid,.0013,gold,5)


def oval(name,face,u,v,ru,rv,depth,radius=.004):
    tube(name,[surface_point(face,u+ru*math.cos(i*math.tau/64),v+rv*math.sin(i*math.tau/64),depth) for i in range(65)],radius)


def sapphire(name,face,u,v,ru,rv):
    # Closed cabochon with a faceted crown, a gold bezel and little retaining claws.
    n=32;verts=[]
    for r,d in [(1,.013),(.97,.020),(.81,.030),(.50,.037)]:
        for i in range(n):
            a=i*math.tau/n;verts.append(surface_point(face,u+ru*r*math.cos(a),v+rv*r*math.sin(a),d))
    verts.append(surface_point(face,u,v,.039));faces=[tuple(reversed(range(n)))]
    for j in range(3):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;faces.extend([(a,b,b+n),(a,b+n,a+n)])
    for i in range(n):faces.append((3*n+i,3*n+(i+1)%n,4*n))
    mesh(name,verts,faces,gem)
    oval(name+'_Bezel',face,u,v,ru+.006,rv+.006,.017,.005)
    oval(name+'_OuterSetting',face,u,v,ru+.018,rv+.014,.009,.003)
    for a in [0,math.pi/2,math.pi,3*math.pi/2]:
        p=[surface_point(face,u+(ru*r)*math.cos(a),v+(rv*r)*math.sin(a),d) for r,d in [(1.15,.014),(1.05,.025),(.91,.029)]]
        tube(name+'_Claw',p,.0028,gold,6)


# Tiered base, quiet broad body and a genuinely lowered top basin.
box('Base_Foundation',(2.2,2.0,.10),(0,0,.05),edge,.015)
box('Base_UpperStep',(2.08,1.88,.065),(0,0,.131),marble,.009)
frame('Base_GoldPinstripe',2.07,1.87,.166,.012,.016,gold,.002)
box('Base_InnerPlinth',(1.90,1.70,.07),(0,0,.198),edge,.008)
box('Altar_Core',(1.66,1.46,.885),(0,0,.6725),marble,.008)
box('Upper_Frieze',(1.78,1.58,.105),(0,0,1.14),marble,.006)
frame('Upper_Frieze_GoldSeam',1.80,1.60,1.192,.018,.020,gold,.003)
box('Upper_Cornice_Lower',(1.90,1.70,.047),(0,0,1.2195),edge,.006)
box('Upper_Cornice_Upper',(2.00,1.80,.053),(0,0,1.2695),edge,.008)
frame('Basin_OuterBorder',2.04,1.84,1.338,.124,.105,edge,.008)
frame('Basin_OuterGoldInlay',2.025,1.825,1.304,.009,.014,gold,.002)
box('Basin_LoweredBed',(1.84,1.64,.045),(0,0,1.2785),marble,.004)
frame('Basin_InnerLip',1.84,1.64,1.314,.034,.024,edge,.003)
# The long low offering ledge visible inside the reference top.
box('Offering_Ledge',(1.48,.26,.035),(0,-.35,1.3185),edge,.004)
frame('Offering_LedgeFineInlay',1.41,.20,1.338,.005,.010,gold,.001)

# Four engaged Roman corner columns; dimensions fit the original altar body.
# Closed revolved bases, convex shaft entasis and concave flutes follow the
# project's Roman-column authoring guidance, at the altar's much smaller scale.
for sx in (-1,1):
    for sy in (-1,1):
        xy=(sx*.80,sy*.70);name='Corner_%s_%s'%(sx,sy)
        box(name+'_Plinth',(.205,.205,.055),(xy[0],xy[1],.245),edge,.004)
        lathe(name+'_AtticBase',xy,[(.271,.099),(.279,.10),(.292,.092),(.303,.077),(.315,.076),(.328,.084),(.338,.082),(.346,.072)],edge)
        n=160;rings=28;z0=.342;z1=1.047;verts=[];faces=[]
        for j in range(rings+1):
            t=j/rings;base=.072*(1-.075*t+.024*math.sin(math.pi*t))
            f=min(1,t*12,(1-t)*12);f=f*f*(3-2*f)
            for i in range(n):
                phase=((i*20/n+.5)%1)-.5
                notch=math.sqrt(max(0,1-(phase/.39)**2)) if abs(phase)<.39 else 0
                r=base-.0048*notch*f;a=i*math.tau/n
                verts.append((xy[0]+r*math.cos(a),xy[1]+r*math.sin(a),z0+(z1-z0)*t))
        for j in range(rings):
            for i in range(n):
                a=j*n+i;b=j*n+(i+1)%n;faces.append((a,b,b+n,a+n))
        faces.extend([tuple(reversed(range(n))),tuple(rings*n+i for i in range(n))])
        mesh(name+'_FlutedShaft',verts,faces,marble,True)
        lathe(name+'_NeckRing',xy,[(1.039,.068),(1.045,.077),(1.054,.079),(1.062,.074)],edge)
        lathe(name+'_Capital',xy,[(1.06,.074),(1.069,.078),(1.082,.086),(1.099,.099),(1.111,.104)],edge)
        box(name+'_Abacus',(.224,.224,.036),(xy[0],xy[1],1.126),edge,.005)
        for z,r in [(.34,.077),(1.046,.079)]:
            lathe(name+'_GoldFillet',xy,[(z-.004,r-.001),(z-.002,r),(z+.003,r),(z+.004,r-.001)],gold)

# Framed lower panels and gold friezes, repeated on unseen faces symmetrically.
for face in range(4):
    span=.69 if face%2==0 else .59
    # Classical fine mouldings on the broad quiet stone face.
    for delta,radius in [(0,.0055),(.020,.003)]:
        lo=.385+delta;hi=.855-delta;w=span-.035-delta
        points=[surface_point(face,-w,lo,.002),surface_point(face,w,lo,.002),surface_point(face,w,hi,.002),surface_point(face,-w,hi,.002),surface_point(face,-w,lo,.002)]
        tube('Panel_%d_StoneFrame'%face,points,radius,edge,8)
    # Central blue medallion and mirrored scrolling acanthus to either side.
    sapphire('Frieze_%d_BlueMedallion'%face,face,0,1.014,.050,.064)
    oval('Frieze_%d_Halo'%face,face,0,1.014,.084,.087,.011,.0038)
    for sign in (-1,1):
        end=span-.025
        points=[]
        for i in range(65):
            t=i/64;u=sign*(.10+(end-.10)*t);v=1.014+.018*math.sin(t*math.tau*1.5)
            points.append(surface_point(face,u,v,.010))
        tube('Frieze_%d_Vine'%face,points,.0037)
        for k in range(4):
            u=sign*(.15+k*(end-.21)/3)
            for side in (-1,1):
                angle=math.atan2(side*.9,sign*.62)
                leaf('Frieze_%d_Acanthus'%face,face,(u,1.014),angle,.061,.017)
        for k in range(3):
            cx=sign*(.20+k*(end-.27)/2);cy=1.022
            points=[]
            for i in range(65):
                t=i/64;a=-math.pi/2+t*math.tau*1.25;r=.042*(1-.90*t)
                points.append(surface_point(face,cx+sign*r*math.cos(a),cy+r*math.sin(a),.012))
            tube('Frieze_%d_CScroll'%face,points,.0038)
    # Small gilded corner rosettes continue the restrained lower detail.
    for side in (-1,1):
        u=side*(span-.06)
        for a in range(6):leaf('Panel_%d_Rosette'%face,face,(u,.405),a*math.tau/6,.027,.009,.005)

# Fine gold bead band below the projecting rim, with real rounded beads.
for face in range(4):
    span=.82 if face%2==0 else .72
    tube('Cornice_%d_GoldBeadRail'%face,[surface_point(face,-span,1.187,.060),surface_point(face,span,1.187,.060)],.0035)
    for k in range(39 if face%2==0 else 35):
        u=-span+2*span*k/(38 if face%2==0 else 34)
        # Short U-shaped links avoid hundreds of separate spherical assets.
        tube('Cornice_%d_Bead'%face,[surface_point(face,u+.0035*math.cos(a),1.187+.0035*math.sin(a),.063) for a in [i*math.tau/10 for i in range(11)]],.002,gold,5)

# The top border retains small gold corner leaves and the single blue centre
# accent from the reference; no added glow or detached particles.
for sx in (-1,1):
    for sy in (-1,1):
        for a in range(3):
            leaf('TopCorner_Leaf',4,(sx*.970,sy*.870),math.atan2(-sy,-sx)+(a-1)*.45,.048,.013,.103)
sapphire('Top_RearBlueOval',4,0,.70,.061,.037)
for sign in (-1,1):
    for k in range(4):
        leaf('TopRear_Foliage',4,(sign*(.11+k*.12),.70),math.atan2(.5,sign),.075,.020,.009)

# Source is saved as independent editable meshes. Apply geometric modifiers
# for FBX; assign physical UVs before export and keep hard plane normals.
bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get()
for ob in parts:
    evaluated=ob.evaluated_get(deps)
    data=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=deps)
    ob.modifiers.clear();ob.data=data
    uv=data.uv_layers.new(name='PhysicalStoneUV')
    for poly in data.polygons:
        axis=max(range(3),key=lambda i:abs(poly.normal[i]));a,b=((1,2),(0,2),(0,1))[axis]
        for li in poly.loop_indices:
            p=data.vertices[data.loops[li].vertex_index].co
            uv.data[li].uv=(p[a]/1.8,p[b]/1.8)
    data.update()
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SquareAltar.blend'))
bpy.ops.object.select_all(action='SELECT');bpy.context.view_layer.objects.active=parts[0]
bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_SquareAltar'
tri=ob.modifiers.new('FBX_Triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
fbx=OUT/'SM_SquareAltar.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,
    mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False)
report=dict(source_reference=str(REFERENCE),geometry='reference-based reconstruction, unseen sides symmetric',
    intended_dimensions_cm=[220,200,140],column_count=4,flutes_per_column=20,
    fbx=str(fbx),blend=str(OUT/'SquareAltar.blend'),triangles=len(ob.data.polygons),
    materials=[m.name for m in ob.data.materials],rendered=False,runtime_tested=False)
(HERE/'authoring_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('SQUARE_ALTAR_AUTHORED',json.dumps(report))
