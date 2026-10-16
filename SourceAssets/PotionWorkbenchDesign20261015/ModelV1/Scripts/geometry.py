"""Centimetre-scale authoring primitives with explicit surfaces and material UVs."""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[1]
SPEC=json.loads((ROOT/"texture_manifest.json").read_text("utf8"))
MATS={}
PARTS=[]
GROUP="BenchBody"
FRAME=Matrix.Identity(4)
COLLECTION=None

def select(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active=o

def group(name, origin=(0,0,0), angle=0):
    global GROUP,FRAME,COLLECTION
    GROUP=name
    COLLECTION=bpy.data.collections.get(name)
    if COLLECTION is None:
        COLLECTION=bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(COLLECTION)
    FRAME=Matrix.Translation(Vector(origin))@Matrix.Rotation(math.radians(angle),4,"Z")

def rect(key):
    x0,y0,x1,y1=SPEC["regions"][key]
    return ((x0+10)/4096,1-(y1-10)/4096,(x1-10)/4096,1-(y0+10)/4096)

def image(path, noncolor=False):
    im=bpy.data.images.load(str(ROOT/"Textures"/path),check_existing=True)
    im.colorspace_settings.name="Non-Color" if noncolor else "sRGB"
    return im

def principled(name,col=(.5,.5,.5),metal=0,rough=.4,transmission=0,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*col,1)
    p.inputs["Metallic"].default_value=metal
    p.inputs["Roughness"].default_value=rough
    p.inputs["Transmission Weight"].default_value=transmission
    p.inputs["IOR"].default_value=1.46
    if emission:
        p.inputs["Emission Color"].default_value=(*col,1)
        p.inputs["Emission Strength"].default_value=emission
    m.diffuse_color=(*col,1)
    return m

def setup_materials():
    atlas=principled("PW_SurfaceAtlas")
    n=atlas.node_tree.nodes;l=atlas.node_tree.links;p=n.get("Principled BSDF")
    for kind in ("BaseColor","ORM","Normal"):
        tex=n.new("ShaderNodeTexImage");tex.image=image(f"T_PotionWorkbench_{kind}.png",kind!="BaseColor")
        if kind=="BaseColor":l.new(tex.outputs["Color"],p.inputs["Base Color"])
        elif kind=="ORM":
            sep=n.new("ShaderNodeSeparateColor");l.new(tex.outputs["Color"],sep.inputs[0])
            l.new(sep.outputs["Green"],p.inputs["Roughness"]);l.new(sep.outputs["Blue"],p.inputs["Metallic"])
        else:
            norm=n.new("ShaderNodeNormalMap");l.new(tex.outputs["Color"],norm.inputs["Color"]);l.new(norm.outputs[0],p.inputs["Normal"])
    MATS["atlas"]=atlas
    for name,prefix,ext in (("wood","BenchWood","jpg"),("endgrain","EndGrain","png")):
        mat=principled("PW_"+name);n=mat.node_tree.nodes;l=mat.node_tree.links;p=n.get("Principled BSDF")
        for kind in ("BaseColor","Roughness","Normal"):
            tex=n.new("ShaderNodeTexImage");tex.image=image(f"Source_{prefix}_{kind}.{ext}",kind!="BaseColor")
            if kind=="BaseColor":l.new(tex.outputs["Color"],p.inputs["Base Color"])
            elif kind=="Roughness":l.new(tex.outputs["Color"],p.inputs["Roughness"])
            else:
                norm=n.new("ShaderNodeNormalMap");norm.inputs["Strength"].default_value=.55
                l.new(tex.outputs["Color"],norm.inputs["Color"]);l.new(norm.outputs[0],p.inputs["Normal"])
        MATS[name]=mat
    label=principled("PW_PrintedLabels",rough=.8)
    tex=label.node_tree.nodes.new("ShaderNodeTexImage");tex.image=image("T_PotionWorkbench_Labels.png")
    label.node_tree.links.new(tex.outputs["Color"],label.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])
    MATS["label"]=label
    for name,col,trans,rough in (
        ("glass",(.91,.97,.95),1,.09),("amberglass",(.65,.37,.12),.96,.12),
        ("redliquid",(.42,.012,.018),.38,.16),("greenliquid",(.06,.27,.055),.48,.16),
        ("blueliquid",(.015,.24,.36),.48,.15),("clearliquid",(.72,.82,.73),.82,.12),
        ("potion",(.018,.33,.25),.24,.18)):
        MATS[name]=principled("PW_"+name,col,rough=rough,transmission=trans,emission=.15 if name=="potion" else 0)
    MATS["rune"]=principled("PW_RuneInlay",(.8,.36,.055),metal=.3,rough=.3,emission=2)
    MATS["lamp"]=principled("PW_LampDiffuser",(.95,.77,.46),rough=.3,emission=3)
    MATS["display"]=principled("PW_Display",(.013,.06,.075),rough=.25,emission=.6)
    MATS["displaytext"]=principled("PW_DisplayGlyph",(.35,.78,.8),rough=.4,emission=1)
    MATS["leaf"]=principled("PW_Herbs",(.055,.12,.025),rough=.72)

