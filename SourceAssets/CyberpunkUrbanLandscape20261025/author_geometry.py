"""Production meshes in metres: closed furniture, supported park surfaces, exact legacy trims."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parent;OLD=R.parent/'CyberpunkApartmentRebuild20261022'
D=json.loads((R/'layout.json').read_text(encoding='utf8'));OUT=R/'Meshes';OUT.mkdir(exist_ok=True)
report=dict(stage='geometry_authored',meshes=[],tests_run=False)
bpy.ops.wm.read_factory_settings(use_empty=True)

class Build:
    def __init__(self):self.v=[];self.f=[];self.roles=[]
    def mesh(self,v,f,role):
        n=len(self.v);self.v.extend(v);self.f.extend([tuple(i+n for i in face) for face in f]);self.roles.extend([role]*len(f))
    def box(self,p,s,role='Stone'):
        x,y,z=p;a,b,c=[v*.5 for v in s]
        self.mesh([(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),(x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],role)
    def ring(self,p,inner,outer,z0,z1,role='Stone',n=96):
        v=[]
        for z,r in ((z0,inner),(z0,outer),(z1,inner),(z1,outer)):
            v.extend([(p[0]+r*math.cos(i*2*math.pi/n),p[1]+r*math.sin(i*2*math.pi/n),p[2]+z) for i in range(n)])
        f=[]
        for i in range(n):
            j=(i+1)%n;f.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
        self.mesh(v,f,role)
    def cylinder(self,p,r,h,role='Metal',n=48):
        v=[(p[0]+r*math.cos(i*2*math.pi/n),p[1]+r*math.sin(i*2*math.pi/n),p[2]+z) for z in (0,h) for i in range(n)]
        f=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        self.mesh(v,f,role)
    def tube(self,points,r,role='Metal',sides=8):
        v=[]
        for i,p in enumerate(points):
            p=Vector(p);t=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])).normalized();a=t.cross(Vector((0,0,1)))
            if a.length<.01:a=t.cross(Vector((1,0,0)))
            a.normalize();b=t.cross(a).normalized()
            for j in range(sides):v.append(tuple(p+r*(a*math.cos(j*2*math.pi/sides)+b*math.sin(j*2*math.pi/sides))))
        f=[tuple(reversed(range(sides))),tuple(range((len(points)-1)*sides,len(points)*sides))]
        for i in range(len(points)-1):
            for j in range(sides):k=i*sides+j;l=i*sides+(j+1)%sides;f.append((k,l,l+sides,k+sides))
        self.mesh(v,f,role)
    def wedge(self,x0,x1,y0,y1,h0,h1,role='Paving'):
        self.mesh([(x0,y0,0),(x1,y0,0),(x1,y1,0),(x0,y1,0),(x0,y0,h0),(x1,y0,h0),(x1,y1,h1),(x0,y1,h1)],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],role)
    def object(self,name,bevel=.018):
        ground=name.endswith('_Ground')
        if ground:
            # Explicit triangle topology avoids the FBX SDK and BMesh handling
            # collapsed sub-millimetre quads on boolean-clipped surface borders.
            faces=[];roles=[]
            for face,role in zip(self.f,self.roles):
                for j in range(1,len(face)-1):
                    tri=(face[0],face[j],face[j+1])
                    if len(set(tri))<3:continue
                    a,b,c=[Vector(self.v[k]) for k in tri]
                    if (b-a).cross(c-a).length<1e-6:continue
                    faces.append(tri);roles.append(role)
            self.f=faces;self.roles=roles
        mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x,-y,z) for x,y,z in self.v],[],[tuple(reversed(f)) for f in self.f]);mesh.update();obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
        roles=list(dict.fromkeys(self.roles))
        for r in roles:mesh.materials.append(bpy.data.materials.get(r) or bpy.data.materials.new(r))
        for p,r in zip(mesh.polygons,self.roles):p.material_index=roles.index(r)
        if not ground:
            bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
        uv=mesh.uv_layers.new(name='UVMap')
        for p in mesh.polygons:
            ax=max(range(3),key=lambda i:abs(p.normal[i]));dims=[i for i in range(3) if i!=ax]
            for li in p.loop_indices:
                co=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(co[dims[0]]/4,co[dims[1]]/4)
        bpy.context.view_layer.objects.active=obj;obj.select_set(True)
        if bevel:
            mod=obj.modifiers.new('Manufactured edge radii','BEVEL');mod.width=bevel;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.65
            bpy.ops.object.modifier_apply(modifier=mod.name)
            wn=obj.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=40;bpy.ops.object.modifier_apply(modifier=wn.name)
        obj.select_set(False);return obj

def export(obj,key,**extra):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    name='SM_UL_'+key;obj.name=name;path=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
    report['meshes'].append(dict(key=key,name=name,fbx=str(path),roles=[m.name for m in obj.data.materials],triangles=sum(len(p.vertices)-2 for p in obj.data.polygons),**extra))

def bench(b,offset=(0,0,0)):
    x,y,z=offset
    b.box((x,y,z-.1),(2.8,1.15,.2),'Paving')
    for xx in (-.85,.85):
        b.box((x+xx,y,z+.22),(.10,.58,.44),'Metal');b.box((x+xx,y+.28,z+.64),(.08,.08,.65),'Metal')
    for yy in (-.24,-.08,.08,.24):b.box((x,y+yy,z+.46),(2.4,.135,.075),'Copper')
    for zz in (.69,.84):b.box((x,y+.29,z+zz),(2.4,.07,.12),'Copper')
    for xx in (-1.04,1.04):b.tube([(x+xx,y-.25,z+.48),(x+xx,y-.25,z+.65),(x+xx,y+.24,z+.65)],.027,'Metal')

def basin(b,r,p=(0,0,0),jets=False):
    b.cylinder(p,r,.12,'Stone',128);b.ring(p,r-.48,r,.12,.62,'Stone',128)
    b.ring(p,r-.53,r-.48,.18,.55,'Metal',128);b.ring(p,r-.47,r-.35,.62,.66,'Copper',128)
    b.cylinder((p[0],p[1],p[2]+.145),r-.54,.10,'Water',128)
    if jets:
        b.cylinder((p[0],p[1],p[2]+.12),1.8,.48,'Stone',64)
        b.ring(p,1.65,1.81,.6,.64,'Copper',64)
        for i in range(9):
            a=i*2*math.pi/9;c,s=math.cos(a),math.sin(a)
            b.cylinder((p[0]+c*1.4,p[1]+s*1.4,p[2]+.6),.12,.14,'Metal',24)
            pts=[]
            for j in range(33):
                t=j/32;rr=1.4+6.7*t;pts.append((p[0]+c*rr,p[1]+s*rr,p[2]+.74*(1-t)+.245*t+3.5*4*t*(1-t)))
            b.tube(pts,.055,'Flow',10)

builders={}
for kind in ('Bench','Planter','Shelter','Wayfinding','Bin','Fountain','Pool','Terraces','Lookout'):
    b=Build()
    if kind=='Bench':bench(b)
    elif kind=='Planter':
        b.box((0,0,-.03),(2.2,1.1,.34),'Stone')
        for s in (-1,1):b.box((s*1.025,0,.38),(.15,1.1,.54),'Stone');b.box((0,s*.475,.38),(1.9,.15,.54),'Stone')
        b.box((0,0,.46),(1.9,.8,.04),'Soil')
        for s in (-1,1):b.box((s*1.025,0,.67),(.17,1.12,.04),'Copper');b.box((0,s*.475,.67),(1.9,.17,.04),'Copper')
    elif kind=='Shelter':
        # A closed support plinth also meets the original ground 20 cm below.
        b.box((0,0,-.1),(6.4,4.0,.2),'Paving')
        for x in (-2.7,2.7):
            for y in (-1.5,1.5):b.box((x,y,1.55),(.16,.16,3.1),'Metal');b.box((x,y,.06),(.35,.35,.12),'Stone')
        b.box((0,0,3.14),(6.1,3.8,.22),'Metal');b.box((0,0,3.28),(6.3,4.0,.08),'Copper')
        for x in (-2.8,2.8):b.box((x,0,3.01),(.04,3.25,.025),'Warm')
        for i in range(17):b.box((-2.4+i*.3,1.5,1.8),(.09,.10,2.2),'Copper')
        bench(b,(0,.88,0))
    elif kind=='Wayfinding':
        b.box((0,0,-.08),(.65,.65,.24),'Stone');b.box((0,0,1.4),(.12,.12,2.8),'Metal');b.box((0,0,2.35),(1.4,.16,.8),'Metal');b.box((0,-.09,2.35),(1.28,.025,.68),'Rubber')
        for x in (-.42,0,.42):b.box((x,-.111,2.35),(.19,.015,.06),'Teal')
        b.tube([(.49,-.12,2.48),(.62,-.12,2.35),(.49,-.12,2.22)],.025,'Teal')
    elif kind=='Bin':
        b.cylinder((0,0,-.2),.4,.28,'Stone');b.ring((0,0,0),.32,.4,.08,.82,'Metal',48);b.ring((0,0,0),.18,.43,.82,.9,'Copper',48);b.cylinder((0,0,.09),.32,.02,'Rubber',48)
        for i in range(16):a=i*math.pi/8;b.tube([(.402*math.cos(a),.402*math.sin(a),.15),(.402*math.cos(a),.402*math.sin(a),.7)],.012,'Copper')
    elif kind=='Fountain':basin(b,13,jets=True)
    elif kind=='Pool':basin(b,5.2)
    elif kind=='Terraces':
        b.box((0,0,.3),(36,20,.6),'Stone');b.box((0,2.5,.9),(28,15,.6),'Stone')
        b.box((0,0,.605),(35.9,19.9,.01),'Paving');b.box((0,2.5,1.205),(27.9,14.9,.01),'Paving')
        for i in range(4):
            h=(i+1)*.15;b.box((0,-11.4+i*.4,h/2),(8,.4,h),'Paving');b.box((0,-6.4+i*.4,.6+h/2),(8,.4,h),'Paving')
        b.wedge(-18,-15,-22,-10,.025,.6)
        b.wedge(-17,-14,-8,4,.6,1.2)
        b.box((-15.4,4.5,.6),(3.2,1,1.2),'Paving')
        # Rails flank the upper landings; the front stairs and ramps remain open.
        for x in (-13.85,13.85):
            for y in (-3,1,7,9):b.box((x,y,1.75),(.07,.07,1.1),'Metal')
            if x<0:
                b.tube([(x,-4,2.3),(x,3,2.3)],.035,'Metal');b.tube([(x,6,2.3),(x,9.9,2.3)],.035,'Metal')
            else:b.tube([(x,-4,2.3),(x,9.9,2.3)],.035,'Metal')
        basin(b,4.5,(0,3.5,1.21))
        bench(b,(-8,6,1.21));bench(b,(8,6,1.21))
        for x in (-17.8,17.8):b.box((x,0,.63),(.05,18,.025),'Warm')
    elif kind=='Lookout':
        b.box((0,0,.3),(12,10,.6),'Stone');b.box((0,0,.61),(11.9,9.9,.02),'Paving')
        for i in range(4):h=(i+1)*.15;b.box((0,-6.4+i*.4,h/2),(4,.4,h),'Paving')
        b.wedge(6,8.5,-8,4,.025,.6);b.box((7.25,4.5,.3),(2.5,1,.6),'Paving')
        for x in (-5.85,5.85):
            for y in (-4.8,-1.6,1.6):b.box((x,y,1.15),(.07,.07,1.1),'Metal')
            b.tube([(x,-4.8,1.7),(x,2.8,1.7)],.035,'Metal')
        for x in (-5.85,-2,2,5.85):b.box((x,4.85,1.15),(.07,.07,1.1),'Metal')
        b.tube([(-5.85,4.85,1.7),(5.85,4.85,1.7)],.035,'Metal');bench(b,(0,3,.62))
    # Water is a separate mesh and actor so native reflection baking excludes it.
    for water in (False,True):
        keep=[i for i,r in enumerate(b.roles) if (r in ('Water','Flow'))==water]
        if not keep:continue
        part=Build();part.v=b.v[:];part.f=[b.f[i] for i in keep];part.roles=[b.roles[i] for i in keep]
        key=kind+('_Water' if water else '');obj=part.object('SM_UL_'+key,0 if water else .018);export(obj,key,kind='fixture',water=water)

for z in D['zones']:
    b=Build();ox,oy,oz=z['origin']
    for field,h,role in [('paving_triangles',.2,'Paving'),('lawn_triangles',.12,'Lawn')]:
        # Weld shared edges before closing the surface; no internal vertical walls.
        coords=[];idx={};faces=[];edges={}
        def point(p):
            k=(round(p[0]-ox,3),round(p[1]-oy,3))
            if k not in idx:idx[k]=len(coords);coords.append(k)
            return idx[k]
        for tri in z[field]:
            f=[point(p) for p in tri]
            if len(set(f))<3:continue
            a,c,d=[coords[i] for i in f]
            cross=(c[0]-a[0])*(d[1]-a[1])-(c[1]-a[1])*(d[0]-a[0])
            if abs(cross)<1e-6:continue
            if cross<0:f.reverse()
            faces.append(f)
            for i,j in zip(f,f[1:]+f[:1]):k=tuple(sorted((i,j)));edges[k]=None if k in edges else (i,j)
        n=len(coords);v=[(x,y,0) for x,y in coords]+[(x,y,h) for x,y in coords]
        fs=[tuple(reversed(f)) for f in faces]+[tuple(i+n for i in f) for f in faces]+[(i,j,j+n,i+n) for e in edges.values() if e for i,j in [e]]
        b.mesh(v,fs,role)
    obj=b.object('SM_UL_'+z['id']+'_Ground',0)
    export(obj,z['id']+'_Ground',kind='ground',zone=z['id'],origin=z['origin'])
bpy.ops.wm.save_as_mainfile(filepath=str(R/'UrbanLandscape_Source.blend'))

# Trim ONLY the outdated vegetation from the retained street / frontage assets.
for version,filename,names,remove in [('RefinementV16','HarborStreets_Source.blend',['SM_AP16_Trees'],('Bark','Leaves')),('RefinementV18','WaterfrontLife_Source.blend',[f'AP18_Frontage_{i}' for i in range(3)]+[f'AP18_Lookouts_{i}' for i in range(2)],('Leaves',))]:
    bpy.ops.wm.open_mainfile(filepath=str(OLD/version/filename))
    for name in names:
        src=bpy.data.objects[name];obj=src.copy();obj.data=src.data.copy();bpy.context.collection.objects.link(obj)
        bm=bmesh.new();bm.from_mesh(obj.data);bad=[p for p in bm.faces if obj.data.materials[p.material_index].name.removeprefix('AP16_').removeprefix('AP18_') in remove];bmesh.ops.delete(bm,geom=bad,context='FACES');bm.to_mesh(obj.data);bm.free()
        if version=='RefinementV18':
            obj.matrix_world=Matrix.Identity(4)
            for v in obj.data.vertices:x,y,z=v.co;v.co=((-x+10)*1.25,-(y-615)*1.25,(z-90)*1.25)
            # One reflection reverses winding; restore outward orientation.
            bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(obj.data);bm.free()
        key='Retained_'+name.removeprefix('SM_');export(obj,key,kind='trim',actor=name.removeprefix('SM_'),removed_roles=list(remove))
(R/'geometry.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('URBAN_GEOMETRY_AUTHORED',len(report['meshes']),sum(r['triangles'] for r in report['meshes']),flush=True)
