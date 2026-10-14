"""Three small authored measuring/finishing tools, using the bench's existing materials."""
import bpy,bmesh,math,re
from mathutils import Matrix,Vector

def add_engineering_tools(existing):
    mats={re.sub(r'\.\d{3}$','',m.name):m for o in existing for m in o.data.materials if m}
    steel=mats['WBKC_Misc'];dark=mats['WSBench_CableRubber'];grip=mats['WSSculpt_RubberGrip']
    steel_rect=(.52,.52,.98,.98)
    def activate(o):
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    def uv(o,mat):
        lay=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap');lay.name='UVMap'
        for p in o.data.polygons:
            for li in p.loop_indices:
                v=o.data.vertices[o.data.loops[li].vertex_index].co
                lay.data[li].uv=((steel_rect[0]+(v.x*3%1)*.44,steel_rect[1]+(v.y*3%1)*.44) if mat==steel else (v.x*5,v.y*5))
    def finish(o,mat,bevel=0):
        activate(o);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
        o.data.materials.append(mat);uv(o,mat)
        if bevel:
            m=o.modifiers.new('Tool edge bevel','BEVEL');m.width=bevel;m.segments=3;m.affect='EDGES'
            bpy.ops.object.modifier_apply(modifier=m.name)
        for p in o.data.polygons:p.use_smooth=True
        m=o.modifiers.new('Tool face normals','WEIGHTED_NORMAL');m.keep_sharp=True
        bpy.ops.object.modifier_apply(modifier=m.name)
        return o
    def box(name,loc,size,mat=steel,bevel=.00035):
        bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=size;return finish(o,mat,bevel)
    def cyl(name,loc,r,depth,mat=steel,axis='Z',verts=32):
        rot=(math.pi/2,0,0) if axis=='Y' else (0,0,0)
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc,rotation=rot)
        o=bpy.context.object;o.name=name;return finish(o,mat,.0002)
    def poly(name,points,z0,z1,mat=steel):
        n=len(points);verts=[(x,y,z) for z in (z0,z1) for x,y in points]
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o)
        return finish(o,mat,0 if mat==dark else .00025)
    def text(name,caption,loc,size=.0022):
        cu=bpy.data.curves.new(name,'FONT');cu.body=caption;cu.resolution_u=4;cu.size=size;cu.extrude=.000006;cu.align_x='CENTER'
        ob=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(ob);ob.location=loc;activate(ob);bpy.ops.object.convert(target='MESH')
        return finish(bpy.context.object,dark,0)
    def join_place(parts,name,x,y,yaw=0):
        activate(parts[0])
        for o in parts[1:]:o.select_set(True)
        bpy.ops.object.join();o=bpy.context.object;o.name=name
        if name=='detail_hand_file':o.data.transform(Matrix.Rotation(math.radians(.56),4,'X'))
        o.data.transform(Matrix.Rotation(math.radians(yaw),4,'Z'))
        lo=[min(v.co[i] for v in o.data.vertices) for i in range(3)];hi=[max(v.co[i] for v in o.data.vertices) for i in range(3)]
        o.data.transform(Matrix.Translation(Vector((-x/100-(lo[0]+hi[0])/2,-y/100-(lo[1]+hi[1])/2,.9392-lo[2]))));o.data.update()
        return o
    # Vernier caliper: real jaws, slider, locking wheel, depth blade and beam graduations.
    p=[box('Caliper_beam',(0,0,.004),(.235,.012,.003)),box('Caliper_slider',(-.049,0,.006),(.039,.028,.007)),box('Caliper_depth_blade',(.132,0,.0036),(.056,.003,.0015))]
    p += [poly('Caliper_fixed_jaw',[(-.116,-.007),(-.104,-.007),(-.104,-.037),(-.101,-.047),(-.113,-.049)],.002,.006),
          poly('Caliper_sliding_jaw',[(-.061,-.01),(-.05,-.01),(-.05,-.049),(-.061,-.045),(-.064,-.035)],.002,.006),
          poly('Caliper_inside_fixed',[(-.115,.005),(-.107,.005),(-.105,.027),(-.115,.021)],.002,.005),
          poly('Caliper_inside_slider',[(-.054,.010),(-.047,.010),(-.044,.021),(-.054,.026)],.002,.005),
          cyl('Caliper_lock_screw',(-.05,0,.011),.005,.003)]
    for i in range(91):
        x=-.092+i*.002
        p.append(box('Caliper_scale', (x,-.002,.00556),(.00014,.0045 if i%5==0 else .0025,.00007),dark,0))
    for i in range(10):p.append(text('Caliper_numeral',str(i*20),(-.09+i*.020,.0016,.0056),.0026))
    for i in range(11):p.append(box('Caliper_vernier',(-.065+i*.003,-.010,.00955),(.00015,.0035 if i%5==0 else .002,.00008),dark,0))
    caliper=join_place(p,'detail_vernier_caliper',44,73,90)
    # Try square: 180 mm blade, dark thick stock, three flush metal rivets and markings.
    p=[box('Square_blade',(0,.004,.004),(.18,.019,.0022)),box('Square_stock',(-.086,-.043,.006),(.019,.116,.012),grip,.0012)]
    for y in (-.083,-.049,-.014):p.append(cyl('Square_rivet',(-.086,y,.0121),.003,.0007))
    for i in range(76):p.append(box('Square_tick',(-.07+i*.002,.009,.00515),(.00016,.007 if i%5==0 else .004,.00006),dark,0))
    for i in range(8):p.append(text('Square_number',str(i*20),(-.068+i*.020,-.002,.0052),.003))
    square=join_place(p,'detail_try_square',229,248,0)
    # Hand file: bevelled steel blank, crossed cutting teeth, ferrule and shaped rubber handle.
    p=[poly('File_blank',[(-.012,-.16),(.012,-.16),(.015,.04),(-.015,.04)],0,.005),
       cyl('File_ferrule',(0,.048,.008),.010,.018,axis='Y'),cyl('File_handle',(0,.105,.012),.014,.101,grip,axis='Y')]
    for i in range(45):
        y=-.154+i*.0042
        p.append(poly('File_cross_cut',[(-.011,y),(.011,y+.009),(.011,y+.0094),(-.011,y+.0004)],.00503,.00510,dark))
    for y in (.065,.078,.091,.104,.117,.13,.143):p.append(cyl('File_grip_rib',(0,y,.012),.0146,.0018,grip,axis='Y'))
    file=join_place(p,'detail_hand_file',148,223,0)
    return [caliper,square,file]