def uv_project(o,key):
    me=o.data;me.update();uv=me.uv_layers.active or me.uv_layers.new(name="UVMap");uv.name="UVMap"
    if not me.vertices:return
    lo=[min(v.co[k] for v in me.vertices) for k in range(3)]
    hi=[max(v.co[k] for v in me.vertices) for k in range(3)]
    rr=rect(key) if key in SPEC["regions"] else None
    for f in me.polygons:
        ax=max(range(3),key=lambda k:abs(f.normal[k]))
        a,b=(0,1) if ax==2 else (0,2) if ax==1 else (1,2)
        for li in f.loop_indices:
            c=me.vertices[me.loops[li].vertex_index].co
            if rr:
                u=(c[a]-lo[a])/max(hi[a]-lo[a],.0001)
                v=(c[b]-lo[b])/max(hi[b]-lo[b],.0001)
                uv.data[li].uv=(rr[0]+u*(rr[2]-rr[0]),rr[1]+v*(rr[3]-rr[1]))
            elif key in ("wood","endgrain"):
                uv.data[li].uv=(c[a]/120+.173,c[b]/65+.277)
            else:uv.data[li].uv=((c[a]-lo[a])/max(hi[a]-lo[a],.001),(c[b]-lo[b])/max(hi[b]-lo[b],.001))

def add(o,name,key="green"):
    o.name=name
    for c in list(o.users_collection):c.objects.unlink(o)
    COLLECTION.objects.link(o)
    o["component"]=GROUP;o["surface"]=key
    o.data.materials.clear();o.data.materials.append(MATS.get(key,MATS["atlas"]))
    if o.type=="MESH":uv_project(o,key)
    o.matrix_world=FRAME@o.matrix_world
    PARTS.append(o)
    return o

def normals(me):
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(me);bm.free();me.update()

def mesh(name,verts,faces,key="green",smooth=False):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);normals(me)
    ob=bpy.data.objects.new(name,me);COLLECTION.objects.link(ob)
    for p in me.polygons:p.use_smooth=smooth
    return add(ob,name,key)

def bevel(o,r=.15,segments=3):
    if r<=0:return o
    m=o.modifiers.new("Authored edge radii","BEVEL");m.width=r;m.segments=segments
    m.limit_method="ANGLE";m.angle_limit=math.radians(33);m.use_clamp_overlap=True;m.harden_normals=True
    w=o.modifiers.new("Weighted face normals","WEIGHTED_NORMAL");w.keep_sharp=True;w.weight=50
    return o

def box(name,p,size,key="green",r=.15):
    w,h,d=[v/2 for v in size]
    vs=[(-w,-h,-d),(w,-h,-d),(w,h,-d),(-w,h,-d),(-w,-h,d),(w,-h,d),(w,h,d),(-w,h,d)]
    fs=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    o=mesh(name,vs,fs,key);o.matrix_world=FRAME@Matrix.Translation(Vector(p));return bevel(o,r)

def rounded_points(w,h,r,n=10):
    r=min(r,w*.49,h*.49);points=[]
    for cx,cy,angle in ((w/2-r,-h/2+r,-90),(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180)):
        for j in range(n):
            a=math.radians(angle+90*j/(n-1));points.append((cx+r*math.cos(a),cy+r*math.sin(a)))
    return points

