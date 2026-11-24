"""Build the Eclipse cosmetic frame from traced side-view curves on the production bow rig.
Curve coordinates below are pixels of EclipseFrameConceptR1's 1536 x 1024 art.
The existing grip, accessory seats and moving assembly define the mating surfaces.
"""
from pathlib import Path
import math
import bpy, bmesh
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

src=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(src.parent/'RigContactR2/FrontierCompoundBow_R2.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
rig=scene.objects['Armature']
rig.data.pose_position='REST'
scene.frame_set(1)
shell=scene.objects['Riser']
hardware=[scene.objects[k] for k in ('UpperLimb','LowerLimb','UpperCam','LowerCam','ControlCable1','ControlCable2')]
finish=bpy.data.materials.new('M_Eclipse_Frame')
finish.use_nodes=True
nodes=finish.node_tree.nodes
links=finish.node_tree.links
shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
for suffix in ('Color','ORM','Normal'):
    image=bpy.data.images.load(str(src/'Textures'/f'T_Eclipse_{suffix}.png'))
    if suffix!='Color':image.colorspace_settings.name='Non-Color'
    tex=nodes.new('ShaderNodeTexImage');tex.image=image
    if suffix=='Color':links.new(tex.outputs['Color'],shader.inputs['Base Color'])
    if suffix=='ORM':
        sep=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],sep.inputs[0])
        links.new(sep.outputs['Green'],shader.inputs['Roughness']);links.new(sep.outputs['Blue'],shader.inputs['Metallic'])
    if suffix=='Normal':
        split=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs[0],split.inputs[0])
        invert=nodes.new('ShaderNodeMath');invert.operation='SUBTRACT';invert.inputs[0].default_value=1;links.new(split.outputs['Green'],invert.inputs[1])
        rgb=nodes.new('ShaderNodeCombineColor')
        for label,n in [('Red',split.outputs['Red']),('Green',invert.outputs[0]),('Blue',split.outputs['Blue'])]:links.new(n,rgb.inputs[label])
        normal=nodes.new('ShaderNodeNormalMap');links.new(rgb.outputs[0],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])

# Remove only the old webs. Retain limb pocket, grip collars, stabilizer boss,
# arrow guide and the outside of the original optic shoe.
bm=bmesh.new();bm.from_mesh(shell.data)
for axis,levels in [(2,[-28.8,-23.6,-9.15,6.04,13.92,15.9,33.9,39.3]),(0,[-3.7,2.1,8.55]),(1,[1.18])]:
    direction=Vector((0,0,0));direction[axis]=1
    for value in levels:
        bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],
            plane_co=direction*value,plane_no=direction,dist=.00001)
def remove(c):
    x,y,z=c
    trim_upper=6.04<z<39.3 and x> -3.7 and (z<33.9 or x<8.55)
    trim_lower=-28.8<z< -9.15 and (z> -23.6 or x<8.55)
    return trim_upper or trim_lower
bmesh.ops.delete(bm,geom=[p for p in bm.faces if remove(p.calc_center_median())],context='FACES')
bm.to_mesh(shell.data);bm.free()

def trace(start,*curves):
    """Cubic Bezier segments. Samples retain precise tips and intentional corners."""
    pts=[Vector(start)]
    for control in curves:
        a=pts[-1];b,c,d=(Vector(control[i:i+2]) for i in (0,2,4))
        count=max(3,math.ceil(((b-a).length+(c-b).length+(d-c).length)/5.0))
        for k in range(1,count+1):
            t=k/count;u=1-t
            pts.append(a*u**3+b*(3*t*u*u)+c*(3*t*t*u)+d*t**3)
    return pts
def shape(start,*curves):
    pts=trace(start,*curves)
    if (pts[0]-pts[-1]).length<.01:pts.pop()
    return pts
upper=shape((275,205),(281,196,315,181,337,179),(351,206,382,224,397,250),
    (419,273,431,302,423,337),(419,365,399,392,398,424),(397,445,405,456,408,462),
    (405,473,405,488,404,501),(390,503,363,502,344,503),(344,487,348,464,347,442),
    (346,409,342,379,343,356),(341,325,328,295,309,266),(296,249,286,233,275,223),(274,217,273,211,275,205))
eye=shape((349,260),(360,253,379,267,385,285),(394,311,379,336,362,348),
    (365,339,366,328,373,320),(357,318,343,311,339,301),(335,289,338,268,349,260))
upper_window=shape((395,348),(405,372,386,395,386,422),(385,423,384,424,383,422),
    (375,413,367,401,367,391),(365,376,384,355,395,348))
small_window=shape((373,424),(379,427,388,447,388,464),(389,476,385,484,380,482),
    (370,479,366,466,366,452),(365,441,368,428,373,424))
