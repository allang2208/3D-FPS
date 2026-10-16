"""Tailored cover-mounted bookmarks, outside the complete page-turn sweep."""
from pathlib import Path
import bpy,bmesh,json,math
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'AlchemyManualFinePress20261016/AlchemyManualFinePress.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
body=bpy.data.objects['SM_AlchemyManualOpen']
cover=BVHTree.FromPolygons([body.matrix_world@v.co for v in body.data.vertices],
    [list(f.vertices) for f in body.data.polygons if body.data.materials[f.material_index].name=='M_BookCover'])
old=bpy.data.objects.get('SM_AlchemyManualBookmarks')
if old:bpy.data.objects.remove(old,do_unlink=True)
cloth=bpy.data.materials.new('ManualRibbonV6');metal=bpy.data.materials.new('ManualClaspV6')
half=.92;ya=11.70;yb=14.05;thickness=.042;centers=(-13.2,13.2)
verts=[];faces=[];values=[];smooth=[];anchors=[]
nx,ny=24,24
for side,cx in enumerate(centers):
    hit=cover.ray_cast((cx,11.78,10),(0,0,-1))[0]
    if hit is None:raise RuntimeError('Missing actual cover contact')
    anchor=hit.z;anchors.append(anchor)
    base=len(verts);layer=(nx+1)*(ny+1)
    for bottom in (False,True):
        for i in range(nx+1):
            u=i/nx;x=cx+(2*u-1)*half
            r=.14;corner=max(0,abs(x-cx)-(half-r));inset=r-math.sqrt(max(0,r*r-corner*corner))
            for j in range(ny+1):
                t=j/ny;y=ya+inset+(yb-ya-2*inset)*t
                # Root lies on the cover; modest longitudinal bow and a soft tip.
                z=anchor+thickness/2+.008+.035*math.sin(math.pi*t)-.10*t**3
                z+=.009*math.sin(u*2*math.pi)*math.sin(t*math.pi)
                z+=(-thickness/2 if bottom else thickness/2)
                verts.append((x,y,z))
    def face(ids,soft=True):
        faces.append(ids);smooth.append(soft)
        values.append([((side+(verts[k][0]-cx+half)/(2*half))/2,(verts[k][1]-ya)/(yb-ya)) for k in ids])
    for bottom in (False,True):
        for i in range(nx):
            for j in range(ny):
                a=base+int(bottom)*layer+i*(ny+1)+j;ids=(a,a+ny+1,a+ny+2,a+1)
                face(tuple(reversed(ids)) if bottom else ids)
    rim=[i*(ny+1) for i in range(nx+1)]+[nx*(ny+1)+j for j in range(1,ny+1)]+[i*(ny+1)+ny for i in range(nx-1,-1,-1)]+[j for j in range(ny-1,0,-1)]
    for a,b in zip(rim,rim[1:]+rim[:1]):face((base+a,base+a+layer,base+b+layer,base+b),False)
mesh=bpy.data.meshes.new('Tailored cover tabs');mesh.from_pydata(verts,[],faces);mesh.materials.append(cloth);mesh.update()
uv=mesh.uv_layers.new(name='UVMap').data
for face,coords,soft in zip(mesh.polygons,values,smooth):
    face.use_smooth=soft
    for li,coord in zip(face.loop_indices,coords):uv[li].uv=coord
tabs=bpy.data.objects.new('SM_AlchemyManualBookmarks',mesh);bpy.context.scene.collection.objects.link(tabs)

def clasp(name,location,size,radius):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location);obj=bpy.context.object;obj.name=name;obj.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(metal)
    mod=obj.modifiers.new('Polished rounded edges','BEVEL');mod.width=radius;mod.segments=5
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj

clips=[]
for cx,z in zip(centers,anchors):
    # A bridge just above the cloth, with feet landing outside its two selvages.
    clips.append(clasp('Rounded binding clasp',(cx,11.79,z+.079),(2.02,.23,.042),.018))
    for dx in (-.975,.975):
        clips.append(clasp('Clasp foot',(cx+dx,11.79,z+.029),(.07,.23,.058),.014))
    # Tiny flush rivet heads in the side feet, never a bar over the label.
    for dx in (-.975,.975):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=1,location=(cx+dx,11.79,z+.101))
        obj=bpy.context.object;obj.name='Flush rivet';obj.scale=(.032,.032,.009)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);obj.data.materials.append(metal)
        for f in obj.data.polygons:f.use_smooth=True
        clips.append(obj)
bpy.ops.object.select_all(action='DESELECT')
for obj in [tabs]+clips:obj.select_set(True)
bpy.context.view_layer.objects.active=tabs;bpy.ops.object.join()
bm=bmesh.new();bm.from_mesh(tabs.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(tabs.data);bm.free()
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/SM_AlchemyManualBookmarks.fbx'),use_selection=True,
    object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',
    mesh_smooth_type='FACE',use_tspace=False,bake_anim=False,path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'AlchemyManualReadingFit.blend'))
tabs.data.calc_loop_triangles()
spec=dict(source=str(SOURCE),parts=[dict(name=tabs.name,materials=[m.name for m in tabs.data.materials],triangles=len(tabs.data.loop_triangles))],
    cover_contact_z_cm=anchors,bookmark_centers_cm=centers,bookmark_half_width_cm=half,bookmark_y_cm=[ya,yb],
    page_y_max_cm=11.47300434,page_sweep_separation_cm=ya-11.47300434,cloth_thickness_cm=thickness,rendered=False)
(ROOT/'model.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
header='#pragma once\n// Cover-mounted bookmarks; Blender Y converted to UE Y.\nnamespace AlchemyManualGeometry {\n'
header+='constexpr float LeafHeight=3.05000324f,Width=15.51884842f,Height=24.18600941f;\n'
header+=f'constexpr float BookmarkCenter=13.2f,BookmarkHalfWidth={half}f,BookmarkFrontY={-yb}f,BookmarkBackY={-ya}f,BookmarkPlaneZ={sum(anchors)/len(anchors)+.025:.8f}f;\n}}\n'
(ROOT/'AlchemyManualGeometry.h').write_text(header,encoding='utf-8')
print('BOOKMARKS_EXPORTED '+json.dumps(spec))
