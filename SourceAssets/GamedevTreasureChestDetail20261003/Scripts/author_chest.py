"""Author the next detailed treasure, preserving the original rigid hinge rig.

Helper recipes are inherited from the local accepted source; no preview/test.
All dimensions below use its pre-map cm coordinates (0.65 source scale).
"""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

HERE=Path(__file__).resolve().parents[1]
PROJECT=HERE.parents[1]
OUT=HERE/'Authored'; OUT.mkdir(parents=True,exist_ok=True)
# The adopted helper snapshot is local to this revision. The superseded
# coarse authoring package can be archived without becoming a dependency.
helper=HERE/'Scripts/geometry_helpers.py'
exec(compile(helper.read_text(encoding='utf-8'),str(helper),'exec'))

# Replace finish: consistently authored edge normals, physical UV0, and a second
# UV for geometric edge wear. Color R=bevel, G/B=face dimensions / 200 cm.
def finish(obj,name,mat,bone='Root',bevel=0):
    obj.name=name
    if not obj.data.materials: obj.data.materials.append(materials[mat])
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    if bevel:
        mod=obj.modifiers.new('RoundedMachinedEdges','BEVEL')
        mod.width=bevel;mod.segments=4;mod.limit_method='ANGLE'
        mod.angle_limit=math.radians(35);mod.use_clamp_overlap=True
        mod.harden_normals=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for f in obj.data.polygons:f.use_smooth=True
        norm=obj.modifiers.new('WeightedFaceNormals','WEIGHTED_NORMAL')
        norm.keep_sharp=True;norm.weight=50
        bpy.ops.object.modifier_apply(modifier=norm.name)
    obj.data.transform(mapping @ obj.matrix_world)
    obj.matrix_world=Matrix.Identity(4);obj.data.update()
    uv=obj.data.uv_layers.get('UV0_Physical') or obj.data.uv_layers.new(name='UV0_Physical')
    wearuv=obj.data.uv_layers.new(name='UV1_ComponentWear')
    colors=obj.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    mins=[min(v.co[i] for v in obj.data.vertices) for i in range(3)]
    maxs=[max(v.co[i] for v in obj.data.vertices) for i in range(3)]
    spans=[max(maxs[i]-mins[i],.001) for i in range(3)]
    # Decor pieces get distinct sampling offsets, all independent of actor motion.
    seed=sum((i+1)*ord(c) for i,c in enumerate(name))
    offset=((seed%997)/137.,((seed//11)%991)/151.)
    for face in obj.data.polygons:
        axis=max(range(3),key=lambda i:abs(face.normal[i]))
        axes=((1,2),(0,2),(0,1))[axis]
        bevelmask=.72 if bevel and max(abs(n) for n in face.normal)<.995 else 0.
        for li in face.loop_indices:
            p=obj.data.vertices[obj.data.loops[li].vertex_index].co
            uv.data[li].uv=(p[axes[0]]/100+offset[0],p[axes[1]]/100+offset[1])
            wearuv.data[li].uv=((p[axes[0]]-mins[axes[0]])/spans[axes[0]],
                                (p[axes[1]]-mins[axes[1]])/spans[axes[1]])
            colors.data[li].color=(bevelmask,min(1,spans[axes[0]]/200),min(1,spans[axes[1]]/200),1)
    group=obj.vertex_groups.new(name=bone)
    group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    obj.select_set(False);parts.append(obj)
    pieces.append(dict(name=name,bone=bone,material=names[mat],vertices=len(obj.data.vertices)))
    return obj

_original_arch_shell=arch_shell
def arch_shell(name,x0,x1,outer_r,outer_h,inner_r,inner_h,outer_mat=IRON,inner_mat=INNER):
    ob=_original_arch_shell(name,x0,x1,outer_r,outer_h,inner_r,inner_h,outer_mat,inner_mat)
    # Continuous physical unwrap across the vault: no dominant-axis jumps in
    # the middle of the visible curved metal or dark wood inner surface.
    uv=ob.data.uv_layers.get('UV0_Physical');wearuv=ob.data.uv_layers.get('UV1_ComponentWear')
    colors=ob.data.color_attributes.get('Color');inv=mapping.inverted()
    arc_length=math.pi*(outer_r+outer_h)*.5*.65
    for f in ob.data.polygons:
        f.use_smooth=abs(f.normal.y)<.999
        for li in f.loop_indices:
            p=inv@ob.data.vertices[ob.data.loops[li].vertex_index].co
            theta=math.atan2(max(0,p.z-99)/outer_h,-p.y/outer_r)
            uv.data[li].uv=(p.x*.65/100,theta/math.pi*arc_length/100)
            wearuv.data[li].uv=((p.x-x0)/(x1-x0),theta/math.pi)
            colors.data[li].color=(0,min(1,(x1-x0)*.65/200),min(1,arc_length/200),1)
    return ob

def rivet(name,loc,radius=.98,bone='Root',axis='Y',mat=GOLD):
    # Low dome, seated with a narrow washer: no floating spheres.
    # Allocate the small washer's tessellation to its visible chamfer, rather
    # than inheriting the large hinge cylinder's four-segment bevel everywhere.
    n=16;verts=[]
    for r,d in ((radius*1.10,-.15),(radius*1.18,-.075),(radius*1.18,.075),(radius*1.10,.15)):
        for i in range(n):
            a=2*math.pi*i/n;u,v=r*math.cos(a),r*math.sin(a)
            delta={'X':(d,u,v),'Y':(u,d,v),'Z':(u,v,d)}[axis]
            verts.append(tuple(loc[k]+delta[k] for k in range(3)))
    faces=[tuple(range(n-1,-1,-1)),tuple(range(3*n,4*n))]
    faces += [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(3) for i in range(n)]
    seat=raw(name+'_Seat',verts,faces,[mat]*len(faces),bone,smooth=True)
    seat.data.polygons[0].use_smooth=False;seat.data.polygons[1].use_smooth=False
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1,location=loc)
    ob=bpy.context.object
    ob.scale={'X':(.38,radius,radius),'Y':(radius,.38,radius),'Z':(radius,radius,.38)}[axis]
    for f in ob.data.polygons:f.use_smooth=True
    return finish(ob,name,mat,bone)

def path_tube(name,points,radius=.65,bone='Root',mat=GOLD):
    # Existing closed curve recipe, endpoints buried in the support plate.
    return curve(name,points,radius,mat,bone,cap_studs=False)

def relief_leaf(name,mode,fixed,cu,cv,angle,length=13,width=4,bone='Root',mat=GOLD):
    # A lenticular leaf, curved silhouette and raised centre vein, with thickness.
    ca,sa=math.cos(angle),math.sin(angle)
    n=14;verts=[]
    for side in (-1,0,1):
        for j in range(n+1):
            t=j/n;u=side*width*math.sin(math.pi*t)**.8
            v=length*t;uu=ca*u-sa*v+cu;vv=sa*u+ca*v+cv
            depth=.35+(.9 if side==0 else .08)*math.sin(math.pi*t)
            if mode=='front':verts.append((uu,fixed-depth,vv))
            elif mode=='back':verts.append((uu,fixed+depth,vv))
            else:verts.append((fixed-depth if mode=='left' else fixed+depth,uu,vv))
    faces=[]
    for i in range(2):
        for j in range(n):
            a=i*(n+1)+j;b=a+n+1
            faces.append((a,a+1,b+1,b))
    # Solid leaf shell: give the back a real 0.25 cm thickness.
    front_count=len(verts)
    for co in verts[:]:
        p=list(co);p[1 if mode in ('front','back') else 0]+= .25 if mode in ('front','left') else -.25
        verts.append(tuple(p))
    frontfaces=list(faces)
    faces += [tuple(front_count+k for k in reversed(f)) for f in frontfaces]
    boundary=[(a,b) for f in frontfaces for a,b in zip(f,f[1:]+f[:1])]
    counts={}
    for a,b in boundary:counts[tuple(sorted((a,b)))]=counts.get(tuple(sorted((a,b))),0)+1
    for a,b in boundary:
        if counts[tuple(sorted((a,b)))]==1:faces.append((a,b,b+front_count,a+front_count))
    ob=raw(name,verts,faces,[mat]*len(faces),bone,smooth=True)
    # Collapse the shared leaf tip coordinates as part of constructing a solid
    # embossed leaf; retain UV/color/weight layers through the mesh operation.
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    return ob

def scroll_panel(tag,mode,fixed,cu,cv,size=1,mat=GOLD):
    def co(x,z):
        x=cu+x*size;z=cv+z*size
        if mode=='front':return (x,fixed-.62,z)
        if mode=='back':return (x,fixed+.62,z)
        return (fixed-.62 if mode=='left' else fixed+.62,x,z)
    for s in (-1,1):
        path_tube(tag+'_Scroll_'+str(s),[co(s*x,z) for x,z in [(0,-10),(8,-7),(13,0),(12,8),(6,10),(3,6),(7,3),(9,5)]],.72*size,mat=mat)
        path_tube(tag+'_Tendril_'+str(s),[co(s*x,z) for x,z in [(1,-8),(6,-2),(3,5),(0,12)]],.47*size,mat=mat)
        relief_leaf(tag+'_Leaf_'+str(s),mode,fixed,cu+s*5*size,cv-8*size,
                    -s*.65,10*size,3*size,mat=mat)
    relief_leaf(tag+'_CentreLeaf',mode,fixed,cu,cv-4*size,0,18*size,3.5*size,mat=mat)

# BODY: existing external size, real open cavity, joined bottom / side plates.
box('Body_Floor',(0,0,17.4),(190,142,6.8),IRON,bevel=1.35)
for s in (-1,1):
    box('Body_FB_'+str(s),(0,s*68,55),(190,6,74),IRON,bevel=1.15)
    box('Body_Side_'+str(s),(s*92,0,55),(6,130,74),IRON,bevel=1.15)
    # Individual lining panels meet the cavity walls; keep top open.
    for j,x in enumerate((-66,-22,22,66)):
        box('Inner_WallBoard_FB_%s_%s'%(s,j),(x,s*64.5,56.5),(43.65,1.6,67),INNER,bevel=.25)
    for j,y in enumerate((-42.4,0,42.4)):
        box('Inner_WallBoard_Side_%s_%s'%(s,j),(s*88.3,y,56.5),(1.6,42.1,67),INNER,bevel=.25)
# Seven separate bottom planks: narrow dark joints, no suspended interior plane.
for j in range(7):
    y=-54.9+j*18.3
    box('Interior_FloorPlank_'+str(j),(0,y,22.3),(174.8,17.95,3.2),INNER,bevel=.3)
    for x in (-78,78):rivet('Interior_FloorNail_%s_%s'%(j,x),(x,y,23.99),.53,axis='Z',mat=IRON)

# Actual continuous L angle sections, matching the original frame footprint.
front_rim=[(-75,84),(-75,96),(-64,96),(-64,92),(-71,92),(-71,84)]
front_base=[(-76,14),(-76,26),(-72,26),(-72,18),(-62,18),(-62,14)]
band_yz('Rim_Front',front_rim);band_yz('Rim_Back',[(-y,z) for y,z in front_rim])
band_yz('Base_Front',front_base);band_yz('Base_Back',[(-y,z) for y,z in front_base])
side_rim=[(95,84),(99,84),(99,96),(89,96),(89,92),(95,92)]
side_base=[(88,14),(99,14),(99,26),(95,26),(95,18),(88,18)]
for s in (-1,1):
    band_xz('Rim_Side_'+str(s),[(s*x,z) for x,z in side_rim])
    band_xz('Base_Side_'+str(s),[(s*x,z) for x,z in side_base])
corner=[(92,-76),(100,-76),(100,-64),(96,-64),(96,-72),(92,-72)]
for sx in (-1,1):
    for sy in (-1,1):
        # Preserve perimeter order, including the concave corner of the L.
        prof=[(sx*x,sy*y) for x,y in corner]
        band_xy('Corner_Post_%s_%s'%(sx,sy),prof,0,92)
        band_xy('Corner_Toe_%s_%s'%(sx,sy),[(x*1.035,y*1.035) for x,y in prof],0,4)
        for z in (12,34,56,78,88):
            rivet('CornerFront_%s_%s_%s'%(sx,sy,z),(sx*96,sy*76.1,z))
            rivet('CornerSide_%s_%s_%s'%(sx,sy,z),(sx*100.1,sy*68,z),axis='X')
for s in (-1,1):
    for z in (20,90):
        for x in (-82,-58,-34,-10,14,38,62,86):
            rivet('FrameRivet_%s_%s_%s'%(s,z,x),(x,s*75.4,z))
    for x in (-38,38):
        box('PanelStile_%s_%s'%(s,x),(x,s*72,55),(4.5,3,62),GOLD,bevel=.65)
    # Raised black metal inset panel + double thin bevelled trim, two distinct depths.
    for k,(a,b) in enumerate(((-89,-43),(-33,33),(43,89))):
        box('InsetPanel_%s_%s'%(s,k),((a+b)/2,s*71.05,55),(b-a,1.3,48),IRON,bevel=.6)
        for z in (30.5,79.5):box('PanelBorderH_%s_%s_%s'%(s,k,z),((a+b)/2,s*72.0,z),(b-a+1.5,1.15,1.5),GOLD,bevel=.25)
        for x in (a,b):box('PanelBorderV_%s_%s_%s'%(s,k,x),(x,s*72.0,55),(1.5,1.15,50),GOLD,bevel=.25)
    for x in (-66,66):scroll_panel('Scroll_FB_%s_%s'%(s,x),'front' if s<0 else 'back',s*72.1,x,55,.95,GOLD if s<0 else IRON)
for s in (-1,1):
    for y in (-43,43):scroll_panel('Scroll_Side_%s_%s'%(s,y),'left' if s<0 else 'right',s*95.0,y,55,.67,IRON)

# Interior hardware: split corner angle brackets, visible fasteners, upper lining edging.
for sx in (-1,1):
    for sy in (-1,1):
        box('Inside_Corner_FB_%s_%s'%(sx,sy),(sx*84.8,sy*63.3,56),(5.2,1.0,62),GOLD,bevel=.2)
        box('Inside_Corner_Side_%s_%s'%(sx,sy),(sx*87.0,sy*61.2,56),(1.0,5.2,62),GOLD,bevel=.2)
        for z in (29,56,83):
            rivet('InsideRivet_FB_%s_%s_%s'%(sx,sy,z),(sx*84.8,sy*62.7,z),.68,axis='Y',mat=IRON)
            rivet('InsideRivet_S_%s_%s_%s'%(sx,sy,z),(sx*86.4,sy*61.2,z),.68,axis='X',mat=IRON)
for s in (-1,1):
    box('Inner_Rim_FB_'+str(s),(0,s*63.1,88.5),(172,1,2.3),GOLD,bevel=.25)
    box('Inner_Rim_S_'+str(s),(s*86.5,0,88.5),(1,125,2.3),GOLD,bevel=.25)

# LOCK: contoured metal plate with actual recessed key opening.
shield=[(0,-18),(6,-15),(11,-10),(14,-4),(13,5),(9,11),(4,13),(0,13.7),(-4,13),(-9,11),(-13,5),(-14,-4),(-11,-10),(-6,-15)]
lock=prism('Lock_Escutcheon',shield,'front',-72.1,0,57,3.5,0,GOLD,bevel=.55)
# Boolean cutters are in mapped space, so the hole is cut right through the plate.
cutters=[]
for typ,loc,size in [('round',(0,-75,60),(2.2,9)),('stem',(0,-75,55.8),(2.45,9,6.8))]:
    if typ=='round':
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=size[0],depth=size[1],location=loc)
        cut=bpy.context.object;cut.rotation_euler.x=math.pi/2
    else:
        bpy.ops.mesh.primitive_cube_add(size=1,location=loc);cut=bpy.context.object;cut.dimensions=size
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    cut.data.transform(mapping@cut.matrix_world);cut.matrix_world=Matrix.Identity(4)
    bpy.context.view_layer.objects.active=lock
    mod=lock.modifiers.new('Cut_Keyhole_'+typ,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
# Cavity stays dark behind the opening, without a protruding painted dot.
box('Lock_KeyholeCavity',(0,-72.25,57),(6,.7,15),IRON,bevel=.25)
for x,z in ((-8,61),(8,61),(-6,48),(6,48)):
    rivet('Lock_Rivet_%s_%s'%(x,z),(x,-75.85,z),.83)
for s in (-1,1):scroll_panel('Lock_FineScroll_'+str(s),'front',-75.55,s*7.8,53.6,.27,GOLD)

# SIDE HANDLES: two real spindle seats per bail, rounded U profile and grip sleeve.
for s in (-1,1):
    for y in (-23,23):
        box('Handle_LugPlate_%s_%s'%(s,y),(s*95.2,y,62),(1.7,10,16),GOLD,bevel=.9)
        cylinder('Handle_Seat_%s_%s'%(s,y),(s*98,y,62),3.6,6,GOLD,axis='X',bevel=.35)
        cylinder('Handle_Spindle_%s_%s'%(s,y),(s*101,y,62),1.4,6,IRON,axis='X',bevel=.25)
        for z in (57,67):rivet('Handle_LugRivet_%s_%s_%s'%(s,y,z),(s*96.1,y,z),.75,axis='X')
    path_tube('Handle_Bail_'+str(s),[(s*102,-23,62),(s*104,-23,45),(s*104,-18,40),(s*104,18,40),(s*104,23,45),(s*102,23,62)],1.9)
    cylinder('Handle_Grip_'+str(s),(s*104,0,40),2.2,28,IRON,axis='Y',bevel=.35)
    for y in (-15,15):cylinder('Handle_Collar_%s_%s'%(s,y),(s*104,y,40),2.35,1.2,GOLD,axis='Y',bevel=.2)

# HINGE: original rear pivot (y=76,z=99). Interleaved moving/fixed knuckles.
for x in (-62,62):
    box('Hinge_FixedLeaf_'+str(x),(x,74.7,84),(23.6,2.2,22),GOLD,bevel=.6)
    box('Hinge_MovingLeaf_'+str(x),(x,74.7,108.5),(23.6,2.2,19),GOLD,'Lid',bevel=.6)
    cylinder('Hinge_Axle_'+str(x),(x,76,99),1.55,29,IRON,axis='X',bevel=.18)
    for i in range(5):
        xx=x+(i-2)*5.25
        cylinder('Hinge_Knuckle_%s_%s'%(x,i),(xx,76,99),3.65,4.9,GOLD,'Lid' if i%2 else 'Root',axis='X',bevel=.25)
    for xx in (x-15,x+15):cylinder('Hinge_PinCap_%s_%s'%(x,xx),(xx,76,99),2.2,1.3,GOLD,axis='X',bevel=.3)
    for xx in (x-7,x+7):
        for z in (78,89):rivet('Hinge_FixedRivet_%s_%s'%(xx,z),(xx,76.0,z),.9)
        for z in (105,113):rivet('Hinge_MovingRivet_%s_%s'%(xx,z),(xx,76.0,z),.9,'Lid')

# LID: segmented shell, continuous inner surface, no flat lid plug.
arch_shell('Lid_MainVault',-101,101,74,58,69.5,53.5,IRON,INNER)
end_panel('Lid_EndLeft',-101,-97.5);end_panel('Lid_EndRight',97.5,101)
for index,x in enumerate((-66,66)):
    arch_shell('Lid_OuterStrap_'+str(index),x-5.4,x+5.4,76.2,60.2,73.9,57.9,GOLD,GOLD)
    # Twin fine rolled strap edges.
    for dx in (-4.5,4.5):arch_shell('Lid_StrappedEdge_%s_%s'%(index,dx),x+dx-.45,x+dx+.45,76.5,60.5,76.05,60.05,GOLD,GOLD)
    for deg in (16,40,64,90,116,140,164):
        t=math.radians(deg)
        for dx in (-3.0,3.0):
            # Dome is aligned to the ellipse normal before the inherited mapping.
            loc=(x+dx,-76.3*math.cos(t),99+60.3*math.sin(t))
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1,location=loc)
            ob=bpy.context.object;ob.scale=(.87,.87,.42)
            n=Vector((0,-math.cos(t)/76.2,math.sin(t)/60.2)).normalized()
            ob.rotation_euler=Vector((0,0,1)).rotation_difference(n).to_euler()
            for f in ob.data.polygons:f.use_smooth=True
            finish(ob,'Lid_StrapDome_%s_%s_%s'%(index,deg,dx),GOLD,'Lid')
for s in (-1,1):
    cylinder('Lid_EdgeRoll_'+str(s),(0,s*75.5,100),3.7,207,GOLD,'Lid',axis='X',bevel=.25)
    arch_shell('Lid_EndRim_'+str(s),s*102.2-3.4,s*102.2+3.4,76.3,60.3,72.8,56.8,GOLD,GOLD)
    path_tube('Lid_EndScroll_'+str(s),[(s*102,-35,111),(s*102,-23,127),(s*102,0,137),(s*102,22,126),(s*102,10,115),(s*102,-4,121),(s*102,-12,127)],1.1,'Lid')

# Visible dark wood ribs seated against the vault inner wall, and gold rib ends.
for i,x in enumerate((-82,-27,27,82)):
    arch_shell('Lid_InnerRib_'+str(i),x-1.6,x+1.6,69.45,53.45,66.9,50.9,INNER,INNER)
    for s in (-1,1):
        box('Lid_InnerRibShoe_%s_%s'%(i,s),(x,s*67.4,102.4),(6,4.2,5.3),GOLD,'Lid',bevel=.35)
        rivet('Lid_InnerRibScrew_%s_%s'%(i,s),(x,s*65.0,102.4),.7,'Lid',mat=IRON)
for s in (-1,1):
    box('Lid_InnerEdge_'+str(s),(0,s*68.4,99.8),(190,2.2,2.8),INNER,'Lid',bevel=.3)

# Moving hasp fits the fixed lock plate and stays entirely on Lid.
hasp=[(-75.5,101),(-80,77),(-78.2,75),(-73.5,99.5)]
verts=[(x,y,z) for x in (-5.3,5.3) for y,z in hasp]
faces=[(3,2,1,0),(4,5,6,7)]+[(i,(i+1)%4,(i+1)%4+4,i+4) for i in range(4)]
raw('Lid_Hasp',verts,faces,[GOLD]*6,'Lid',smooth=False,bevel=.55)
cylinder('Lid_HaspPin',(0,-75.5,100),2.35,14,IRON,'Lid',axis='X',bevel=.3)
cylinder('Hasp_EndDisc',(0,-79.3,77),4.7,2.2,GOLD,'Lid',axis='Y',bevel=.4)
rivet('Hasp_EndRivet',(0,-80.8,77),1.05,'Lid')

# Rosette: all its rings, carved leaves and fine beads are Lid-bound.
cylinder('Lid_MedallionBase',(0,0,155.8),25.8,4.3,GOLD,'Lid',bevel=.5)
ring('Lid_MedallionSkirt',(0,0,154.0),25.6,1.25,GOLD,'Lid')
ring('Lid_MedallionBorder',(0,0,159.2),21,1.65,GOLD,'Lid')
ring('Lid_MedallionInnerBorder',(0,0,159.1),15.7,.65,GOLD,'Lid')
for i in range(12):
    a=2*math.pi*i/12;ca,sa=math.cos(a),math.sin(a)
    prof=[(21,-1.4),(26,-.8),(26,.8),(21,1.4)]
    prism('Lid_MedallionRay_'+str(i),[(ca*u-sa*v,sa*u+ca*v) for u,v in prof],'flat',157.8,0,0,1.7,0,GOLD,'Lid',bevel=.3)
    stud('Lid_MedallionBead_'+str(i),(23.3*math.cos(a+math.pi/12),23.3*math.sin(a+math.pi/12),159.2),.75,GOLD,'Lid',squash=.5)
for i in range(8):
    a=2*math.pi*i/8
    # Solid petal with a subtle longitudinal crease, lying on the medallion.
    ob=relief_leaf('Lid_MedallionPetal_'+str(i),'front',0,0,0,a,12,3.2,'Lid')
    # Author leaf in its own local XY plane at the crown; apply source-space map.
    inv=mapping.inverted()
    transform=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,159.3),(0,0,0,1)))
    ob.data.transform(mapping@transform@inv);ob.data.update()
