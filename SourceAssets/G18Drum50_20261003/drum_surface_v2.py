"""Detailed exterior, authored in a drum frame, then yawed without moving its seat."""
def smooth01(lo,hi,v):
    t=max(0,min(1,(v-lo)/(hi-lo)));return t*t*(3-2*t)

def mesh_part(name,verts,faces,mat=poly,bevel=0):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    return finish(ob,mat,bevel)

def arc_strip(name,profile,angle,half_angle,mat=poly):
    # The outer latch surfaces follow the actual shell radius instead of floating boxes.
    n=12;verts=[(x,cy+rad*math.cos(a),cz+rad*math.sin(a)) for x,rad in profile for a in [angle-half_angle+2*half_angle*i/n for i in range(n+1)]]
    faces=[];w=n+1
    for j in range(len(profile)):
        for i in range(n):faces.append((j*w+i,j*w+i+1,((j+1)%len(profile))*w+i+1,((j+1)%len(profile))*w+i))
    faces.append(tuple(j*w for j in reversed(range(len(profile)))))
    faces.append(tuple(j*w+n for j in range(len(profile))))
    return mesh_part(name,verts,faces,mat)

lathe('Moulded_shell_continuous_profile',[(-.036,.055),(-.034,.060),(-.030,.0623),(-.025,.063),(.008,.063),(.012,.0627),(.0126,.0621),(.0133,.0621),(.014,.0627),(.024,.0623),(.030,.061),(.034,.0575),(.035,.0535)])
lathe('Front_cover_rolled_lip',[(-.036,.0556),(-.039,.0556),(-.041,.0570),(-.042,.0591),(-.0415,.0601),(-.0403,.0612),(-.0378,.0622),(-.0345,.062),(-.033,.0608),(-.0335,.059)],poly,True)
lathe('Fine_annular_cover_seal',[(-.0415,.0554),(-.0415,.0561),(-.0402,.0561),(-.0402,.0554)],rubber,True)

# A single connected face contains all three raised pressings with radiused roots.
n=240
radii=[0,.004,.0085,.0095,.0100,.0104,.0109,.0114,.0121,.0135,.016,.021,.026,.031,.036,.041,.045,.0475,.0485,.0495,.0505,.0518,.053,.054,.0546,.0553,.0557]
verts=[]
for rad in radii:
    for i in range(n):
        a=2*math.pi*i/n
        base=-.0402-.0007*(1-smooth01(.0095,.0109,rad))
        groove=.00058*math.exp(-((rad-.0106)/.00035)**2)
        form=0
        for k in range(3):
            axis=math.pi/2+k*2*math.pi/3
            along=rad*math.cos(a-axis);across=abs(rad*math.sin(a-axis))
            form=max(form,(1-smooth01(.0009,.0029,across))*smooth01(.0109,.0135,along)*(1-smooth01(.0475,.0508,along)))
        x=base+groove-.0027*form+.0003*smooth01(.0525,.0557,rad)
        verts.append((x,cy+rad*math.cos(a),cz+rad*math.sin(a)))
faces=[]
for j in range(len(radii)-1):
    for i in range(n):faces.append((j*n+i,(j+1)*n+i,(j+1)*n+(i+1)%n,j*n+(i+1)%n))
ob=mesh_part('One_piece_three_rib_front_cover',verts,faces,poly)
select(ob);bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000005);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()

for k in range(6):
    a=math.pi/6+k*math.pi/3
    arc_strip('Formed_cover_latch_%d'%k,[(-.041,.0597),(-.0414,.061),(-.0385,.0635),(-.029,.0640),(-.0278,.0632),(-.029,.0623),(-.037,.0619)],a,.062)
    arc_strip('Latch_thumb_recess_%d'%k,[(-.0348,.06405),(-.034,.06405),(-.034,.06418),(-.0348,.06418)],a,.039,rubber)
