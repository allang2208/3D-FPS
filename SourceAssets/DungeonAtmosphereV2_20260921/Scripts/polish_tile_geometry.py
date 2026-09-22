"""Refine the existing wall tile groups while retaining the authored building."""
import bpy
import bmesh
import math
import json
import random
import shutil
import zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/TilePolish';OUT.mkdir(exist_ok=True)
source=ROOT/'Authored/DungeonAtmosphereV2_Structure.blend'
backup=OUT/'DungeonAtmosphereV2_Structure_PreTilePolish.blend'
if not backup.exists():shutil.copy2(source,backup)
bpy.ops.wm.open_mainfile(filepath=str(backup))
for image in bpy.data.images:
    if image.filepath.startswith('//'):
        image.filepath=str(source.parent/image.filepath[2:])
scene=bpy.context.scene
recipes=json.loads((OUT/'material-manifest.json').read_text())
mats=[]
for name,maps in recipes.items():
    mat=bpy.data.materials.new('V2_'+name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes.get('Principled BSDF')
    for channel,input_name in [('BaseColor','Base Color'),('Roughness','Roughness'),('Normal','Normal')]:
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(maps[channel],check_existing=True)
        tex.image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
        pin=tex.outputs['Color']
        if channel=='Normal':
            n=nodes.new('ShaderNodeNormalMap');links.new(pin,n.inputs['Color']);pin=n.outputs['Normal']
        links.new(pin,p.inputs[input_name])
    mats.append(mat)

groups={};stats={'tiles':0,'missing':0,'fractured':0,'corner_chipped':0,'adhesive_ridges':0}
def group(name):return groups.setdefault('SM_V2_'+name+'_Tiles',{'v':[],'f':[],'m':[],'uv':[]})

def wall(name,axis,a,b,fixed,inside):
    g=group(name);r=random.Random(zlib.crc32(f'{name}:{axis}:{a}:{b}:{fixed}'.encode()))
    def transform(t,d,z):return (t,fixed+inside*d,z) if axis=='x' else (fixed+inside*d,t,z)
    def face(vs,material,uv=None):
        # The source plane is XZ with its normal facing -Y. Correct axis/side
        # parity before exporting; the exposed glaze always faces the corridor.
        if (axis=='x' and inside==1) or (axis=='y' and inside==-1):
            vs=list(reversed(vs));uv=list(reversed(uv)) if uv else None
        start=len(g['v']);g['v'].extend([transform(*p) for p in vs]);g['f'].append(tuple(range(start,start+len(vs))))
        g['m'].append(material);g['uv'].append(uv or [(p[0]/.5,p[2]/.5) for p in vs])
    def prism(points,depth,thick,material=0,cell=0,rect=None,tilt=0):
        # Canonical positive XZ winding for all polygon fronts.
        area=sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))
        if area<0:points=list(reversed(points))
        if rect is None:
            rect=(min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points))
        x0,z0,x1,z1=rect
        front=[(x,depth+(x-(x0+x1)/2)*tilt,z) for x,z in points]
        row,col=divmod(cell,8)
        uv=[((col+.045+.91*(x-x0)/max(.001,x1-x0))/8,1-(row+.045+.91*(z1-z)/max(.001,z1-z0))/8) for x,z in points]
        face(front,material,uv if material==0 else None)
        for i in range(len(points)):
            j=(i+1)%len(points);x,z=points[i];xx,zz=points[j]
            face([front[j],front[i],(x,depth-thick,z),(xx,depth-thick,zz)],2 if material==0 else material)
    # Continuous uneven mortar bed fills the grout and remains visible in losses.
    nx=max(1,math.ceil((b-a)/.075));nz=20
    heights=[[.124+r.uniform(-.002,.002) for j in range(nz+1)] for i in range(nx+1)]
    for i in range(nx):
        for j in range(nz):
            x0=a+(b-a)*i/nx;x1=a+(b-a)*(i+1)/nx;z0=.155+j*1.435/nz;z1=.155+(j+1)*1.435/nz
            face([(x0,heights[i][j],z0),(x1,heights[i+1][j],z0),(x1,heights[i+1][j+1],z1),(x0,heights[i][j+1],z1)],1)
    span=b-a
    count=max(1,round(span/3.4))
    patches=[(a+span*(i+.4+r.random()*.25)/count,r.uniform(.35,1.3),r.uniform(.42,.83),r.uniform(.28,.5)) for i in range(count)]
    if name=='Corridor_North' and a==0:patches=[(3.8,.93,.74,.39),(6.9,.38,.53,.34)]
    if name=='Corridor_South' and a==0:patches=[(1.55,.55,.65,.39),(3.83,1.3,.36,.24)]
    for row in range(9):
        z=.24+row*.158;x=a+.155
        while x<b-.10:
            stats['tiles']+=1
            impact=max(math.exp(-((x-px)/sx)**2-((z-pz)/sz)**2) for px,pz,sx,sz in patches)
            damp=max(math.exp(-((x-px)/(sx*.75))**2)*(.32+.68*(1-z/1.8)) for px,pz,sx,sz in patches)
            missing=impact+r.uniform(-.16,.16)>.56
            hw=min(.152,(b-x)-.002);hh=.076+r.uniform(-.0007,.0007)
            cx=x+r.uniform(-.0015,.0015);cz=z+r.uniform(-.0015,.0015)
            x0,x1=cx-hw,cx+hw;z0,z1=cz-hh,cz+hh
            rect=(x0,z0,x1,z1);depth=.144+r.uniform(-.0017,.0017)
            if missing:
                stats['missing']+=1
                # Small runs of original combed adhesive remain in the recess.
                for k in range(15):
                    if r.random()<.20:continue
                    qx=x0+.011+k*.019+r.uniform(-.004,.004);qz=z0+r.uniform(.002,.04);end=z1-r.uniform(.002,.032)
                    phase=math.sin(x*1.17)*2;lean=math.sin(x*.9+z*1.7)*.29
                    for seg in range(4):
                        za=qz+(end-qz)*seg/4;zb=qz+(end-qz)*(seg+1)/4
                        xa=max(x0+.005,min(x1-.005,qx+math.sin(za*7+phase)*.014+(za-z)*lean))
                        xb=max(x0+.005,min(x1-.005,qx+math.sin(zb*7+phase)*.014+(zb-z)*lean))
                        # Shallow rounded comb crest, continuous with its bed.
                        crest=.1257+r.uniform(-.0003,.0003)
                        face([(xa-.004,.124,za),(xa,crest,za),(xb,crest,zb),(xb-.004,.124,zb)],1)
                        face([(xa,crest,za),(xa+.004,.124,za),(xb+.004,.124,zb),(xb,crest,zb)],1)
                    stats['adhesive_ridges']+=1
                if r.random()<.52:
                    pts=[(x0,z0),(x0+r.uniform(.03,.13),z0),(x0+r.uniform(.008,.065),z0+r.uniform(.025,.095)),(x0,z0+r.uniform(.045,.14))]
                    # Bond the retained fragment to the old bed; a small rough
                    # adhesive footprint also supports its visible broken edge.
                    center=(sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts))
                    glue=[(center[0]+(px-center[0])*1.045,center[1]+(pz-center[1])*1.045) for px,pz in pts]
                    prism(glue,.135,.016,1)
                    prism(pts,depth,.016,0,r.randrange(48,64),rect)
                x+=.31;continue
            cell=r.randrange(0,32)
            # Grout sits close to the glaze face, with the older recessed bed
            # only visible where a tile has actually detached.
            face([(x-.155,.138,z-.079),(x+.155,.138,z-.079),(x+.155,.138,z+.079),(x-.155,.138,z+.079)],1)
            if damp>.25:cell=r.randrange(32,48)
            if r.random()<.09+impact*.36:cell=r.randrange(48,64)
            chip=(r.uniform(.008,.026) if r.random()<.17+impact*.5 else r.uniform(.001,.003))
            if chip>.007:stats['corner_chipped']+=1
            # Different corners wear independently; no identical diagonal notch.
            cuts=[chip if r.random()<.5 else r.uniform(.001,.004) for _ in range(4)]
            bl,br,tr,tl=cuts
            pts=[(x0+bl,z0),(x1-br,z0),(x1-br*.65,z0+br*.28),(x1-br*.38,z0+br*.24),
                 (x1-br*.30,z0+br*.7),(x1,z0+br),(x1,z1-tr),(x1-tr*.48,z1-tr*.66),
                 (x1-tr*.41,z1-tr*.34),(x1-tr,z1),(x0+tl,z1),(x0,z1-tl),(x0,z0+bl)]
            tilt=r.uniform(-.005,.005)
            if impact>.25 and r.random()<.16:
                stats['fractured']+=1
                # Two separate ceramic islands, a narrow open split and one
                # lifted edge catch light without disrupting the installed grid.
                q1=cx+r.uniform(-.07,.04);q2=q1+r.uniform(-.045,.045);gap=.0015
                prism([(x0,z0),(q1-gap,z0),(q2-gap,z1),(x0,z1)],depth,.018,0,cell,rect,tilt)
                prism([(q1+gap,z0),(x1,z0),(x1,z1),(q2+gap,z1)],depth+.0025,.018,0,cell,rect,-.018)
            else:prism(pts,depth,.018,0,cell,rect,tilt)
            x+=.31

