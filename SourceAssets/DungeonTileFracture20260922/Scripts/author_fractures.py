"""Rebuild partial tile cells as bonded, thick ceramic remnants. No rendering."""
import ast
import json
import math
import random
import re
import zlib
from collections import defaultdict
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
CFG=json.loads((ROOT/'Config/fracture.json').read_text())
INPUT=json.loads((ROOT/'Sources/scene-inputs.json').read_text())
PRIOR=ROOT.parent/'DungeonWallRelief20260922'
SOURCE=PRIOR/'Authored/DungeonWallRelief_Source.blend'
BEDCFG=json.loads((PRIOR/'Config/surface.json').read_text())
# Read the existing wall span data without executing the previous producer.
tree=ast.parse((PRIOR/'Scripts/author_walls.py').read_text())
SPANS=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and
           any(isinstance(t,ast.Name) and t.id=='SPANS' for t in n.targets))
TW=CFG['tile_width_m'];TH=CFG['tile_height_m']


def clean(s):return re.sub(r'[._][0-9]{3}$','',s)


def coords(co,span):
    axis,a,b,fixed,inside=span
    return (co.x,(co.y-fixed)*inside,co.z) if axis=='x' else (co.y,(co.x-fixed)*inside,co.z)


def poly_area(p):
    return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p))))*.5


def bed_height(t,z,phase):
    value=(.46*math.sin(t*9.1+z*6.7+phase)+.27*math.sin(t*16.3-z*11.2+phase*.7)
           +.17*math.sin(t*26.4+z*23.1-phase)+.10*math.sin(t*40.2-z*31.7))
    return BEDCFG['bed_center_m']+BEDCFG['bed_amplitude_m']*value


def inset(p,amount):
    cx=sum(x for x,z in p)/len(p);cz=sum(z for x,z in p)/len(p)
    return [(x+(cx-x)*amount/max(math.hypot(cx-x,cz-z),.001),
             z+(cz-z)*amount/max(math.hypot(cx-x,cz-z),.001)) for x,z in p]


def remnant_outline(rect,side,coverage,lateral,r):
    x0,z0,x1,z1=rect;w=x1-x0;h=z1-z0
    along=w if side in ('bottom','top') else h
    across=h if side in ('bottom','top') else w
    fraction=max(CFG['min_retained_fraction'],min(CFG['max_retained_fraction'],coverage))
    knots=[fraction+r.uniform(-.16,.16) for _ in range(5)]
    if lateral<0:knots[0]=min(.87,fraction+.28)
    if lateral>0:knots[-1]=min(.87,fraction+.28)
    knots=[min(.86,max(.14,v)) for v in knots]
    n=max(7,math.ceil(along/.015));broken=[]
    for i in range(n+1):
        s=i/n;q=s*4;k=min(3,int(q));f=q-k
        d=(knots[k]*(1-f)+knots[k+1]*f)*across
        if 0<i<n:
            d-=r.uniform(*CFG['edge_chip_m'])
            if r.random()<.09:d-=r.uniform(.002,.005)
        broken.append((s*along,max(across*.10,d)))
    # Local coordinates run along the intact edge and inward into the tile.
    def world(s,d):
        if side=='bottom':return x0+s,z0+d
        if side=='top':return x1-s,z1-d
        if side=='left':return x0+d,z1-s
        return x1-d,z0+s
    p=[world(0,0),world(along,0)]+[world(s,d) for s,d in reversed(broken)]
    signed=sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))
    if signed<0:p.reverse()
    return p


class Build:
    def __init__(self,span):self.span=span;self.v=[];self.f=[];self.mi=[];self.uv=[]
    def face(self,points,mi,uv):
        axis,a,b,fixed,inside=self.span
        if (axis=='x' and inside==1) or (axis=='y' and inside==-1):
            points=list(reversed(points));uv=list(reversed(uv))
        start=len(self.v)
        self.v.extend((t,fixed+inside*d,z) if axis=='x' else (fixed+inside*d,t,z) for t,d,z in points)
        self.f.append(tuple(range(start,start+len(points))));self.mi.append(mi);self.uv.append(uv)
    def cap(self,p,depth,mi,uvfunc,back=False):
        # Tessellate the 2D ceramic outline explicitly; no triangle-island sampling.
        vec=[Vector((x,z,0)) for x,z in p]
        for tri in tessellate_polygon([vec]):
            indices=list(tri)
            if back:indices.reverse()
            q=[p[i] for i in indices]
            self.face([(x,depth(x,z),z) for x,z in q],mi,[uvfunc(x,z) for x,z in q])
    def sides(self,top,bottom,dt,db,mi,uvfunc=None):
        length=0
        for i in range(len(top)):
            j=(i+1)%len(top);a=top[i];b=top[j];aa=bottom[i];bb=bottom[j]
            edge=math.dist(a,b);scale=CFG['core_texture_size_m']
            uv=([uvfunc(*q) for q in (b,a,aa,bb)] if uvfunc else
                [((length+edge)/scale,0),(length/scale,0),
                 (length/scale,(dt(*a)-db(*aa))/scale),((length+edge)/scale,(dt(*b)-db(*bb))/scale)])
            self.face([(b[0],dt(*b),b[1]),(a[0],dt(*a),a[1]),(aa[0],db(*aa),aa[1]),(bb[0],db(*bb),bb[1])],mi,uv)
            length+=edge


