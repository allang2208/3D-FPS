"""Rebuild only the three native slide seats, retaining each optical body and UV0."""
import bpy,bmesh,json,ast,math,re
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

O=Path(__file__).parent;S=O.parent;C=S/'PitViper2011Integration20261002'
E=O/'Exports';E.mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
records={}
old_job=S/'PitViper2011Attachments20261002'
helpers={'select','source_bvh','metal','physical_uv','new_mesh','join','add_socket','export','load_source','remove_adapter'}
tree=ast.parse((old_job/'author_parts.py').read_text(encoding='utf8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in helpers],type_ignores=[]),'<existing export helpers>','exec'))
auth=json.loads((C/'Single/authoring.json').read_text());alignment=Matrix(auth['alignment'])
raw=json.loads((C/'canonical_parts.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(C/'Single/PitViper2011_single_Editable.blend'))
rig=bpy.data.objects['SK_PitViper2011_Manny'];root=rig.data.bones['WPN_root'].matrix_local.copy();rinv=root.inverted()
rear=rinv@rig.data.bones['WPN_RearSight'].head_local
forward=rinv@rig.data.bones['WPN_FrontSight'].head_local-rear
forward.z=0;forward.normalize();up=Vector((0,0,1));lateral=up.cross(forward).normalized()
origin=rear+forward*.016+up*.0045
slide=source_bvh([p for p in raw if p['identity']=='2011pv slide_1' and p['material']=='h-190'])

def roof(x,y):
    hit=slide.ray_cast(origin+forward*x+lateral*y+up*.10,-up)[0]
    if hit is None:raise RuntimeError('Missing native slide plate contact '+str((x,y)))
    return hit.z-origin.z-.00018

def shell(name,nx,ny,lower,upper):
    verts=[];faces=[]
    for fn in (lower,upper):verts.extend(fn(i/nx,j/ny) for i in range(nx+1) for j in range(ny+1))
    count=(nx+1)*(ny+1);index=lambda i,j:i*(ny+1)+j
    for i in range(nx):
        for j in range(ny):
            quad=(index(i,j),index(i+1,j),index(i+1,j+1),index(i,j+1))
            faces.extend([quad[::-1],tuple(v+count for v in quad)])
    edge=[index(i,0) for i in range(nx)]+[index(nx,j) for j in range(ny)]+[index(i,ny) for i in range(nx,0,-1)]+[index(0,j) for j in range(ny,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]):faces.append((a,b,b+count,a+count))
    return new_mesh(name,verts,faces,metal())

profiles={
 'holographic':(-.009,.025,.0107,.0145),
 'panoramic_red_dot':(-.009,.020,.0102,.0163),
 'eoth_holographic':(-.009,.043,.0107,.0145)}

for key,(xmin,xmax,half,upper_half) in profiles.items():
    source=old_job/f'Exports/SM_PitViper2011_{key}_Editable.blend'
    ob=load_source(source);remove_adapter(ob)
    optical=[p for p in ob.data.polygons if 'reticle' in ob.data.materials[p.material_index].name.lower()]
    reticle_ids={i for p in optical for i in p.vertices}
    if not reticle_ids:raise RuntimeError('Missing physical reticle '+key)
    rp=[ob.data.vertices[i].co.copy() for i in reticle_ids]
    aim=Vector(((min(v.x for v in rp)+max(v.x for v in rp))*.5,(min(v.y for v in rp)+max(v.y for v in rp))*.5,(min(v.z for v in rp)+max(v.z for v in rp))*.5))
    body_faces=[list(p.vertices) for p in ob.data.polygons
        if not any(s in ob.data.materials[p.material_index].name.lower() for s in ('glass','reticle'))]
    body_bvh=BVHTree.FromPolygons([v.co.copy() for v in ob.data.vertices],body_faces)
    body_min=min(ob.data.vertices[i].co.z for p in body_faces for i in p)
    nx,ny=64,32
    pts={}
    for i in range(nx+1):
        for j in range(ny+1):
            x=xmin+(xmax-xmin)*i/nx;y=upper_half*(j/ny*2-1)
            hit,normal,_,_=body_bvh.ray_cast(Vector((x,y,-.10)),up)
            if hit is not None and normal.z<-.15 and hit.z<=body_min+.0045:pts[(i,j)]=hit
    quads=[]
    for i in range(nx):
        for j in range(ny):
            q=((i,j),(i+1,j),(i+1,j+1),(i,j+1))
            if all(v in pts for v in q):quads.append(q)
    used={v for q in quads for v in q}
    if not used:raise RuntimeError('No load-bearing optic footprint '+key)
    roof_values=[roof(xmin+(xmax-xmin)*i/24,half*(j/16*2-1)) for i in range(25) for j in range(17)]
    plate_top=max(roof_values)+.00108  # 0.9 mm above the highest real roof.
    dz=plate_top+.00085-min(pts[v].z for v in used)
    ob.data.transform(Matrix.Translation((0,0,dz)))
    for child in ob.children:
        if child.type=='EMPTY':child.location.z+=dz
    aim.z+=dz
    def low(u,v):
        x=xmin+(xmax-xmin)*u;y=half*(v*2-1);return (x,y,roof(x,y))
    def high(u,v):return (xmin+(xmax-xmin)*u,half*(v*2-1),plate_top)
    plate=shell('PitViper_ContouredSlidePlate',36,20,low,high)
    select(plate)
    bevel=plate.modifiers.new('Machined edge radius','BEVEL');bevel.width=.00020;bevel.segments=2
    bevel.limit_method='ANGLE';bevel.angle_limit=.45
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    keys=sorted(used);ids={v:i for i,v in enumerate(keys)};verts=[]
    for v in keys:
        p=pts[v];verts.append((p.x,p.y*min(1.,(half-.0003)/upper_half),plate_top-.00012))
    for v in keys:
        p=pts[v];verts.append((p.x,p.y,p.z+dz+.00018))
    count=len(keys);faces=[];edges={}
    for q in quads:
        f=tuple(ids[v] for v in q);faces.extend([f[::-1],tuple(i+count for i in f)])
        for a,b in zip(f,f[1:]+f[:1]):
            edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
    for (a,b),n in edges.items():
        if n==1:faces.append((a,b,b+count,a+count))
    contact=new_mesh('PitViper_FittedOpticFoot',verts,faces,metal())
    parts=[plate,contact]
    for x in (xmin+.003,xmax-.003):
        for side in (-1,1):
            bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.00075,depth=.00032,
                location=(x,side*(half-.001),plate_top-.00007))
            screw=bpy.context.object;screw.name='PitViper_CountersunkFastener';screw.data.materials.append(metal());parts.append(screw)
    join(ob,parts)
    add_socket(ob,'AimCenter',aim);add_socket(ob,'SightRear',aim)
    add_socket(ob,'SightFront',aim+Vector((.03,0,0)));add_socket(ob,'SightUp',aim+Vector((0,0,.03)))
    export(ob,key,dict(source=str(source),repair_source=str(O/'author_optics.py'),
        frame='+X forward, +Z up; unchanged native slide mount',mount_origin_root_m=list(origin),
        adapter='contoured full rear slide plate, tapered contact patches sampled from actual downward-facing optic foot, embedded fasteners',
        base_plate_extent_mm=[(xmax-xmin)*1000,half*2000],contact_patches=len(quads),
        body_vertical_adjustment_mm=dz*1000,slide_embed_mm=.18,body_embed_mm=.18,
        optical_body_uv0_preserved=True,aim_source='physical retained reticle plane center'))

original=json.loads((old_job/'authoring.json').read_text());original.update(records)
(old_job/'authoring.json').write_text(json.dumps(original,indent=2))
print('PIT_VIPER_OPTIC_SEATS_AUTHORED',len(records),flush=True)
