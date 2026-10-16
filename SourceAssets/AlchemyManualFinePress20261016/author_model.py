"""Fine folio geometry from the preserved V3 source; no preview render."""
from pathlib import Path
import bpy,bmesh,json,math
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'Export'
SOURCE=PROJECT/'SourceAssets/PotionWorkbenchDesign20261015/ManualV3/AlchemyManual.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
WIDTH=15.51884842;HEIGHT=24.18600941;LIFT=3.05000324
body=bpy.data.objects['SM_AlchemyManualOpen'];old_leaf=bpy.data.objects['SM_AlchemyManualLeaf'];closed=bpy.data.objects['SM_AlchemyManualClosed']
left=bpy.data.materials['RecipeLeft'];right=bpy.data.materials['RecipeRight'];edge=bpy.data.materials['M_BookPages']
brass=bpy.data.materials.new('ManualAntiqueBrass');ribbon=bpy.data.materials.new('ManualBookmarks')
trim=bpy.data.materials.new('ManualLeatherBinding')

# Remove only the two old printable leaf islands, retaining the exterior and stack.
bm=bmesh.new();bm.from_mesh(body.data)
seeds={v for f in bm.faces if body.data.materials[f.material_index].name in ('RecipeLeft','RecipeRight') for v in f.verts}
removed=set(seeds);todo=list(seeds)
while todo:
    v=todo.pop()
    for e in v.link_edges:
        other=e.other_vert(v)
        if other not in removed:removed.add(other);todo.append(other)
bmesh.ops.delete(bm,geom=list(removed),context='VERTS');bm.to_mesh(body.data);bm.free()

def paper(name,side=1,turning=False):
    nx,ny=48,24;x0,x1=.32,WIDTH-.60;y0,y1=-HEIGHT/2+.62,HEIGHT/2-.62
    verts=[];faces=[];slots=[];uvs=[]
    for bottom in (False,True):
        for i in range(nx+1):
            t=i/nx
            for j in range(ny+1):
                y=y0+(y1-y0)*j/ny;r=.28;corner=max(0,abs(y)-(y1-r))
                inset=r-math.sqrt(max(0,r*r-corner*corner))
                x=x0+inset+(x1-x0-2*inset)*t
                x+=.009*math.sin(y*3.7)*t**8
                z=.22*math.sin(math.pi*x/WIDTH)-.045*math.exp(-x/.7)+.014*math.cos(y*.7)*t*t
                z+=(-.016 if bottom else .016)+(0 if turning else LIFT)
                verts.append((side*x,y,z))
    layer=(nx+1)*(ny+1)
    def add(ids,material,back=False):
        faces.append(ids);slots.append(material);uv=[]
        for k in ids:
            x,y,z=verts[k];u=abs(x)/WIDTH
            if (not turning and side<0) or (turning and back):u=1-u
            uv.append((u,y/HEIGHT+.5))
        uvs.append(uv)
    for bottom in (False,True):
        for i in range(nx):
            for j in range(ny):
                a=int(bottom)*layer+i*(ny+1)+j;ids=(a,a+ny+1,a+ny+2,a+1)
                if bottom!=(side<0):ids=tuple(reversed(ids))
                add(ids,0 if bottom and not turning else (1 if bottom or side<0 else 2),bottom)
    rim=[i*(ny+1) for i in range(nx+1)]+[nx*(ny+1)+j for j in range(1,ny+1)]+[i*(ny+1)+ny for i in range(nx-1,-1,-1)]+[j for j in range(ny-1,0,-1)]
    for a,b in zip(rim,rim[1:]+rim[:1]):
        ids=(a,a+layer,b+layer,b)
        if side<0:ids=tuple(reversed(ids))
        add(ids,0)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    for mat in (edge,left,right):mesh.materials.append(mat)
    uv=mesh.uv_layers.new(name='UVMap').data
    for f,slot,values in zip(mesh.polygons,slots,uvs):
        f.material_index=slot;f.use_smooth=slot!=0
        for li,value in zip(f.loop_indices,values):uv[li].uv=value
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);return obj

pages=[paper('FinePaperLeft',-1),paper('FinePaperRight',1)]
bpy.data.objects.remove(old_leaf,do_unlink=True)
leaf=paper('SM_AlchemyManualLeaf',1,True)

def bevel_box(name,location,size,mat,bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location);obj=bpy.context.object;obj.name=name;obj.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(mat);mod=obj.modifiers.new('Edge softening','BEVEL');mod.width=bevel;mod.segments=3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for f in obj.data.polygons:f.use_smooth=False
    return obj