bpy.ops.wm.read_factory_settings(use_empty=True)
names=['SM_WallRelief_'+a['label'].removeprefix('DGN_AV2_').removesuffix('_Tiles') for a in INPUT['actors']]
with bpy.data.libraries.load(str(SOURCE),link=False) as (src,dst):dst.objects=names
for ob in dst.objects:
    if ob is None:raise RuntimeError('Wall source object missing')
    bpy.context.scene.collection.objects.link(ob)

core=bpy.data.materials.new('V2_CeramicFractureCore');core.use_nodes=True
pn=core.node_tree.nodes.get('Principled BSDF');pn.inputs['Base Color'].default_value=(.42,.39,.33,1);pn.inputs['Roughness'].default_value=.9
material_manifest=json.loads((OUT/'material-manifest.json').read_text())
for channel,pin in [('BaseColor','Base Color'),('Roughness','Roughness'),('Normal','Normal')]:
    tex=core.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(material_manifest['channels'][channel],check_existing=True)
    tex.image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
    value=tex.outputs['Color']
    if channel=='Normal':
        n=core.node_tree.nodes.new('ShaderNodeNormalMap');core.node_tree.links.new(value,n.inputs['Color']);value=n.outputs['Normal']
    core.node_tree.links.new(value,pn.inputs[pin])

