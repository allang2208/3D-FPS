"""Reusable centimeter-scale electronic prop parts; geometry is not a working circuit."""
import bpy, bmesh, math
from mathutils import Vector
import mesh_helpers as H

box=H.box;cut=H.cut;cyl=H.cylinder;ring=H.ring;panel=H.panel

def pcb(name,p,size,notches=()):
    obj=box(name,p,size,'pcb',.035,2);obj['pcb_surface']=True
    for at,extent in notches:cut(obj,at,extent)
    return obj

def round_cut(obj,p,radius,depth,axis='Z'):
    rotation=(0,math.pi/2,0) if axis=='X' else (math.pi/2,0,0) if axis=='Y' else (0,0,0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=40,radius=radius,depth=depth,location=p,rotation=rotation)
    cutter=bpy.context.object;H.select(obj)
    mod=obj.modifiers.new('Drilled opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    while obj.modifiers.find(mod.name)>0:bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    H.project_uv(obj,obj['surface_region'])

def chip(name,p,w,h,t=.17,mark=True):
    obj=box(name,p,(w,h,t),'chip',min(.035,t*.12),2)
    if mark:panel(name+' laser marking',(p[0],p[1],p[2]+t*.5+.002),w*.84,min(h*.72,w*.84/2.8),'chipmark')
    return obj

def smd(name,p,size=(.18,.10,.06),region='ceramic'):
    w,h,t=size
    box(name,p,size,region,0)
    for sign in (-1,1):box(name+' solder terminal',(p[0]+sign*w*.41,p[1],p[2]-.004),(w*.20,h+.016,t+.01),'solder',0)

def cap_row(name,x,y,z,count=10,spacing=.31,axis='X'):
    for j in range(count):
        smd(name,(x+j*spacing if axis=='X' else x,y+j*spacing if axis=='Y' else y,z))

def plated_hole(obj,name,x,y,z,r=.17):
    round_cut(obj,(x,y,z),r,1.5)
    ring(name,(x,y,z+.091),r+.09,r,.021,'solder',sides=32)

def edge_contacts(name,x0,y,z,length,count,height=.63,gap=None):
    # Thin plated contacts retain actual thickness without subpixel bevel strips.
    for i in range(count):
        x=x0+(i+.5)*length/count
        if gap and gap[0]<x<gap[1]:continue
        for side in (-1,1):
            box(name,(x,y,z+side*.085),(length/count*.70,height,.014),'gold',0)

def heat_sink(name,p,w,h,height,fin_count=15,region='aluminum',along='Y'):
    x,y,z=p
    box(name+' base',(x,y,z+.10),(w,h,.20),region,.045,3)
    if along=='Y':
        for j in range(fin_count):
            xx=x-w*.47+j*w*.94/max(1,fin_count-1)
            box(name+' fin',(xx,y,z+.20+height*.5),(.066,h,height),region,.006,1)
    else:
        for j in range(fin_count):
            yy=y-h*.47+j*h*.94/max(1,fin_count-1)
            box(name+' fin',(x,yy,z+.20+height*.5),(w,.067,height),region,.006,1)

def side_panel(name,p,w,h,region='primary',side='X-'):
    ux=Vector((0,-1,0)) if side=='X-' else Vector((0,1,0))
    vy=Vector((0,0,1))
    verts=[tuple(Vector(p)+ux*a+vy*b) for a,b in ((-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2))]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],[(0,1,2,3)]);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);H.register(obj,name,region)
    u0,v0,u1,v1=H.uv_rect(region)
    for li,uv in zip(mesh.polygons[0].loop_indices,((u0,v0),(u1,v0),(u1,v1),(u0,v1))):mesh.uv_layers.active.data[li].uv=uv
    return obj

def port_x(name,p,depth,width,height,side=-1,region='steel',contacts=8):
    x,y,z=p
    obj=box(name+' formed housing',p,(depth,width,height),region,.065,3)
    cut(obj,(x+side*.22*depth,y,z+.01),(depth*.94,width-.20,height-.20))
    # Back insulation and contact carrier are inside the real recess.
    box(name+' rear insulation',(x-side*depth*.36,y,z),(depth*.14,width-.24,height-.24),'plastic',.025,2)
    for j in range(contacts):
        yy=y-width*.35+(j+.5)*width*.70/contacts
        box(name+' contact',(x+side*.08*depth,yy,z-height*.22),(depth*.52,width*.48/contacts,.028),'gold',.008,2)
    return obj

