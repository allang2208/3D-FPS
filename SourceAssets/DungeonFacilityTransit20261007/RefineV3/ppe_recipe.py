"""Moulded half masks, cartridge filter construction and stitched fabric protection pouches."""
import math
import bpy,bmesh
from mathutils import Vector

def contents(c):
    finish=c['finish'];box=c['box'];cylinder=c['cylinder'];tube=c['tube'];torus=c['torus'];parts=c['parts']
    def curved(points,r,mat):
        cu=bpy.data.curves.new('Relaxed tube','CURVE');cu.dimensions='3D';cu.resolution_u=12;cu.bevel_depth=r;cu.bevel_resolution=3;cu.use_fill_caps=True
        sp=cu.splines.new('BEZIER');sp.bezier_points.add(len(points)-1)
        for p,co in zip(sp.bezier_points,points):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
        ob=bpy.data.objects.new('Flexible detail',cu);bpy.context.collection.objects.link(ob);c['select'](ob);bpy.ops.object.convert(target='MESH');ob=bpy.context.object
        for f in ob.data.polygons:f.use_smooth=True
        return finish(ob,mat,0)
    def mesh(name,vs,fs,mat,smooth=True):
        me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
        for f in me.polygons:f.use_smooth=smooth
        return finish(ob,mat,0)
    def ellipse(cx,cy,cz,rx,ry):return [(cx+rx*math.cos(i*math.tau/64),cy+ry*math.sin(i*math.tau/64),cz) for i in range(65)]
    def buckle(x,y,z):
        for dx in (-.011,.011):box((x+dx,y,z),(.004,.030,.005),'Steel',.001)
        for dy in (-.013,0,.013):box((x,y+dy,z),(.023,.004,.005),'Steel',.001)
    # Cloth pouches are softly subdivided forms, with actual fold, piping, zip and webbing.
    for k,cx in enumerate((-.145,.125)):
        for level in range(2):
            cz=.551+level*.049;sy=.011*(-1 if level else 1);w=.224;depth=.275
            ob=box((cx,sy,cz),(w,depth,.049),'Fabric',.014)
            c['select'](ob);sub=ob.modifiers.new('Soft cloth subdivision','SUBSURF');sub.levels=2;bpy.ops.object.modifier_apply(modifier=sub.name)
            for v in ob.data.vertices:
                p=v.co;edge=min(1,abs(p.x)/(w*.5));p.z+=.0018*math.sin(p.x*131+p.y*87)*edge
            for f in ob.data.polygons:f.use_smooth=True
            outline=[(cx-w*.42,sy-depth*.46,cz+.017),(cx+w*.42,sy-depth*.46,cz+.017),(cx+w*.47,sy,cz+.017),(cx+w*.42,sy+depth*.46,cz+.017),(cx-w*.42,sy+depth*.46,cz+.017),(cx-w*.47,sy,cz+.017),(cx-w*.42,sy-depth*.46,cz+.017)]
            curved(outline,.0018,'Seam')
            for j in range(37):
                xx=cx-.089+j*.005;box((xx,sy+depth*.475,cz+.007),(.0018,.0024,.0031),'Steel',.00035)
            box((cx+.077,sy+depth*.481,cz+.010),(.018,.006,.010),'Steel',.0015)
            curved([(cx+.077,sy+depth*.48,cz+.01),(cx+.07,sy+depth*.5+.019,cz+.012),(cx+.083,sy+depth*.5+.028,cz+.008),(cx+.091,sy+depth*.5+.018,cz+.010)],.0018,'Steel')
            if level:
                for xx in (cx-.067,cx+.067):
                    box((xx,sy,cz+.026),(.016,.263,.003),'Webbing',.001);buckle(xx,sy+.05,cz+.029)
                c['ppe_label']((cx,sy+.085,cz+.028),.080,.020,0,True)
    # Two compact anatomically shaped face cups rest on the centre shelf.
    for mx in (-.145,.145):
        my=.017;bz=1.015;nt=72;nr=16;vs=[];fs=[]
        # Inner and outer shells share a thick rounded sealing rim; a raised narrow nose
        # and full cheek/chin profile replace the former flattened sphere silhouette.
        for inner in (False,True):
            for j in range(nr+1):
                r=max(.001,j/nr)
                for i in range(nt):
                    t=math.tau*i/nt;sn=math.sin(t);cs=math.cos(t);rx=.077*(1-.22*max(cs,0));rz=.084 if cs>0 else .064
                    xx=rx*r*sn;zz=.076+rz*r*cs;yy=.061*math.sqrt(max(0,1-r*r))+.008+max(cs,0)**4*.012*r
                    if inner:yy-=.003;xx*=.966;zz=.076+(zz-.076)*.966
                    vs.append((mx+xx,my+yy,bz+zz))
            off=(nr+1)*nt if inner else 0
            for j in range(nr):
                for i in range(nt):
                    a=off+j*nt+i;b=off+j*nt+(i+1)%nt;d=a+nt;e=b+nt;fs.append((a,d,e,b) if inner else (a,b,e,d))
        nn=(nr+1)*nt
        for i in range(nt):
            a=nr*nt+i;b=nr*nt+(i+1)%nt;fs.append((a,a+nn,b+nn,b))
        fs.extend([tuple(reversed(range(nt))),tuple(nn+i for i in range(nt))]);mesh('Moulded face seal',vs,fs,'Rubber')
        # Raised front exhalation housing and a protective slotted cap.
        cylinder((mx,my+.071,bz+.058),.023,.018,'Charcoal',axis=(0,1,0),sides=64)
        torus((mx,my+.083,bz+.058),.021,.0022,'Steel',axis=(0,1,0))
        for z in (-.011,-.005,.001,.007,.013):
            width=2*math.sqrt(max(0,.017**2-z*z));box((mx,my+.084,bz+.058+z),(width,.002,.0018),'Rubber',.0005)
        for sign in (-1,1):
            axis=Vector((sign*.27,.963,0));pos=Vector((mx+sign*.063,my+.040,bz+.046))
            cylinder(pos,.026,.017,'Rubber',axis=axis,sides=64)
            cylinder(pos+axis*.026,.031,.041,'Gray',axis=axis,sides=64)
            for offset in (.009,.031,.048):torus(pos+axis*offset,.031,.0020,'Charcoal',axis=axis)
            # Cartridge bayonet ribs, concentric intake guard and real narrow grille slats.
            u=Vector((axis.y,-axis.x,0));v=Vector((0,0,1));face=pos+axis*.048
            for i in range(24):
                t=math.tau*i/24;q=pos+axis*.028+(u*math.cos(t)+v*math.sin(t))*.031
                cylinder(q,.0012,.026,'Charcoal',axis=axis,sides=8)
            cylinder(face,.028,.002,'Filter',axis=axis,sides=64)
            for j in range(-5,6):
                zz=j*.0046;half=math.sqrt(max(.00001,.026**2-zz*zz));tube([face+axis*.002+v*zz-u*half,face+axis*.002+v*zz+u*half],.00085,'Charcoal')
            torus(face+axis*.003,.027,.0016,'Steel',axis=axis)
            cylinder((mx+sign*.072,my-.005,bz+.104),.008,.008,'Gray',axis=(0,1,0),sides=32)
        # Soft harness lies behind the mask and returns to both anchor points.
        for dz in (0,.037):
            path=[(mx-.070,my,bz+.105+dz),(mx-.095,my-.055,bz+.059),(mx-.074,my-.126,1.030),(mx+.074,my-.126,1.030),(mx+.095,my-.055,bz+.059),(mx+.07,my,bz+.105+dz)]
            ob=curved(path,.0035,'Webbing');ob.name='Relaxed elastic harness'
        buckle(mx-.088,my-.057,bz+.048)
    # Upper shelf: two replaceable pleated filters, crimp rings, caps and printed bands.
    for i,cx in enumerate((-.082,.082)):
        cy=-.006;z0=1.387;nt=192;vs=[];fs=[]
        for z in (z0+.01,z0+.148):
            for j in range(nt):
                r=.038 if j%2 else .044;vs.append((cx+r*math.cos(math.tau*j/nt),cy+r*math.sin(math.tau*j/nt),z))
        for j in range(nt):fs.append((j,(j+1)%nt,(j+1)%nt+nt,j+nt))
        mesh('Pleated cellulose element',vs,fs,'Filter',False)
        for z in (z0+.007,z0+.153):
            cylinder((cx,cy,z),.045,.012,'Gray',sides=96);torus((cx,cy,z),.044,.002,'Steel')
        cylinder((cx,cy,z0+.163),.021,.012,'Rubber',sides=64)
        torus((cx,cy,z0+.170),.018,.002,'Steel')
        for z in (z0+.053,z0+.109):torus((cx,cy,z),.0445,.0018,'Steel')
        c['ppe_label']((cx,cy+.046,z0+.080),.061,.01525,1,False)