def loft(name,sections,key="ivory",n=12):
    vs=[];fs=[];count=n*4
    for z,w,h,r,x,y in sections:vs.extend((xx+x,yy+y,z) for xx,yy in rounded_points(w,h,r,n))
    for i in range(len(sections)-1):
        for j in range(count):k=(j+1)%count;fs.append((i*count+j,i*count+k,(i+1)*count+k,(i+1)*count+j))
    fs.extend((tuple(reversed(range(count))),tuple((len(sections)-1)*count+j for j in range(count))))
    ob=mesh(name,vs,fs,key,True)
    ob.data.polygons[-1].use_smooth=False;ob.data.polygons[-2].use_smooth=False
    return ob

def rounded(name,p,size,key="ivory",corner=2,edge=.08):
    w,h,d=size
    ob=loft(name,[(-d/2,w,h,corner,0,0),(d/2,w,h,corner,0,0)],key)
    ob.matrix_world=FRAME@Matrix.Translation(Vector(p));return bevel(ob,edge)

def lathe(name,p,profile,key="steel",segments=64,closed=True,axis=(0,0,1)):
    # A zero-radius profile point uses one pole, not a degenerate ring.
    if len(profile)>1 and profile[0]==profile[-1]:profile=profile[:-1]
    verts=[];rings=[];faces=[]
    for z,r in profile:
        if abs(r)<1e-7:
            rings.append([len(verts)]);verts.append((0,0,z))
        else:
            ring=[]
            for j in range(segments):
                a=j*math.tau/segments;ring.append(len(verts));verts.append((r*math.cos(a),r*math.sin(a),z))
            rings.append(ring)
    for i in range(len(rings) if closed else len(rings)-1):
        a=rings[i];b=rings[(i+1)%len(rings)]
        if len(a)==1 and len(b)==1:continue
        for j in range(segments):
            k=(j+1)%segments
            if len(a)==1:faces.append((a[0],b[k],b[j]))
            elif len(b)==1:faces.append((a[j],a[k],b[0]))
            else:faces.append((a[j],a[k],b[k],b[j]))
    ob=mesh(name,verts,faces,key,True)
    rot=Vector(axis).to_track_quat("Z","Y").to_matrix().to_4x4()
    ob.matrix_world=FRAME@Matrix.Translation(Vector(p))@rot
    # Cylindrical UV avoids a seam in hammered metal or circular lettering.
    if key in SPEC["regions"]:
        u0,v0,u1,v1=rect(key);uv=ob.data.uv_layers.active
        zmin=min(z for z,r in profile);zmax=max(z for z,r in profile)
        for face in ob.data.polygons:
            angles=[]
            for li in face.loop_indices:
                vv=ob.data.vertices[ob.data.loops[li].vertex_index].co
                angles.append((math.atan2(vv.y,vv.x)/math.tau)%1)
            if max(angles)-min(angles)>.5:angles=[a+1 if a<.5 else a for a in angles]
            for li,aa in zip(face.loop_indices,angles):
                vv=ob.data.vertices[ob.data.loops[li].vertex_index].co
                uv.data[li].uv=(u0+aa*(u1-u0),v0+(vv.z-zmin)/max(zmax-zmin,.001)*(v1-v0))
    return ob

def cylinder(name,p,radius,height,key="steel",axis=(0,0,1),sides=48,edge=.06):
    ob=lathe(name,p,[(-height/2,0),(-height/2,radius),(height/2,radius),(height/2,0)],key,sides,True,axis)
    for f in ob.data.polygons:
        if abs(f.normal.z)>.99:f.use_smooth=False
    return bevel(ob,min(edge,radius*.15,height*.2))

def ring(name,p,outer,inner,height,key="brass",axis=(0,0,1),sides=80):
    return lathe(name,p,[(-height/2,outer),(height/2,outer),(height/2,inner),(-height/2,inner)],key,sides,True,axis)

def torus(name,p,major,minor,key="brass",axis=(0,0,1),steps=80,tube=10):
    profile=[(minor*math.sin(j*math.tau/tube),major+minor*math.cos(j*math.tau/tube)) for j in range(tube)]
    return lathe(name,p,profile,key,steps,True,axis)

def rod(name,a,b,r,key="steel",sides=24):
    a=Vector(a);b=Vector(b);return cylinder(name,(a+b)*.5,r,(b-a).length,key,(b-a).normalized(),sides,edge=min(.04,r*.2))

