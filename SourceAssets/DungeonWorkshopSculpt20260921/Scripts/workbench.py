def build_bench():
    for c,w,d in [((.55,2.61),.76,2.26),((1.77,3.73),1.64,.68)]:
        x,y=c;g='BenchFrame'
        for dx in (-w/2+.045,w/2-.045):
            for dy in (-d/2+.050,d/2-.050):
                xx,yy=x+dx,y+dy
                f=flat((xx,yy,.458),math.pi if dx>0 else 0)
                profile(g,'Rolled angle steel leg',[(-.027,-.027),(.027,-.027),(.027,-.022),(-.022,-.022),(-.022,.027),(-.027,.027)],f,.812,'RackPaint',.0012)
                box(g,'Welded adjustable foot plate',(xx,yy,.045),(.075,.075,.010),'Machined',.004)
                cylinder(g,'Levelling foot screw',(xx,yy,.010),(xx,yy,.054),.009,'Machined',32)
                lathe(g,'Pressed round foot',Frame((xx,yy,0),(1,0,0),(0,0,1)),[(.001,.026),(.004,.032),(.010,.032),(.015,.023)],'RubberGrip',48)
                for zz in (.246,.805):bolt(g,(xx+.031,yy,zz),(1,0,0),.005)
        for dy in (-d/2+.033,d/2-.033):
            profile(g,'Pressed apron channel',[(-.023,-.047),(.023,-.047),(.023,-.042),(-.018,-.042),(-.018,.042),(.023,.042),(.023,.047),(-.023,.047)],Frame((x,y+dy,.830),(0,1,0),(0,0,1)),w-.045,'RackPaint',.0014)
        for dx in (-w/2+.029,w/2-.029):
            profile(g,'Side apron folded channel',[(-.022,-.047),(.022,-.047),(.022,-.042),(-.017,-.042),(-.017,.042),(.022,.042),(.022,.047),(-.022,.047)],Frame((x+dx,y,.830),(1,0,0),(0,0,1)),d-.082,'RackPaint',.0014)
        box(g,'Lower pressed storage pan',(x,y,.205),(w-.079,d-.083,.004),'RackPaint',.001)
        for dy in (-d/2+.042,d/2-.042):box(g,'Pan upturned lip',(x,y+dy,.216),(w-.077,.004,.025),'RackPaint',.001)
        for dx in (-w/2+.040,w/2-.040):box(g,'Pan return flange',(x+dx,y,.216),(.004,d-.083,.025),'RackPaint',.001)
        for dx in (-w/2+.045,w/2-.045):
            for dy in (-d/2+.05,d/2-.05):
                ff=Frame((x+dx,y+dy,.820),(1 if dx<0 else -1,0,0),(0,0,-1))
                profile(g,'Welded triangular knee brace',rounded([(0,0),(.105,0),(0,.105)],.007,5),ff,.006,'RackPaint',.001)
    # Long planks retain planar working surfaces, rounded end cuts and irregular worn arrises.
    for k in range(6):
        first=k<3;i=k%3;length=2.26 if first else 1.64;width=(.76 if first else .68)/3-.003
        center=Vector((.17+(i+.5)*.76/3,2.61,.908) if first else (1.77,3.39+(i+.5)*.68/3,.908))
        long=Vector((0,1,0)) if first else Vector((1,0,0));cross=Vector((1,0,0)) if first else Vector((0,1,0))
        radius=.0035;hw=width/2;hh=.031
        section=rounded([(-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh)],radius,7);N=len(section);vs=[];fs=[];steps=100
        for j in range(steps+1):
            t=j/steps;along=(t-.5)*length;end_round=.002*(math.exp(-(t/.012)**2)+math.exp(-((1-t)/.012)**2))
            for across,z in section:
                wear=(.00025+.00055*(.5+.5*math.sin(t*61+k*3))**6)*min(1,abs(across)/(hw-.006))**10
                side=1 if across>0 else -1
                p=center+long*along+cross*(across-side*(wear+end_round))
                p.z+=z-(wear if z>hh-.006 else 0);vs.append(p)
        for j in range(steps):
            for i2 in range(N):a=j*N+i2;b=j*N+(i2+1)%N;fs.append((a,b,b+N,a+N))
        fs.extend([tuple(reversed(range(N))),tuple(steps*N+i2 for i2 in range(N))])
        ob=part('BenchTop','Worn long grain ash plank '+str(k+1),vs,fs,'Timber',True);ob.data.materials.append(MATS['EndGrain'])
        for face in ob.data.polygons:
            end=face.index>=len(ob.data.polygons)-2
            if end:face.material_index=1;face.use_smooth=False
            for li in face.loop_indices:
                vi=ob.data.loops[li].vertex_index;v=ob.data.vertices[vi].co-center
                ob.data.uv_layers.active.data[li].uv=((v.dot(cross)/width+.5),(v.z/.062+.5) if end else (v.dot(long)/2+.5))
        # A few tapered checks at cut ends, aligned with the wood fibres.
        for sign in (-1,1):
            for off,ln in [(-.044,.041),(.061,.026)]:
                a=center+long*(sign*(length/2-.002))+cross*off;a.z=.9392
                b=a-long*sign*ln
                profile('BenchWear','Fine open end-grain check',[(-.00025,0),(.00035,0),(0,ln)],Frame(a,cross,-long*sign),.00012,'RubberGrip',0)
    for x,y in [(.235,1.56),(.865,1.56),(.235,3.67),(.865,3.67),(1.015,3.445),(2.525,3.445),(1.015,4.015),(2.525,4.015)]:
        cylinder('BenchDetail','Flush countersunk bench screw',(x,y,.9385),(x,y,.9398),.0042,'Machined',32)
        sweep('BenchDetail','Screwdriver slot',[(x-.0027,y,.9400),(x+.0027,y,.9400)],.00035,'Forged',8,False)