def sata_end(x,z,width=6.7):
    carrier=box('Recessed SATA carrier',(x,0,z),(.67,width,.55),'plastic',.04,3)
    for y,w,n in ((-1.66,2.80,15),(1.28,1.58,7)):
        cut(carrier,(x+.22,y,z+.10),(.59,w,.35))
        box('SATA insulating tongue',(x+.18,y,z+.025),(.54,w-.12,.075),'plastic',.015,2)
        for j in range(n):
            yy=y-w*.42+(j+.5)*w*.84/n
            box('SATA contact pad',(x+.185,yy,z+.073),(.42,w*.54/n,.018),'gold',.008,2)
        box('SATA connector key',(x+.23,y-w*.5+.07,z+.15),(.45,.12,.20),'plastic',.018,2)
    return carrier

def power_socket(name,p,width=2.15,depth=1.40,height=1.25):
    x,y,z=p;body=box(name,p,(width,depth,height),'plastic',.065,3)
    for row in (-1,1):
        for col in range(4):
            xx=x+(col-1.5)*width*.215;zz=z+row*height*.22
            cut(body,(xx,y-depth*.43,zz),(width*.16,depth*.50,height*.30))
            box(name+' recessed terminal',(xx,y-depth*.25,zz),(.09,.16,.09),'solder',.012,2)
    box(name+' locking catch',(x,y, z+height*.5+.10),(.56,.48,.20),'plastic',.035,3)

def fan(name,p,radius,blades=11):
    x,y,z=p
    ring(name+' frame',p,radius+.12,radius,.24,'plastic',sides=72)
    cyl(name+' motor hub',(x,y,z+.025),radius*.245,.42,'plastic',sides=56,radius=.055)
    cyl(name+' centre medallion',(x,y,z+.252),radius*.18,.045,'blue',sides=40,radius=.015)
    for j in range(blades):
        verts=[];faces=[];steps=12
        for side in (0,1):
            for k in range(steps+1):
                t=k/steps;r=radius*(.24+.72*t)
                centre=j*math.tau/blades-.40*t
                span=.12+.25*math.sin(t*math.pi*.65)
                for edge in (-1,1):
                    a=centre+edge*span*.5
                    zz=z+.03+.10*math.sin(t*math.pi)+edge*.09*t+side*.045
                    verts.append((x+r*math.cos(a),y+r*math.sin(a),zz))
        count=(steps+1)*2
        for k in range(steps):
            a=k*2;faces.extend(((a,a+2,a+3,a+1),(count+a+1,count+a+3,count+a+2,count+a),
                (a,count+a,count+a+2,a+2),(a+1,a+3,count+a+3,count+a+1)))
        faces.extend(((0,1,count+1,count),(steps*2,count+steps*2,count+steps*2+1,steps*2+1)))
        mesh=bpy.data.meshes.new(name+' swept blade');mesh.from_pydata(verts,[],faces);mesh.update()
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
        obj=bpy.data.objects.new(name+' swept blade',mesh);bpy.context.collection.objects.link(obj);H.register(obj,obj.name,'plastic')
        for face in mesh.polygons:face.use_smooth=True

def pcb_uv(obj):
    H.project_uv(obj,'fr4');mesh=obj.data;u0,v0,u1,v1=H.uv_rect('pcb')
    xs=[v.co.x for v in mesh.vertices];ys=[v.co.y for v in mesh.vertices]
    xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
    for face in mesh.polygons:
        if abs(face.normal.z)<.75:continue
        for li in face.loop_indices:
            point=mesh.vertices[mesh.loops[li].vertex_index].co
            u=(point.x-xmin)/(xmax-xmin);v=(point.y-ymin)/(ymax-ymin)
            if face.normal.z<0:u=1-u
            mesh.uv_layers.active.data[li].uv=(u0+u*(u1-u0),v0+v*(v1-v0))
