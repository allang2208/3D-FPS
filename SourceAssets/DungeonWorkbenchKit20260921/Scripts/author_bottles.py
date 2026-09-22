"""Two original reusable containers, curved adhesive labels and detailed closures."""
from pathlib import Path
import bpy,json,math
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';WORLD=Matrix(((-1,0,0,10),(0,-1,0,0),(0,0,1,0),(0,0,0,1)))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
recipes=json.loads((OUT/'bottle-materials.json').read_text());M={};parts=[]
for key,r in recipes.items():
    m=bpy.data.materials.new('WBKBottle_'+key);m.use_nodes=True;p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if not p:p=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    output=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None) or m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(p.outputs['BSDF'],output.inputs['Surface']);p.inputs['Metallic'].default_value=r['metallic']
    for ch,path in r['maps'].items():
        t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(path)
        if ch!='BaseColor':t.image.colorspace_settings.name='Non-Color'
        if ch=='Normal':
            n=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(t.outputs['Color'],n.inputs['Color']);m.node_tree.links.new(n.outputs['Normal'],p.inputs['Normal'])
        else:m.node_tree.links.new(t.outputs['Color'],p.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[ch]])
    M[key]=m

def mesh(name,verts,faces,uvs,mat,smooth=True):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();me.materials.append(M[mat]);uv=me.uv_layers.new(name='UVMap')
    for f in me.polygons:
        f.use_smooth=smooth
        for li,p in zip(f.loop_indices,uvs[f.index]):uv.data[li].uv=p
    ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob);parts.append(ob);return ob

def lathe(name,c,profile,mat,sides=128,ribs=0,amp=0):
    vs=[];fs=[];uvs=[];rings=[];height=max(z for z,r in profile);low=min(z for z,r in profile)
    for j,(z,r) in enumerate(profile):
        if r==0:
            rings.append([len(vs)]);vs.append((c[0],c[1],c[2]+z));continue
        ring=[]
        for i in range(sides+1):
            a=math.tau*i/sides;rr=r+(amp*(.5+.5*math.cos(a*ribs))**3 if ribs and 1<j<len(profile)-2 else 0)
            ring.append(len(vs));vs.append((c[0]+rr*math.sin(a),c[1]-rr*math.cos(a),c[2]+z))
        rings.append(ring)
    for j in range(len(profile)-1):
        for i in range(sides):
            v0=(profile[j][0]-low)/max(.001,height-low);v1=(profile[j+1][0]-low)/max(.001,height-low)
            a,b=rings[j:j+2]
            if len(a)==1:
                fs.append((a[0],b[i+1],b[i]));uvs.append([((i+.5)/sides,v0),((i+1)/sides,v1),(i/sides,v1)])
            elif len(b)==1:
                fs.append((a[i],a[i+1],b[0]));uvs.append([(i/sides,v0),((i+1)/sides,v0),((i+.5)/sides,v1)])
            else:
                fs.append((a[i],a[i+1],b[i+1],b[i]));uvs.append([(i/sides,v0),((i+1)/sides,v0),((i+1)/sides,v1),(i/sides,v1)])
    return mesh(name,vs,fs,uvs,mat)

def radius_at(profile,z):
    for (za,ra),(zb,rb) in zip(profile,profile[1:]):
        if za<=z<=zb:return ra+(rb-ra)*(z-za)/(zb-za) if zb>za else rb
    return profile[-1][1]

def label(c,profile,z0,z1,mat,angle):
    nx=80;ny=16;vs=[];fs=[];uvs=[];half=1.12
    for j in range(ny+1):
        v=j/ny;z=z0+(z1-z0)*v;edge=min(v,1-v)*(z1-z0);corner=.002
        inset=(corner-math.sqrt(max(0,corner**2-(corner-edge)**2)))/.041 if edge<corner else 0
        for i in range(nx+1):
            u=i/nx;a=angle+(u*2-1)*(half-inset);r=radius_at(profile,z)+.00012
            vs.append((c[0]+r*math.sin(a),c[1]-r*math.cos(a),c[2]+z))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1));uvs.append([(i/nx,j/ny),((i+1)/nx,j/ny),((i+1)/nx,(j+1)/ny),(i/nx,(j+1)/ny)])
    mesh('Conforming adhesive label '+mat,vs,fs,uvs,mat)