lower=shape((369,619),(382,621,402,626,418,619),(421,639,423,658,417,681),
    (413,703,396,733,384,758),(373,780,363,804,355,813),(333,820,305,814,276,797),
    (278,785,288,774,298,760),(319,733,341,699,351,672),(362,648,366,633,369,619))
lower_window=shape((398,641),(405,657,395,686,367,698),(363,697,370,682,375,669),(381,654,389,644,398,641))
lower_eye=shape((353,751),(366,741,364,766,357,786),(351,804,325,813,320,803),(317,793,333,763,353,751))
def space(point,high):
    u,v=point
    return Vector(((403-u)*.105-.55,6.0+(494-v)*.1075)) if high else Vector(((419-u)*.103-2.64,-9.0+(630-v)*.112))
def inside(p,ring):
    hit=False
    for i,a in enumerate(ring):
        b=ring[i-1]
        if (a.y>p.y)!=(b.y>p.y) and p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x:hit=not hit
    return hit
def depth(pt,high):
    z=pt.y
    return (1.35+.28*math.exp(-((z-27)/7)**2)) if high else (1.50+.20*math.exp(-((z+22)/7)**2))
def make_object(name,verts,faces,styles):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(finish);mesh.update()
    uv=mesh.uv_layers.new(name=shell.data.uv_layers.active.name)
    for poly,tile in zip(mesh.polygons,styles):
        for li in poly.loop_indices:
            x,y,z=mesh.vertices[mesh.loops[li].vertex_index].co
            u=.07+.86*(x+5+.24*y)/24
            v=.04+.92*(z+32+.38*y)/76
            uv.data[li].uv=((tile+max(.02,min(.98,u)))/4,max(.015,min(.985,v)))
    b=bmesh.new();b.from_mesh(mesh);bmesh.ops.recalc_face_normals(b,faces=b.faces[:]);b.to_mesh(mesh);b.free()
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
    obj.parent=rig
    group=obj.vertex_groups.new(name='bow_body_root');group.add(list(range(len(verts))),1.,'REPLACE')
    mod=obj.modifiers.new('Production bow rig','ARMATURE');mod.object=rig
    return obj
def frame(name,contours,high):
    loops=[[space(p,high) for p in c] for c in contours]
    # Establish solid material to the left of all boundary loops.
    for i,loop in enumerate(loops):
        area=sum(a.x*loop[(k+1)%len(loop)].y-a.y*loop[(k+1)%len(loop)].x for k,a in enumerate(loop))
        if (area>0)!=(i==0):loop.reverse()
    verts=[];faces=[];tiles=[];caps={-1:[],1:[]}
    def face(ids,tile):faces.append(ids);tiles.append(tile)
    for index,loop in enumerate(loops):
        inset=[]
        for k,v in enumerate(loop):
            a=(v-loop[k-1]).normalized();b=(loop[(k+1)%len(loop)]-v).normalized()
            n=Vector((-a.y-b.y,a.x+b.x)).normalized()
            inset.append(n/max(.61,n.dot(Vector((-b.y,b.x)))))
        rows=[]
        for layer,(side,bevel,raise_y) in enumerate([(-1,.17,.17),(-1,.05,.06),(-1,0,-.10),(1,0,-.10),(1,.05,.06),(1,.17,.17)]):
            ids=[]
            for p,n in zip(loop,inset):
                q=p+n*bevel
                ids.append(len(verts));verts.append((q.x,side*(depth(p,high)+raise_y),q.y))
            rows.append(ids)
            if layer in (0,5):caps[side].append(ids)
        for k,(a,b) in enumerate(zip(rows,rows[1:])):
            for i in range(len(loop)):
                j=(i+1)%len(loop);face([a[i],a[j],b[j],b[i]],1 if k in (0,4) else 0)
    for side,borders in caps.items():
        rings=[[Vector((verts[i][0],verts[i][2])) for i in b] for b in borders]
        ids=[i for b in borders for i in b];flat=[q for loop in rings for q in loop]
        edges=[];off=0
        for loop in rings:
            edges.extend((off+i,off+(i+1)%len(loop)) for i in range(len(loop)));off+=len(loop)
        cv,_,tris,source,_,_=delaunay_2d_cdt(flat,edges,[],0,.000001)
        remap=[]
        for q,original in zip(cv,source):
            if original:remap.append(ids[original[0]])
            else:
                remap.append(len(verts));verts.append((q.x,side*(depth(q,high)+.17),q.y))
        for t in tris:
            p=sum((cv[i] for i in t),Vector((0,0)))/len(t)
            if inside(p,rings[0]) and not any(inside(p,h) for h in rings[1:]):face([remap[i] for i in t],0)
    return make_object(name,verts,faces,tiles)