stud('Lid_MedallionCore',(0,0,161.0),4.7,GOLD,'Lid',squash=.45)

# Update final per-piece normals/UV0 affected by keyhole edits and petal rotation.
# UV1 stays authored in component coordinates and follows the moving lid.
for ob in parts:
    if ob.name.startswith('Lock_Escutcheon') or ob.name.startswith('Lid_MedallionPetal'):
        uv=ob.data.uv_layers.get('UV0_Physical')
        for f in ob.data.polygons:
            axis=max(range(3),key=lambda i:abs(f.normal[i]));axes=((1,2),(0,2),(0,1))[axis]
            for li in f.loop_indices:
                p=ob.data.vertices[ob.data.loops[li].vertex_index].co
                uv.data[li].uv=(p[axes[0]]/100,p[axes[1]]/100)

# Save editable components before combining into one skeletal runtime component.
for ob in parts:
    # Boolean cut faces can append an empty cutter slot. Capture each face's
    # semantic material before clearing, then explicitly restore three slots.
    old=list(ob.data.materials)
    ids=[names.index(old[f.material_index].name.split('.')[0])
         if f.material_index<len(old) and old[f.material_index] and old[f.material_index].name.split('.')[0] in names
         else IRON for f in ob.data.polygons]
    ob.data.materials.clear()
    for m in materials:ob.data.materials.append(m)
    for f,i in zip(ob.data.polygons,ids):f.material_index=i
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True)
bpy.context.view_layer.objects.active=arm
for ob in parts:
    ob.parent=arm;mod=ob.modifiers.new('OriginalRigidHinge','ARMATURE');mod.object=arm
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TreasureChest_Detail_Components.blend'))
for ob in parts:
    ob.modifiers.clear();ob.parent=None;ob.select_set(True)