manifest=dict(source=str(SOURCE),config=CFG,objects=[],tests_run=False)
for entry in INPUT['actors']:
    key=entry['label'].removeprefix('DGN_AV2_').removesuffix('_Tiles')
    obj=bpy.data.objects['SM_WallRelief_'+key];mesh=obj.data
    slots=list(mesh.materials);glaze_ids={i for i,m in enumerate(slots) if m and ('Glaze' in m.name or 'CeramicAtlas' in m.name)}
    old_core_ids={i for i,m in enumerate(slots) if m and 'CeramicCore' in m.name}
    finish_ids={i for i,m in enumerate(slots) if m and 'WallReliefFinish' in m.name}
    repair_ids={i for i,m in enumerate(slots) if m and 'NaturalRepair' in m.name}
    core_id=len(slots);mesh.materials.append(core)
    finish_id=next(iter(finish_ids))
    bm=bmesh.new();bm.from_mesh(mesh);uvlayer=bm.loops.layers.uv.active
    cells=defaultdict(lambda:dict(area=0,largest=0,face=None,faces=[],repair=0,depth=0,slot_area=defaultdict(float)))
    face_cell={}
    for face in bm.faces:
        if face.material_index not in glaze_ids|old_core_ids|finish_ids|repair_ids:continue
        center=face.calc_center_median()
        sid=min(range(len(SPANS[key])),key=lambda i:abs(coords(center,SPANS[key][i])[1]-.14)+
                max(SPANS[key][i][1]-coords(center,SPANS[key][i])[0],0)+max(coords(center,SPANS[key][i])[0]-SPANS[key][i][2],0))
        span=SPANS[key][sid];t,d,z=coords(center,span)
        row=round((z-.24)/TH);col=math.floor((t-span[1])/TW)
        if row<0 or row>8 or col<0 or t>span[2]+.002:continue
        ck=(sid,col,row);face_cell[face]=ck;c=cells[ck];c['faces'].append(face)
        p=[(coords(v.co,span)[0],coords(v.co,span)[2]) for v in face.verts];area=poly_area(p)
        if face.material_index in repair_ids:c['repair']+=area
        if face.material_index not in glaze_ids:continue
        c['area']+=area;c['depth']+=d*area;c['slot_area'][face.material_index]+=area
        if area>c['largest']:
            c['largest']=area
            c['face']=[(coords(loop.vert.co,span),tuple(loop[uvlayer].uv)) for loop in face.loops]
    for ck,c in cells.items():
        sid,col,row=ck;span=SPANS[key][sid]
        left=span[1]+col*TW+.003;right=min(span[1]+(col+1)*TW-.003,span[2]-.003)
        c['coverage']=min(1,c['area']/max((right-left)*.152,1e-8))
        c['rect']=(left,.24+row*TH-.076,right,.24+row*TH+.076)
    partial={k:c for k,c in cells.items() if .00003<c['area'] and c['coverage']<CFG['intact_coverage'] and c['repair']<.001}
    remove=[]
    for face,ck in face_cell.items():
        if ck not in partial:continue
        if face.material_index in glaze_ids|old_core_ids:remove.append(face)
        elif face.material_index in finish_ids:
            ds=[coords(v.co,SPANS[key][ck[0]])[1] for v in face.verts]
            if max(ds)<.1375:remove.append(face)
    builders=[Build(span) for span in SPANS[key]];records=[];kept=0;isolated=0
    for ck,c in sorted(partial.items()):
        sid,col,row=ck;span=SPANS[key][sid]
        r=random.Random(CFG['seed']+zlib.crc32((key+str(ck)).encode()))
        offsets={'left':(-1,0),'right':(1,0),'bottom':(0,-1),'top':(0,1)}
        neighbors={s:cells.get((sid,col+dc,row+dr),{}).get('coverage',0) for s,(dc,dr) in offsets.items()}
        eligible=[s for s,cv in neighbors.items() if cv>=CFG['intact_coverage']]
        if not eligible or c['coverage']<.065:
            isolated+=1;records.append(dict(cell=list(ck),old_coverage=c['coverage'],action='remove_isolated_fragment'));continue
        side=max(eligible,key=lambda s:neighbors[s]+r.uniform(0,.08))
        lateral=0
        first,last={'bottom':('left','right'),'top':('right','left'),'left':('top','bottom'),'right':('bottom','top')}[side]
        lateral=-1 if neighbors[first]>=CFG['intact_coverage'] else 1 if neighbors[last]>=CFG['intact_coverage'] else 0
        p=remnant_outline(c['rect'],side,c['coverage'],lateral,r)
        front=c['depth']/max(c['area'],1e-8);front=max(.142,min(.146,front))
        thickness=r.uniform(*CFG['core_thickness_m']);back=front-thickness
        top=inset(p,r.uniform(.00025,.0007));mid=inset(p,-r.uniform(.0001,.0004));bottom=inset(p,.00035)
        # Recover the original atlas cell as an affine map from its largest face.
        samples=c['face'][:3]
        matrix=np.array([[a[0][0],a[0][2],1] for a in samples])
        values=np.array([a[1] for a in samples])
        coefficients=np.linalg.solve(matrix,values)
        uv=lambda x,z:tuple(np.array([x,z,1])@coefficients)
        planar=lambda x,z:(x/CFG['core_texture_size_m'],z/CFG['core_texture_size_m'])
        b=builders[sid];glaze=max(c['slot_area'],key=c['slot_area'].get)
        ft=lambda x,z:front
        lip=lambda x,z:front-CFG['glaze_lip_m']
        half=lambda x,z:front-thickness*.48
        bk=lambda x,z:back
        b.cap(top,ft,glaze,uv)
        b.sides(top,p,ft,lip,glaze,uv)
        b.sides(p,mid,lip,half,core_id)
        b.sides(mid,bottom,half,bk,core_id)
        b.cap(bottom,bk,core_id,planar,back=True)
        adhesive_top=inset(bottom,.00045);adhesive_base=inset(bottom,-.0004)
        glue_top=lambda x,z:back+.00015
        phase=span[3]*.43+sid*.61
        glue_bottom=lambda x,z:bed_height(x,z,phase)-.004
        mortar_uv=lambda x,z:(x/(BEDCFG['tile_size_cm']/100),z/(BEDCFG['tile_size_cm']/100))
        b.cap(adhesive_top,glue_top,finish_id,mortar_uv)
        b.sides(adhesive_top,adhesive_base,glue_top,glue_bottom,finish_id,mortar_uv)
        b.cap(adhesive_base,glue_bottom,finish_id,mortar_uv,back=True)
        kept+=1;records.append(dict(cell=list(ck),old_coverage=c['coverage'],action='bonded_remnant',attached_side=side,
                                    core_thickness_m=thickness,outline_vertices=len(p)))
    bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(mesh);bm.free()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    for i,b in enumerate(builders):
        if not b.f:continue
        data=bpy.data.meshes.new(key+'_Fracture_'+str(i));data.from_pydata(b.v,[],b.f);data.update()
        for mat in mesh.materials:data.materials.append(mat)
        layer=data.uv_layers.new(name='UVMap')
        for poly,mi,uvs in zip(data.polygons,b.mi,b.uv):
            poly.material_index=mi;poly.use_smooth=False
            for li,co in zip(poly.loop_indices,uvs):layer.data[li].uv=co
        new=bpy.data.objects.new(key+'_BondedCeramic',data);bpy.context.scene.collection.objects.link(new);new.select_set(True)
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
    mod=obj.modifiers.new('Export ceramic triangulation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.name='SM_TileFracture_'+key
    file=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
                            bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    materials={clean(s['name']):s['material'] for s in entry['slots']}
    manifest['objects'].append(dict(name=obj.name,actor=entry['label'],previous_mesh=entry['mesh'],fbx=str(file),materials=materials,
                                    partial_cells=len(partial),bonded_remnants=kept,isolated_cells_removed=isolated,changes=records))
    print('AUTHORED_CERAMIC',key,'partial',len(partial),'bonded',kept,'isolated_removed',isolated,flush=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonTileFracture_Source.blend'))
(OUT/'geometry-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