def ribbon(name,left,right,high,metal,lift):
    # Paired boundary curves create the thick crest and its two tapered horns.
    def at(poly,t):
        f=t*(len(poly)-1);a=min(len(poly)-2,int(f));return poly[a].lerp(poly[a+1],f-a)
    verts=[];faces=[];tiles=[]
    for side in (-1,1):
        rows=[]
        for k in range(65):
            t=k/64;a=space(at(left,t),high);b=space(at(right,t),high)
            if (a-b).length<.014:b=a+Vector((.013,0))
            envelope=max(.04,math.sin(math.pi*t)**.45)
            prof=[(0,-.10),(.015,.025),(.10,.32),(.36,1),(.80,.75),(.975,.16),(1,-.10)]
            ids=[]
            for f,h in prof:
                q=a.lerp(b,f);ids.append(len(verts))
                verts.append((q.x,side*(depth(q,high)+.17+h*lift*envelope),q.y))
            rows.append(ids)
        for a,b in zip(rows,rows[1:]):
            for j in range(len(a)):
                k=(j+1)%len(a)
                faces.append([a[j],a[k],b[k],b[j]])
                tiles.append((3 if j in (1,4) else 2) if metal else (1 if j==2 else 0))
        for row in [rows[0],rows[-1]]:faces.append(row);tiles.append(2 if metal else 0)
    return make_object(name,verts,faces,tiles)
parts=[frame('Eclipse_UpperWeb',[upper,eye,upper_window,small_window],True),
       frame('Eclipse_LowerWeb',[lower,lower_window,lower_eye],False)]
def crest(name,high,metal,lift,start,left,right):
    parts.append(ribbon(name,trace(start,*left),trace(start,*right),high,metal,lift))
crest('Eclipse_UpperBronzeCrescent',True,True,.36,(304,244),
    [(332,216,375,226,397,258),(419,290,409,330,357,355)],
    [(343,222,374,249,385,279),(399,315,380,341,357,355)])
crest('Eclipse_LowerBronzeArc',False,True,.25,(303,774),
    [(318,745,347,720,382,720)],[(326,752,358,729,382,720)])
crest('Eclipse_UpperBrow',True,False,.47,(301,237),
    [(309,222,322,204,337,194),(359,198,383,230,397,253)],
    [(319,221,331,220,345,222),(365,225,388,239,397,253)])
crest('Eclipse_UpperDiagonal',True,False,.30,(344,386),
    [(350,362,372,347,395,333),(407,324,416,307,418,287)],
    [(358,368,378,360,397,346),(416,333,422,305,418,287)])
crest('Eclipse_LowerKeel',True,False,.22,(344,485),
    [(351,462,355,424,355,407),(356,391,366,375,377,366)],
    [(354,463,358,445,359,411),(359,390,371,376,377,366)])
crest('Eclipse_LowerSweep',False,False,.35,(296,772),
    [(310,750,342,719,361,708),(385,693,402,681,413,655)],
    [(325,748,346,725,366,717),(390,705,408,684,413,655)])
# A recessed graphite backing for the original optic shoe only; the visible
# outside is the retained R2 surface. The front cheek stays open at the window.
def cosmetic_boss(name,outline,back,front):
    verts=[(x,y,z) for y in (back,front) for x,z in outline]
    n=len(outline)
    faces=[list(reversed(range(n))),list(range(n,n*2))]
    faces.extend([[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)])
    return make_object(name,verts,faces,[0]*len(faces))
parts.append(cosmetic_boss('Eclipse_SightSeat',[
    (-.30,14.44),(.04,14.23),(1.96,14.22),(2.33,14.51),
    (2.18,15.51),(1.86,15.76),(.01,15.72),(-.31,15.44)],.84,1.55))
parts.append(cosmetic_boss('Eclipse_CableGuideHeel',[
    (1.8,9.80),(.0,9.72),(-3.8,9.57),(-5.18,9.54),(-5.18,9.22),
    (-3.7,9.11),(-.1,9.01),(1.8,8.72)],-1.12,-.66))
def select(objects,active):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=active
copies=[]
for obj in [shell,*hardware,*parts]:
    duplicate=obj.copy();duplicate.data=obj.data.copy();scene.collection.objects.link(duplicate);copies.append(duplicate)
select(copies,copies[0]);bpy.ops.object.join()
export=copies[0];export.name='SK_Frontier_Eclipse'
select([rig,export],rig)
bpy.ops.export_scene.fbx(filepath=str(src/'Export/SK_Frontier_Eclipse.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},
    axis_forward='-Y',axis_up='Z',add_leaf_bones=False,apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE')
bpy.data.objects.remove(export,do_unlink=True)
for im in bpy.data.images:
    if im.source=='FILE' and not im.packed_file and Path(bpy.path.abspath(im.filepath)).is_file():im.pack()
rig.data.pose_position='POSE';scene.frame_set(1)
select(parts,parts[0])
bpy.ops.wm.save_as_mainfile(filepath=str(src/'Frontier_Eclipse.blend'),compress=True)