for a,b in [(0,4.4),(9.6,14.4),(16.2,26)]:wall('Corridor_South','x',a,b,0,1)
for a,b in [(0,8.3),(12.7,15),(21.5,22)]:wall('Corridor_North','x',a,b,4,-1)
wall('EntryEnd','y',0,4,0,1)
for name,axis,a,b,k,s in [('Workshop','x',4,10,-4.2,1),('Workshop','y',-4.2,0,4,1),('Workshop','y',-4.2,0,10,-1),
 ('MachineBay','x',8,13,8,-1),('MachineBay','y',4,8,8,1),('MachineBay','y',4,8,13,-1),
 ('ServiceRecess','x',14,16.6,-2.2,1),('ServiceRecess','y',-2.2,0,14,1),('ServiceRecess','y',-2.2,0,16.6,-1),
 ('Dogleg','y',0,10,26,-1),('Dogleg','y',4,14,22,1),('EndLanding','x',22,29,14,-1),('EndLanding','y',10,14,29,-1),('EndLanding','x',26,29,10,1)]:
    wall(name,axis,a,b,k,s)

manifest=[]
for name,g in groups.items():
    previous=bpy.data.objects.get(name)
    if previous:bpy.data.objects.remove(previous,do_unlink=True)
    data=bpy.data.meshes.new(name+'_Polished');data.from_pydata(g['v'],[],g['f']);data.update()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    for mat in mats:data.materials.append(mat)
    uv=data.uv_layers.new(name='UVMap')
    for face,mi,coords in zip(data.polygons,g['m'],g['uv']):
        face.material_index=mi
        for li,co in zip(face.loop_indices,coords):uv.data[li].uv=co
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bm.to_mesh(data);bm.free()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    # Explicit front/edge material separation is retained across triangulation.
    mod=obj.modifiers.new('Ceramic bevel highlight','BEVEL');mod.width=.0008;mod.segments=2;mod.limit_method='ANGLE';mod.angle_limit=.7
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=obj.modifiers.new('Export tangents','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    path=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    manifest.append({'name':name,'fbx':str(path),'materials':list(recipes),'triangles':len(obj.data.polygons)})
    obj.select_set(False)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(source))
(OUT/'geometry-manifest.json').write_text(json.dumps({'objects':manifest,'stats':stats,'scope':'Existing tile groups only; all building/prop transforms retained','gameplay_tests':False},indent=2),encoding='utf-8')
print('TILE_GEOMETRY_AUTHORED',json.dumps(stats))