for k in range(6):
    a=math.pi/6+k*math.pi/3
    arc_strip('Long_shell_formed_rib_%d'%k,[(-.028,.0623),(-.024,.0632),(-.021,.0642),(.009,.0642),(.021,.0634),(.025,.0618),(.018,.0625),(-.024,.0625)],a,.032)
lathe('Rear_cover_inset_seam',[(.029,.0590),(.031,.0601),(.032,.0600),(.030,.0590)],rubber,True)
lathe('Rear_cover_moulded_edge',[(.030,.0530),(.034,.054),(.036,.0545),(.037,.0528),(.037,.0495),(.035,.048)],poly,True)
disk('Rear_service_plate',.0357,.0493,.0026)
lathe('Rear_cap_centre_recess',[(.0371,.010),(.0374,.012),(.0371,.014),(.0368,.014),(.0368,.010)],rubber,True)
disk('Rear_service_lock',.0373,.0102,.0012,steel,48)
for k in range(4):
    a=math.pi/4+k*math.pi/2
    box('Rear_shallow_support_web_%d'%k,(.0373,cy+math.cos(a)*.030,cz+math.sin(a)*.030),(.0018,.003,.032),poly,.0007,a-math.pi/2)
    y=cy+math.cos(a)*.044;z=cz+math.sin(a)*.044
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.0021,depth=.00065,location=(.038,y,z),rotation=(0,math.pi/2,0))
    ob=bpy.context.object;ob.name='Rear_recessed_fastener_%d'%k;finish(ob,steel,.00018)
    box('Rear_fastener_socket_%d'%k,(.0384,y,z),(.00015,.0014,.00045),rubber,.00008)
# Rotate only the drum and its exterior. The G18 magazine seat and feed neck stay fixed.
pivot=Vector((0,cy,cz));yaw=Matrix.Rotation(-math.pi/2,4,'Z')
turn=Matrix.Translation(pivot)@yaw@Matrix.Translation(-pivot)
for ob in parts:ob.matrix_world=turn@ob.matrix_world

def collar(name,rows,mat=poly):
    verts=[]
    for z,hx,hy,r in rows:
        for x,y in [(-hx+r,-hy),(hx-r,-hy),(hx,-hy+r),(hx,hy-r),(hx-r,hy),(-hx+r,hy),(-hx,hy-r),(-hx,-hy+r)]:verts.append((x,neck_end_y+y,z))
    faces=[]
    for j in range(len(rows)-1):
        for i in range(8):faces.append((j*8+i,j*8+(i+1)%8,(j+1)*8+(i+1)%8,(j+1)*8+i))
    faces.extend([tuple(range(7,-1,-1)),tuple((len(rows)-1)*8+i for i in range(8))])
    return mesh_part(name,verts,faces,mat,.00055)

# Rebuild the adapter in the unchanged neck frame, flowing into the newly yawed shell.
collar('Sculpted_neck_to_drum_saddle',[(-.157,.024,.024,.005),(-.147,.020,.025,.0035),(-.139,.017,.025,.0025),(-.123,.0157,.0235,.0018)])
collar('Feed_neck_collar_seal',[(-.124,.0158,.0236,.0015),(-.1228,.0158,.0236,.0015)],rubber)
collar('Rolled_neck_socket_lip',[(-.123,.0158,.0236,.0015),(-.1215,.016,.0238,.0017),(-.120,.0147,.0225,.0014)],steel)
for side in (-1,1):
    for dy in (-.016,.016):
        y=neck_end_y+dy
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.0026,depth=.00055,location=(side*.0172,y,-.1355),rotation=(0,math.pi/2,0))
        ob=bpy.context.object;ob.name='Adapter_counterbore';finish(ob,rubber,.0002)
        bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.0019,depth=.0007,location=(side*.0175,y,-.1355),rotation=(0,math.pi/2,0))
        ob=bpy.context.object;ob.name='Adapter_recessed_bolt';finish(ob,steel,.00015)
        box('Adapter_hex_socket',(side*.01795,y,-.1355),(.00015,.0012,.0012),rubber,.00020)