arm.select_set(False);bpy.context.view_layer.objects.active=parts[0]
bpy.ops.object.join();mesh=bpy.context.object;mesh.name='SK_GamedevTreasureChest'
tri=mesh.modifiers.new('ExportTriangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
mesh.parent=arm;mod=mesh.modifiers.new('OriginalRigidHinge','ARMATURE');mod.object=arm
lid=arm.pose.bones['Lid'];lid.rotation_mode='QUATERNION'
axis=arm.data.bones['Lid'].matrix_local.to_3x3().inverted()@Vector((0,1,0))
def selection():
    bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);arm.select_set(True)
    bpy.context.view_layer.objects.active=arm
def export(name,static=False):
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,
        object_types={'MESH'} if static else {'MESH','ARMATURE'},apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',
        mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,use_tspace=True,
        use_mesh_modifiers=True,use_custom_props=False,colors_type='LINEAR')
selection();export('SK_GamedevTreasureChest')
for name,angle in [('SM_TreasureChest_Closed',0),('SM_TreasureChest_Open',-58)]:
    lid.rotation_quaternion=Quaternion(axis,math.radians(angle));bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get();data=bpy.data.meshes.new_from_object(mesh.evaluated_get(dg),depsgraph=dg)
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    export(name,True);bpy.data.objects.remove(ob,do_unlink=True)
lid.rotation_quaternion=Quaternion();selection();scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TreasureChest_Detail.blend'))
# Preserve the exact original action in the editable source, rather than approximate it.
with bpy.data.libraries.load(str(PROJECT/'SourceAssets/GamedevTreasureChest20260922/Authored/GamedevTreasureChest_Opening.blend'),link=False) as (src,dst):
    dst.actions=['A_TreasureChest_Opening']
arm.animation_data_create();arm.animation_data.action=dst.actions[0]
if dst.actions[0].slots:arm.animation_data.action_slot=dst.actions[0].slots[0]
scene.frame_start=1;scene.frame_end=31;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TreasureChest_Detail_Opening.blend'))
record=dict(revision='Detailed20261003',parts=pieces,triangles=len(mesh.data.polygons),
            material_slots=[m.name for m in mesh.data.materials],
            rig=[dict(name=b.name,head=list(b.head_local),tail=list(b.tail_local)) for b in arm.data.bones],
            source_scale=.65,unit='cm',uv0='physical one-meter texture space',
            uv1='component edge coordinates',color='R bevel, GB physical face size /200 cm',
            original_skeleton_and_animation_preserved=True,rendered=False,tested=False)
(HERE/'Receipts').mkdir(exist_ok=True)
(HERE/'Receipts/authoring.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('TREASURE_DETAIL_AUTHORED triangles='+str(record['triangles']))