# Discreet corner guards placed on the actual cover edge, never on page tops.
cover_ids={i for f in body.data.polygons if body.data.materials[f.material_index].name=='M_BookCover' for i in f.vertices}
cover=[body.data.vertices[i].co.copy() for i in cover_ids]
xmin,xmax=min(v.x for v in cover),max(v.x for v in cover);ymin,ymax=min(v.y for v in cover),max(v.y for v in cover)
details=[]
for sx in (-1,1):
    for sy in (-1,1):
        x=(xmax-.16 if sx>0 else xmin+.16);y=(ymax-.16 if sy>0 else ymin+.16)
        near=sorted(cover,key=lambda v:(v.x-x)**2+(v.y-y)**2)[:12]
        z=max(v.z for v in near)+.035
        details.append(bevel_box('Cover corner gold',(x-sx*.65,y,z),(1.42,.12,.065),brass,.025))
        details.append(bevel_box('Cover corner gold',(x,y-sy*.65,z),(.12,1.42,.065),brass,.025))

# A compressed leather gutter sits below the two thin leaves.
details.append(bevel_box('Spine lining',(0,0,LIFT-.14),(.51,HEIGHT-1.2,.15),trim,.065))

# Each ribbon is a closed, densely segmented cloth strip with a gently folded tip.
verts=[];faces=[];values=[];cx_values=(-13.2,13.2);half=1.18;ya,yb=9.7,14.15
nx,ny=8,32
for side,cx in enumerate(cx_values):
    base=len(verts);layer=(nx+1)*(ny+1)
    for back in (False,True):
        for i in range(nx+1):
            u=i/nx
            for j in range(ny+1):
                t=j/ny;x=cx+(u-.5)*half*2
                notch=.30*(1-abs(u-.5)*2)*t**24
                y=ya+(yb-ya)*t-notch
                z=LIFT+.09+.16*math.sin(math.pi*t)-.23*t**4+.028*math.sin(u*3*math.pi)*math.sin(t*math.pi)
                z+=-.027 if back else .027
                verts.append((x,y,z))
    def face(ids):
        faces.append(ids);values.append([((side+(verts[k][0]-cx+half)/(2*half))/2,(verts[k][1]-ya)/(yb-ya)) for k in ids])
    for back in (False,True):
        for i in range(nx):
            for j in range(ny):
                a=base+int(back)*layer+i*(ny+1)+j;ids=(a,a+ny+1,a+ny+2,a+1)
                face(tuple(reversed(ids)) if back else ids)
    rim=[i*(ny+1) for i in range(nx+1)]+[nx*(ny+1)+j for j in range(1,ny+1)]+[i*(ny+1)+ny for i in range(nx-1,-1,-1)]+[j for j in range(ny-1,0,-1)]
    for a,b in zip(rim,rim[1:]+rim[:1]):face((base+a,base+a+layer,base+b+layer,base+b))
mesh=bpy.data.meshes.new('Woven bookmarks');mesh.from_pydata(verts,[],faces);mesh.materials.append(ribbon);mesh.update()
uv=mesh.uv_layers.new(name='UVMap').data
for f,coords in zip(mesh.polygons,values):
    f.use_smooth=True
    for li,value in zip(f.loop_indices,coords):uv[li].uv=value
tabs=bpy.data.objects.new('SM_AlchemyManualBookmarks',mesh);bpy.context.scene.collection.objects.link(tabs)
clips=[]
for cx in cx_values:
    z=LIFT+.23
    clips.append(bevel_box('Bookmark clasp',(cx,10.15,z),(2.48,.36,.12),brass,.05))
    for dx in (-.94,.94):clips.append(bevel_box('Clasp end',(cx+dx,10.15,z+.04),(.10,.36,.045),brass,.02))

def join(active,others):
    bpy.ops.object.select_all(action='DESELECT')
    for o in [active]+others:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=active;bpy.ops.object.join()
join(body,pages+details);join(tabs,clips)
records=[]
for obj in (body,leaf,closed,tabs):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',mesh_smooth_type='FACE',use_tspace=False,bake_anim=False,path_mode='STRIP')
    obj.data.calc_loop_triangles();records.append(dict(name=obj.name,materials=[m.name for m in obj.data.materials],triangles=len(obj.data.loop_triangles)))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'AlchemyManualFinePress.blend'))
spec=dict(source=str(SOURCE),parts=records,spine_origin_cm=LIFT,bookmark_centers_cm=cx_values,bookmark_half_width_cm=half,bookmark_y_cm=[ya,yb],rendered=False)
(ROOT/'model.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
header='#pragma once\n// Fine-press authoring geometry, centimetres, UE Y conversion included.\nnamespace AlchemyManualGeometry {\n'
header+=f'constexpr float LeafHeight={LIFT:.8f}f,Width={WIDTH:.8f}f,Height={HEIGHT:.8f}f;\n'
header+=f'constexpr float BookmarkCenter=13.2f,BookmarkHalfWidth={half}f,BookmarkFrontY={-yb}f,BookmarkBackY={-ya}f,BookmarkPlaneZ={LIFT+.13:.8f}f;\n}}\n'
(ROOT/'AlchemyManualGeometry.h').write_text(header,encoding='utf-8')
print('Fine folio exported:',json.dumps(records))