def tube(name,points,r=.12,key="rubber",smooth=True):
    c=bpy.data.curves.new(name,"CURVE");c.dimensions="3D";c.resolution_u=8
    c.bevel_depth=r;c.bevel_resolution=2;c.use_fill_caps=True
    if smooth:
        s=c.splines.new("BEZIER");s.bezier_points.add(len(points)-1)
        for q,p in zip(s.bezier_points,points):q.co=p;q.handle_left_type="AUTO";q.handle_right_type="AUTO"
    else:
        s=c.splines.new("POLY");s.points.add(len(points)-1)
        for q,p in zip(s.points,points):q.co=(*p,1)
    ob=bpy.data.objects.new(name,c);COLLECTION.objects.link(ob);select(ob);bpy.ops.object.convert(target="MESH")
    # Build end caps during authoring, including Blender headless conversions.
    bm=bmesh.new();bm.from_mesh(ob.data)
    boundary=[e for e in bm.edges if e.is_boundary]
    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    return add(ob,name,key)

def cut_cylinder(target,p,radius,height):
    cutter=cylinder("Manufacturing cutter",p,radius,height,"steel",sides=96,edge=0)
    PARTS.remove(cutter);select(target)
    mod=target.modifiers.new("Manufactured through opening","BOOLEAN");mod.operation="DIFFERENCE";mod.solver="EXACT";mod.object=cutter
    while target.modifiers.find(mod.name)>0:bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    bm=bmesh.new();bm.from_mesh(target.data)
    bmesh.ops.dissolve_degenerate(bm,dist=.00005,edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(target.data);bm.free()
    uv_project(target,target["surface"])

def screw(name,p,r=.33,axis=(0,1,0),key="steel"):
    v=Vector(p);a=Vector(axis).normalized()
    cylinder(name+" washer",v-a*.035,r*1.28,.10,key,a,24,0)
    o=cylinder(name+" head",v+a*.07,r,.17,key,a,6,.025)
    # Recessed drive is a dark inset with a narrower actual metal bridge.
    cylinder(name+" drive",v+a*.162,r*.44,.018,"rubber",a,12,0)
    return o

def text(name,body,p,size=1,key="brass",axis=(0,1,0),extrude=.015):
    c=bpy.data.curves.new(name,"FONT");c.body=body;c.size=size;c.align_x="CENTER";c.align_y="CENTER";c.extrude=extrude;c.resolution_u=3
    o=bpy.data.objects.new(name,c);COLLECTION.objects.link(o)
    o.location=p;o.rotation_euler=Vector(axis).to_track_quat("Z","Y").to_euler()
    select(o);bpy.ops.object.convert(target="MESH");return add(o,name,key)

def label_flat(name,p,width,height,index,axis=(0,1,0)):
    vs=[(-width/2,-height/2,0),(width/2,-height/2,0),(width/2,height/2,0),(-width/2,height/2,0)]
    ob=mesh(name,vs,[(0,1,2,3)],"label")
    ob.matrix_world=FRAME@Matrix.Translation(Vector(p))@Vector(axis).to_track_quat("Z","Y").to_matrix().to_4x4()
    u0=(index%4)/4+.008;u1=u0+.234
    v1=1-(index//4)/4-.008;v0=v1-.234
    for d,uv in zip(ob.data.uv_layers.active.data,((u0,v0),(u1,v0),(u1,v1),(u0,v1))):d.uv=uv
    return ob

def label_bottle(name,center,radius,z,height,index,angle=math.pi/2,span=1.5):
    vs=[];n=24
    for zz in (z-height/2,z+height/2):
        for i in range(n+1):
            a=angle-span/2+span*i/n
            vs.append((center[0]+radius*math.cos(a),center[1]+radius*math.sin(a),zz))
    fs=[(i,i+1,n+2+i,n+1+i) for i in range(n)]
    ob=mesh(name,vs,fs,"label",True)
    u0=(index%4)/4+.008;u1=u0+.234
    v1=1-(index//4)/4-.008;v0=v1-.234
    for f in ob.data.polygons:
        for li in f.loop_indices:
            ix=ob.data.loops[li].vertex_index
            ob.data.uv_layers.active.data[li].uv=(u0+(ix%(n+1))/n*(u1-u0),v0+(ix//(n+1))*(v1-v0))
    return ob

def parent_keep(objects,name,pivot):
    ob=bpy.data.objects.new(name,None);COLLECTION.objects.link(ob);ob.location=pivot
    ob.empty_display_type="PLAIN_AXES";ob.empty_display_size=6
    bpy.context.view_layer.update()
    for child in objects:
        world=child.matrix_world.copy();child.parent=ob;child.matrix_world=world
    return ob
