"""Create only boundary variants and a local service connector. Keep accepted assets intact."""
import bpy, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1
base=PROJECT/'SourceAssets/DungeonAtmosphereV2_20260921/Authored'
tile=PROJECT/'SourceAssets/DungeonTileFracture20260922/Authored'
tile_manifest=json.loads((tile/'geometry-manifest.json').read_text(encoding='utf-8'))
base_manifest=json.loads((base/'structure-manifest.json').read_text(encoding='utf-8'))
records=[]

def load_object(file,name):
    with bpy.data.libraries.load(str(file),link=False) as (source,target):
        if name not in source.objects:raise RuntimeError('Missing authored object '+name)
        target.objects=[name]
    obj=target.objects[0];bpy.context.scene.collection.objects.link(obj)
    return obj

def cut(obj,center,size):
    # The accepted wall meshes contain touching shells and open repair patches.
    # Volume booleans misclassify those surfaces. Clip the existing polygons at
    # the six aperture planes, interpolating their UVs and colors instead.
    data=obj.data;uv_names=[x.name for x in data.uv_layers]
    colors=[(a.name,a.data_type,a.domain) for a in data.color_attributes]
    low=[center[i]-size[i]/2 for i in range(3)];high=[center[i]+size[i]/2 for i in range(3)]
    out=[]
    def split(poly,axis,value,sign):
        inside=[];outside=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da=(a[axis]-value)*sign;db=(b[axis]-value)*sign
            if da>=0:inside.append(a)
            if da<=0:outside.append(a)
            if (da>0 and db<0) or (da<0 and db>0):
                t=da/(da-db);p=tuple(x+(y-x)*t for x,y in zip(a,b))
                inside.append(p);outside.append(p)
        return inside,outside
    for face in data.polygons:
        poly=[]
        for li in face.loop_indices:
            vi=data.loops[li].vertex_index;v=list(data.vertices[vi].co)
            for name in uv_names:v.extend(data.uv_layers[name].data[li].uv)
            for name,kind,domain in colors:v.extend(data.color_attributes[name].data[li if domain=='CORNER' else vi].color)
            poly.append(tuple(v))
        if any(max(v[i] for v in poly)<=low[i] or min(v[i] for v in poly)>=high[i] for i in range(3)):
            out.append((poly,face.material_index,face.use_smooth));continue
        remainder=poly
        for axis,value,sign in [(i,v,s) for i in range(3) for v,s in [(low[i],1),(high[i],-1)]]:
            remainder,exterior=split(remainder,axis,value,sign)
            if len(exterior)>=3:out.append((exterior,face.material_index,face.use_smooth))
            if len(remainder)<3:break
    vertices=[];faces=[]
    for poly,mi,smooth in out:
        start=len(vertices);vertices.extend(v[:3] for v in poly);faces.append(tuple(range(start,len(vertices))))
    mesh=bpy.data.meshes.new(data.name+'_Aperture');mesh.from_pydata(vertices,[],faces);mesh.update()
    for material in data.materials:mesh.materials.append(material)
    for name in uv_names:mesh.uv_layers.new(name=name)
    for name,kind,domain in colors:mesh.color_attributes.new(name=name,type=kind,domain=domain)
    for face,(poly,mi,smooth) in zip(mesh.polygons,out):
        face.material_index=mi;face.use_smooth=smooth
        for li,record in zip(face.loop_indices,poly):
            offset=3
            for name in uv_names:mesh.uv_layers[name].data[li].uv=record[offset:offset+2];offset+=2
            for name,kind,domain in colors:
                index=li if domain=='CORNER' else mesh.loops[li].vertex_index
                mesh.color_attributes[name].data[index].color=record[offset:offset+4];offset+=4
    obj.data=mesh

def export(obj,actor,materials):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    tri=obj.modifiers.new('Export triangles and tangents','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    path=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
                            bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    records.append(dict(name=obj.name,actor=actor,fbx=str(path),materials=materials))

for old,boundary in [('SM_V2_EntryEnd','entry'),('SM_V2_EndLanding','exit'),('SM_V2_ServiceDoor','leaf')]:
    obj=load_object(base/'DungeonAtmosphereV2_Structure.blend',old)
    entry=next(x for x in base_manifest['objects'] if x['name']==old)
    maps={'V2_'+m:'/Game/Dungeons/AtmosphereV2/Materials/M_'+m for m in entry['materials']}
    if boundary=='entry':cut(obj,(0,2,1.19),(1,1.32,2.40))
    elif boundary=='exit':cut(obj,(24,14,2.13),(1.32,1,2.40))
    else:cut(obj,(24,13.86,2.15),(1.322,.13,2.282))
    obj.name=old.replace('SM_V2_','SM_Sample_')+'_Open'
    export(obj,'DGN_AV2_'+old.removeprefix('SM_V2_'),maps)

for old,boundary in [('SM_TileFracture_EntryEnd','entry'),('SM_TileFracture_EndLanding','exit')]:
    obj=load_object(tile/'DungeonTileFracture_Source.blend',old)
    entry=next(x for x in tile_manifest['objects'] if x['name']==old)
    if boundary=='entry':cut(obj,(0,2,1.19),(1,1.32,2.40))
    else:cut(obj,(24,14,2.13),(1.32,1,2.40))
    obj.name=old.replace('SM_TileFracture_','SM_Sample_')+'_Tiles_Open'
    materials=dict(entry['materials'])
    materials['V2_CeramicFractureCore']='/Game/Dungeons/AtmosphereV2/TileFracture/Materials/M_CeramicFractureCore'
    export(obj,entry['actor'],materials)

# Local units in metres; +Y becomes UE -Y, along the original service-door exit.
mats={}
for name in ['Concrete','IvoryTile','PaintedSteel','BareSteel','WarmGlass']:
    m=bpy.data.materials.get('V2_'+name) or bpy.data.materials.new('V2_'+name)
    mats[name]=m
parts=[]
def box(center,size,material,bevel=.006):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center)
    o=bpy.context.object;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mats[material])
    if bevel:
        mod=o.modifiers.new('Manufactured edge','BEVEL');mod.width=bevel;mod.segments=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    parts.append(o)
box((0,2,-.08),(1.62,4,.16),'Concrete')
box((0,2,2.46),(1.62,4,.16),'Concrete')
for x in [-.75,.75]:
    box((x,2,1.19),(.18,4,2.38),'Concrete')
    for y in [i*.4+.2 for i in range(10)]:
        for z in [i*.2+.1 for i in range(9)]:box((x*.874,y,z),(.012,.393,.193),'IvoryTile',.001)
    box((x*.85,2,.07),(.018,4,.14),'PaintedSteel',.002)
    for y in [0.10,3.90]:box((x*.84,y,1.19),(.055,.07,2.38),'BareSteel',.003)
box((0,2,2.25),(.55,.18,.07),'BareSteel')
box((0,2,2.205),(.46,.12,.02),'WarmGlass',.002)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
obj=bpy.context.object;obj.name='SM_Sample_ServiceLink'
bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
uv=obj.data.uv_layers.new(name='UVMap')
for face in obj.data.polygons:
    axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
    for li in face.loop_indices:
        co=obj.data.vertices[obj.data.loops[li].vertex_index].co
        uv.data[li].uv=(co[dims[0]]/2,co[dims[1]]/2)
export(obj,'DGN_Link_A_B',{'V2_'+n:'/Game/Dungeons/AtmosphereV2/Materials/M_'+n for n in mats})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'AuthoredSpace_Connections.blend'))
(OUT/'connections.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('AUTHORED_BOUNDARIES_AND_LINK',len(records))
