"""Map original rune artworks onto the existing bark surface. No rendering."""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Export';OUT.mkdir(exist_ok=True)
KEYS=['eagle_eye_rune','crit_rune','storm_rune']
PALETTE=json.loads((ROOT/'palette.json').read_text(encoding='utf-8'))
SOURCE=ROOT.parent/'BarkRebuildV21/Staff_NaturalBark_V21.blend'
ZMIN,ZMAX=43.20,56.80
HALF_ANGLE=.44
OFFSET_CM=.014
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
with bpy.data.libraries.load(str(SOURCE),link=False) as (src,dst):dst.objects=['SM_Staff_Body']
body=dst.objects[0];bpy.context.scene.collection.objects.link(body);body.name='OriginalBarkReference'
body.hide_render=True;body.hide_set(True)

# Copy and clip the actual authored bark triangles; no nominal cylinder or
# flat tangent quads. Open edges are intentional for a depth-tested mask surface.
patches=[]
for face in range(4):
    angle=face*math.tau/4
    bm=bmesh.new();bm.from_mesh(body.data)
    for co,no in [((0,0,ZMIN),(0,0,1)),((0,0,ZMAX),(0,0,-1)),
                  ((0,0,0),(-math.sin(angle-HALF_ANGLE),math.cos(angle-HALF_ANGLE),0)),
                  ((0,0,0),(math.sin(angle+HALF_ANGLE),-math.cos(angle+HALF_ANGLE),0))]:
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
            dist=.000001,plane_co=co,plane_no=no,clear_inner=True,clear_outer=False)
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for v in bm.verts:
        direction=Vector((v.co.x,v.co.y,0)).normalized();v.co+=direction*OFFSET_CM
    me=bpy.data.meshes.new('BarkLane_'+str(face));bm.to_mesh(me);bm.free();me.update()
    uv=me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        p.use_smooth=True;p.material_index=0
        for li in p.loop_indices:
            v=me.vertices[me.loops[li].vertex_index].co
            a=(math.atan2(v.y,v.x)-angle+math.pi)%math.tau-math.pi
            uv.data[li].uv=((a+HALF_ANGLE)/(2*HALF_ANGLE),(v.z-ZMIN)/(ZMAX-ZMIN))
    # Only this authored channel is exported; the historical bark UV is unrelated.
    for layer in list(me.uv_layers):
        if layer!=uv:me.uv_layers.remove(layer)
    uv.name='UVMap';me.uv_layers.active_index=0;uv.active_render=True
    patches.append(me)

def select(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
manifest=[];art={}
for key in KEYS:
    path=ROOT/'Art'/('T_StaffRune_'+key+'.png')
    image=bpy.data.images.load(str(path),check_existing=True);image.colorspace_settings.name='Non-Color'
    w,h=image.size;pixels=np.empty(w*h*4,np.float32);image.pixels.foreach_get(pixels)
    mask=pixels.reshape((h,w,4))[:,:,:3].max(axis=2)
    yy,xx=np.where(mask>.16)
    x0=max(0,int(xx.min())-8);x1=min(w-1,int(xx.max())+8)
    y0=max(0,int(yy.min())-8);y1=min(h-1,int(yy.max())+8)
    rect_bl=[x0/w,y0/h,(x1-x0)/w,(y1-y0)/h]
    rect_ue=[x0/w,1-y1/h,(x1-x0)/w,(y1-y0)/h]
    art[key]=dict(texture=path.stem,source=str(path),size=[w,h],uv_rect=rect_ue,
                  original_pixels_unchanged=True,design={'eagle_eye_rune':'eye seal with tapered feathers',
                  'crit_rune':'fractured impact seal and cutting strokes','storm_rune':'vortex seal and flowing lightning'}[key])
    image.pack()
    mat=bpy.data.materials.new('M_StaffRuneCraft_'+key);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');ns=mat.node_tree.nodes;links=mat.node_tree.links
    bs.inputs['Base Color'].default_value=(*PALETTE[key]['metal'],1)
    bs.inputs['Metallic'].default_value=.72;bs.inputs['Roughness'].default_value=.31
    bs.inputs['Emission Color'].default_value=(*PALETTE[key]['glow'],1);bs.inputs['Emission Strength'].default_value=.22
    tc=ns.new('ShaderNodeTexCoord');scale=ns.new('ShaderNodeVectorMath');scale.operation='MULTIPLY'
    scale.inputs[1].default_value=(rect_bl[2],rect_bl[3],1);links.new(tc.outputs['UV'],scale.inputs[0])
    add=ns.new('ShaderNodeVectorMath');add.operation='ADD';add.inputs[1].default_value=(rect_bl[0],rect_bl[1],0)
    links.new(scale.outputs[0],add.inputs[0]);tex=ns.new('ShaderNodeTexImage');tex.image=image;tex.extension='CLIP'
    links.new(add.outputs[0],tex.inputs['Vector'])
    cut=ns.new('ShaderNodeMath');cut.operation='GREATER_THAN';cut.inputs[1].default_value=.18
    links.new(tex.outputs['Color'],cut.inputs[0]);links.new(cut.outputs[0],bs.inputs['Alpha'])
    bump=ns.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.3;bump.inputs['Distance'].default_value=.008
    links.new(tex.outputs['Color'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    mat.surface_render_method='DITHERED';mat.diffuse_color=(*PALETTE[key]['metal'],1)
    coll=bpy.data.collections.new(key+'_Editable');bpy.context.scene.collection.children.link(coll)
    objects=[]
    for i,patch in enumerate(patches):
        me=patch.copy();me.materials.clear();me.materials.append(mat)
        o=bpy.data.objects.new(key+'_BarkFace_'+str(i),me);coll.objects.link(o);objects.append(o)
    copies=[]
    for o in objects:
        c=o.copy();c.data=o.data.copy();bpy.context.scene.collection.objects.link(c);copies.append(c)
    select(copies[0])
    for o in copies:o.select_set(True)
    bpy.ops.object.join();joined=bpy.context.object;joined.name='SM_Staff_shaft_rune_'+key
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    file=OUT/(joined.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,apply_scale_options='FBX_SCALE_ALL',path_mode='AUTO',embed_textures=False)
    manifest.append(dict(id=key,name=joined.name,fbx=str(file),materials=[mat.name],
                         triangles=sum(len(p.vertices)-2 for p in joined.data.polygons)))
    joined.hide_set(True);joined.hide_render=True
    for o in objects:o.hide_set(key!='eagle_eye_rune');o.hide_render=key!='eagle_eye_rune'
    print('STAFF_RUNE_AUTHORED '+key,flush=True)

scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['source']='V21 actual bark triangles; four cropped surface lanes; original artwork unmodified'
scene['rune_z_cm']=[ZMIN,ZMAX];scene['offset_cm']=OFFSET_CM
for area in (bpy.context.screen.areas if bpy.context.screen else []):
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_location=Vector((0,0,50));area.spaces.active.region_3d.view_distance=24
(OUT/'meshes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(OUT/'artwork.json').write_text(json.dumps(art,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Staff_EngravedRunes.blend'))
(ROOT/'author-receipt.json').write_text(json.dumps(dict(complete=True,meshes=manifest,artwork=art,
    source=str(SOURCE),range_z_cm=[ZMIN,ZMAX],offset_cm=OFFSET_CM,
    lane_half_angle=HALF_ANGLE,rendered=False,tested=False),indent=2),encoding='utf-8')
print('STAFF_RUNE_ART_AND_GEOMETRY_SAVED',flush=True)
