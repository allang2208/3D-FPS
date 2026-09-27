"""Centimetre-authored hanging tools, with eyelets seated on supported J hooks."""
import math
import bpy
import bmesh
from mathutils import Vector


def co(p):
    return Vector((p[0]*.01,-p[1]*.01,p[2]*.01))


def build():
    # Remove the old unsupported tongs only; preserve the accepted rail and station.
    for ob in list(bpy.context.scene.objects):
        if ob.name.startswith(('Tong handle','Tong jaw','Tong hinge','Tong hook','RackV6 ')):
            bpy.data.objects.remove(ob,do_unlink=True)
    groups={name:[] for name in ('Mounts','Tongs','Hammer','File','Poker')}

    def finish(ob,name,slot,group,bevel=.08):
        ob.name='RackV6 '+name
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True);bpy.context.view_layer.objects.active=ob
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        ob.data.materials.clear();ob.data.materials.append(bpy.data.materials[slot])
        if bevel:
            mod=ob.modifiers.new('Forged edge radius','BEVEL');mod.width=bevel*.01;mod.segments=3
            bpy.ops.object.modifier_apply(modifier=mod.name)
        ob.data.set_sharp_from_angle(angle=math.radians(45))
        uv=ob.data.uv_layers.active or ob.data.uv_layers.new(name='Physical50cm')
        for face in ob.data.polygons:
            axis=max(range(3),key=lambda i:abs(face.normal[i]))
            for li in face.loop_indices:
                p=ob.data.vertices[ob.data.loops[li].vertex_index].co
                # Grain runs lengthwise on all the upright wooden handles.
                pair=(p.x,p.z) if axis==1 else ((p.y,p.z) if axis==0 else (p.x,p.y))
                uv.data[li].uv=(pair[0]/.5,pair[1]/.5)
        groups[group].append(ob)
        return ob

    def beam(name,a,b,radius,slot='DarkSteel',group='Mounts',vertices=16,bevel=.055):
        start,end=co(a),co(b);direction=end-start
        bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius*.01,
                                          depth=direction.length,location=(start+end)*.5)
        ob=bpy.context.object;ob.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
        return finish(ob,name,slot,group,bevel)

    def box(name,center,size,slot='DarkSteel',group='Mounts',bevel=.12):
        bpy.ops.mesh.primitive_cube_add(size=1,location=co(center))
        ob=bpy.context.object;ob.dimensions=Vector(size)*.01
        return finish(ob,name,slot,group,bevel)

    def mesh(name,verts,faces,slot,group,bevel=.06):
        data=bpy.data.meshes.new(name)
        data.from_pydata([co(p) for p in verts],[],[tuple(reversed(f)) for f in faces]);data.update()
        bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
        ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
        return finish(ob,name,slot,group,bevel)

    def tube(name,points,radius,group):
        # A continuous bevelled curve gives smooth forged bends without exposed cylinder ends.
        curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D'
        curve.resolution_u=6;curve.bevel_depth=radius*.01;curve.bevel_resolution=3;curve.use_fill_caps=True
        spline=curve.splines.new('BEZIER');spline.bezier_points.add(len(points)-1)
        for bp,p in zip(spline.bezier_points,points):
            bp.co=co(p);bp.handle_left_type='AUTO';bp.handle_right_type='AUTO'
        ob=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(ob)
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
        bpy.ops.object.convert(target='MESH')
        return finish(bpy.context.object,name,'DarkSteel',group,0)

    def eye(x,group):
        # Hook underside z=94.30 touches the top of the eye opening at z=94.29.
        # The eye bottom z=90.85 is connected directly to the tool's handle/cap.
        bpy.ops.mesh.primitive_torus_add(major_segments=36,minor_segments=10,
            major_radius=.0172,minor_radius=.0028,location=co((x,44,92.85)),rotation=(math.pi/2,0,0))
        return finish(bpy.context.object,group+' suspension eye','DarkSteel',group,0)

    def mount(x):
        box('hook backing plate',(x,47.7,97),(3.4,.45,5.4),bevel=.16)
        for z in (95.05,98.95):
            beam('mounting rivet',(x,47.65,z),(x,47.13,z),.34,vertices=12)
        # Straight bearing section keeps the lower surface coincident with the eye seat.
        tube('upper hook shank',[(x,47.85,97.2),(x,45.5,97.2),(x,43.6,97),
                                 (x,43.1,96.25),(x,43.1,95.2),(x,43.6,94.7)],.4,'Mounts')
        beam('hook bearing seat',(x,43.6,94.7),(x,44.6,94.7),.4)
        tube('retaining hook tip',[(x,44.55,94.7),(x,45.2,95.1),(x,45.3,96.2)],.4,'Mounts')

    def handle(x,bottom,top,group):
        # Oval handle, a narrow neck and a fuller palm section; real end grain faces.
        levels=[(bottom,.72),(bottom+1.2,.74),(bottom+(top-bottom)*.55,1.05),
                (top-1.3,.85),(top,.70)]
        verts=[];n=20
        for z,r in levels:
            for i in range(n):
                a=math.tau*i/n;verts.append((x+math.cos(a)*r,44+math.sin(a)*r*.78,z))
        faces=[]
        for j in range(len(levels)-1):
            for i in range(n):
                k=(i+1)%n;faces.append((j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i))
        faces.extend([tuple(reversed(range(n))),tuple((len(levels)-1)*n+i for i in range(n))])
        mesh(group+' oak handle',verts,faces,'Wood',group,.045)
        beam(group+' eye ferrule',(x,44,top-.6),(x,44,top+.2),.83,group=group)

    for x in (8,27,43,57):
        mount(x)

    # The eye is forged onto ONE rein, so the tongs can still open at their riveted pivot.
    eye(8,'Tongs')
    tube('tong supported rein',[(8,44,91.05),(8.15,44,86),(9.6,44,75),(11,44,65)],.55,'Tongs')
    tube('tong free rein',[(14.5,44.9,89.7),(14.2,44.9,83),(12.3,44.9,74),(11,44.9,65)],.55,'Tongs')
    tube('tong right jaw',[(11,44,65),(12.8,44.2,61),(13,44.45,57),(12.7,44.45,55.8),(11.7,44.45,55)],.7,'Tongs')
    tube('tong left jaw',[(11,44.9,65),(9.2,44.7,61),(9,44.45,57),(9.3,44.45,55.8),(10.3,44.45,55)],.7,'Tongs')
    beam('tong pivot rivet',(11,43.2,65),(11,45.7,65),1.35,'PolishedSteel','Tongs',24)

    # Cross-peen hammer hangs by a metal eye secured into its wooden handle end.
    eye(27,'Hammer');handle(27,66.4,90.7,'Hammer')
    box('hammer forged head',(27,44,67.4),(9.8,4.3,4.7),group='Hammer',bevel=.45)
    box('hammer striking face',(21.75,44,67.4),(1.2,4.6,4.9),'PolishedSteel','Hammer',.3)
    verts=[]
    for x,half_y,half_z in ((31.5,2.05,2.2),(34.5,.5,1.75)):
        verts.extend([(x,44-half_y,67.4-half_z),(x,44+half_y,67.4-half_z),
                      (x,44+half_y,67.4+half_z),(x,44-half_y,67.4+half_z)])
    mesh('hammer cross peen',verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'DarkSteel','Hammer',.16)
    box('hammer handle wedge',(27,44,64.98),(1.25,.55,.25),'DarkSteel','Hammer',.05)

    # Flat file with a wooden handle, ferrule, tang and shallow cross-cut tooth ridges.
    eye(43,'File');handle(43,82.3,90.7,'File')
    beam('file lower ferrule',(43,44,81.8),(43,44,83.5),.82,group='File')
    box('file tang',(43,44,81.2),(1.05,.5,4),group='File',bevel=.09)
    verts=[]
    for z,half_x in ((64.5,.65),(80.1,1.1)):
        verts.extend([(43-half_x,43.69,z),(43+half_x,43.69,z),(43+half_x,44.31,z),(43-half_x,44.31,z)])
    mesh('file blade',verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'PolishedSteel','File',.055)
    for i in range(30):
        z=65.1+i*.48;half_x=.65+(z-64.5)/15.6*.45-.08
        beam('file tooth',(43-half_x,43.66,z),(43+half_x,43.66,z+.32),.045,'DarkSteel','File',6,0)
        beam('file cross tooth',(43-half_x,43.66,z+.34),(43+half_x,43.66,z+.05),.035,'DarkSteel','File',6,0)

    eye(57,'Poker');handle(57,81.3,90.7,'Poker')
    beam('poker lower ferrule',(57,44,80.8),(57,44,82.4),.8,group='Poker')
    tube('poker shaft and bent tip',[(57,44,81.4),(57,44,66),(57,44,56),
                                   (57,43.6,53.8),(57,42,53),(57,39.5,53.2)],.46,'Poker')
    return {'groups':groups,'sockets':{'TongGrip':[8.8,44,82],'TongPivot':[11,44.45,65]},
            'hook_centers_cm':[8,27,43,57],
            'hanging_tools':['eye-supported tongs','cross-peen hammer','flat file','forge poker']}