def tube(name,points,radii,mat,sides=32):
    vs=[];fs=[];uvs=[];previous_t=None
    for j,p in enumerate(points):
        p=Vector(p);t=(Vector(points[min(j+1,len(points)-1)])-Vector(points[max(j-1,0)])).normalized()
        if previous_t is not None and t.dot(previous_t)<0:t=-t
        previous_t=t.copy();axis=Vector((0,1,0));a=t.cross(axis).normalized();b=t.cross(a)
        for i in range(sides+1):
            ang=i*math.tau/sides;vs.append(p+(a*math.cos(ang)+b*math.sin(ang))*radii[j])
    for j in range(len(points)-1):
        for i in range(sides):
            a=j*(sides+1)+i;fs.append((a,a+1,a+sides+2,a+sides+1));uvs.append([(i/sides,j/(len(points)-1)),((i+1)/sides,j/(len(points)-1)),((i+1)/sides,(j+1)/(len(points)-1)),(i/sides,(j+1)/(len(points)-1))])
    mesh(name,vs,fs,uvs,mat)

def finish(name):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in parts:ob.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();ob=parts[0];ob.name=name;ob.data.transform(WORLD);ob.data.update();parts.clear()

c=(1.11,3.97,.9392)
oil=[(0,0),(.0002,.034),(.001,.038),(.003,.0405),(.006,.0415),(.009,.0415),(.011,.0408),(.016,.0407),(.095,.0407),(.108,.0405),(.114,.0399),(.120,.0385),(.128,.0343),(.135,.0278),(.141,.0222),(.146,.020),(.153,.020),(.154,.018),(.154,0)]
lathe('Pressed enamel oil reservoir',c,oil,'OilPaint')
lathe('Rolled lower steel seam',c,[(.002,.039),(.003,.0411),(.005,.0418),(.007,.0415),(.008,.0406)],'SpoutSteel')
lathe('Oil closure rubber seal',c,[(.146,.020),(.147,.0215),(.149,.0215),(.150,.020)],'CapPolymer')
lathe('Ribbed machined oil closure',c,[(.148,.0198),(.149,.021),(.151,.021),(.164,.021),(.166,.020),(.167,.0185),(.167,0)],'CapPolymer',256,48,.00055)
lathe('Spout threaded ferrule',c,[(.166,0),(.166,.009),(.167,.009),(.169,.008),(.172,.006),(.174,.0045),(.174,0)],'SpoutSteel',96)
# Continuous curved spout, including a visible open tube mouth.
P=[Vector((c[0],c[1],c[2]+.171)),Vector((c[0]+.004,c[1],c[2]+.210)),Vector((c[0]+.002,c[1],c[2]+.224)),Vector((c[0]+.053,c[1],c[2]+.249))]
pts=[]
for i in range(65):
    t=i/64;pts.append((1-t)**3*P[0]+3*(1-t)**2*t*P[1]+3*(1-t)*t*t*P[2]+t**3*P[3])
rs=[.00265-(i/64)*.0008 for i in range(65)];t=(pts[-1]-pts[-2]).normalized()
tube('Drawn tapered steel spout',pts+[pts[-1],pts[-1]-t*.004],rs+[rs[-1]-.00055,rs[-1]-.00055],'SpoutSteel',40)
label(c,oil,.026,.098,'OilLabel',-.075);finish('SM_WBKBottle_OilCan')

c=(1.24,3.97,.9392)
cleaner=[(0,0),(.0002,.033),(.002,.0375),(.005,.0405),(.009,.041),(.015,.0412),(.125,.0412),(.139,.0407),(.149,.0387),(.160,.0345),(.172,.0275),(.181,.0208),(.185,.020),(.191,.020),(.192,.018),(.192,0)]
lathe('Moulded red HDPE service bottle',c,cleaner,'CleanerPlastic')
lathe('Tamper collar with moulded lip',c,[(.185,.020),(.186,.022),(.189,.022),(.190,.021)],'CapPolymer',192,48,.00016)
lathe('Fine ribbed polypropylene screw cap',c,[(.190,.0208),(.191,.022),(.193,.022),(.205,.022),(.208,.0215),(.210,.020),(.211,.017),(.211,0)],'CapPolymer',256,48,.00045)
for side in (-1,1):
    points=[]
    for j in range(46):
        z=.012+j/45*.168;r=radius_at(cleaner,z);a=side*math.pi/2;points.append((c[0]+(r-.000025)*math.sin(a),c[1]-(r-.000025)*math.cos(a),c[2]+z))
    tube('Fine mould parting witness',points,[.000085]*len(points),'CleanerPlastic',8)
label(c,cleaner,.038,.127,'CleanerLabel',.065);finish('SM_WBKBottle_Degreaser')
for im in bpy.data.images:
    if im.source=='FILE':im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonWorkbenchBottles.blend'))
print('WORKBENCH_BOTTLES_AUTHORED_NO_RENDER')