def build_cloth():
    # Gravity drape against the real bench envelope. This is production geometry generation.
    g='Rag';nx,ny=49,33;vs=[];fs=[]
    for j in range(ny):
        v=j/(ny-1)
        for i in range(nx):
            t=i/(nx-1);xx=.57+t*.54;yy=2.08+v*.32+.017*math.sin(t*4)
            zz=.951+.009*math.sin(t*17+v*6)*math.sin(math.pi*v)**2+.004*math.sin(v*23+t*11)
            vs.append((xx,yy,zz))
    for j in range(ny-1):
        for i in range(nx-1):a=j*nx+i;fs.append((a,a+1,a+1+nx,a+nx))
    cloth=part(g,'Gravity draped heavy cotton service rag',vs,fs,'Canvas',True)
    for face in cloth.data.polygons:
        for li in face.loop_indices:
            vi=cloth.data.loops[li].vertex_index;cloth.data.uv_layers.active.data[li].uv=(vi%nx/(nx-1),vi//nx/(ny-1))
    support=box('_simulation','Bench collision envelope',(.55,2.61,.908),(.76,2.26,.062),'Timber',.003)
    active(support)
    for mod in list(support.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    support.modifiers.new('Cloth tabletop collision','COLLISION');support.collision.thickness_outer=.0015
    pin=cloth.vertex_groups.new(name='Fabric caught beneath tool at inside corner')
    anchor_ids=[j*nx+i for j in range(12,21) for i in range(3,7)]
    pin.add(anchor_ids,1,'REPLACE')
    for index in anchor_ids:cloth.data.vertices[index].co.z=.941
    mod=cloth.modifiers.new('Gravity and friction drape','CLOTH');s=mod.settings;s.quality=7;s.mass=.32;s.tension_stiffness=24;s.compression_stiffness=24;s.shear_stiffness=12;s.bending_stiffness=.25;s.vertex_group_mass=pin.name
    mod.collision_settings.use_self_collision=True;mod.collision_settings.self_distance_min=.002;mod.collision_settings.distance_min=.0015
    scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=65
    for frame in range(1,66):scene.frame_set(frame)
    active(cloth);bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(support,do_unlink=True);PARTS.pop('_simulation',None)
    sub=cloth.modifiers.new('Soft cloth silhouette','SUBSURF');sub.levels=1;sub.render_levels=1
    solid=cloth.modifiers.new('Woven fabric body','SOLIDIFY');solid.thickness=.0012
    # Stitched hem follows the settled outer boundary.
    for ids in ([j*nx for j in range(ny)],[j*nx+nx-1 for j in range(ny)],list(range(nx)),list(range((ny-1)*nx,ny*nx))):
        sweep(g,'Turned and stitched rag hem',[cloth.data.vertices[i].co for i in ids],.001,'Canvas',10,False)
    scene.frame_set(1)
