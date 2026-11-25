"""Import the fitted Meshy atlases, build the stable joinery and cook its simple collision."""
import json
import hashlib
import math
import os
import sys
from pathlib import Path
import unreal as ue

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
RUN=Path(os.environ['STABLE_RUN'])
SOURCE=PROJECT/'SourceAssets/HillsVillageStable'
ROOT='/Game/WorldGeneration/TemperateHills/VillageStable'
sys.path.insert(0,str(HERE))
from stable_profile import roof_top
sys.path.insert(0,str(HERE.parent/'VillageWindmill'))
os.environ.update(WINDMILL_PROJECT=str(PROJECT),WINDMILL_ART=str(RUN))
from import_windmill_assets import import_fbx, load, save, ASSETS, TOOLS, MAT, SURFACES
from import_work_details import sample,finish


def texture(source,name,mode):
    folder=ROOT+'/Textures'
    address=folder+'/'+name
    if ASSETS.does_asset_exist(address):
        return load(address)
    task=ue.AssetImportTask()
    task.filename=str(source)
    task.destination_path=folder
    task.destination_name=name
    task.automated=True
    TOOLS.import_asset_tasks([task])
    tex=load(address)
    tex.srgb=mode=='base_color'
    if mode=='normal':
        tex.compression_settings=ue.TextureCompressionSettings.TC_NORMALMAP
        tex.flip_green_channel=True
    elif mode!='base_color':
        tex.compression_settings=ue.TextureCompressionSettings.TC_MASKS
    save(tex)
    return tex


def atlas(part):
    folder=ROOT+'/Materials'
    name='MI_Stable_'+part
    if ASSETS.does_asset_exist(folder+'/'+name):
        return load(folder+'/'+name)
    mat=TOOLS.create_asset(name,folder,ue.MaterialInstanceConstant,ue.MaterialInstanceConstantFactoryNew())
    MAT.set_material_instance_parent(mat,load('/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelArtifact'))
    for channel in ('base_color','normal','roughness','metallic'):
        src=SOURCE/'MeshyR1'/part/'downloads'/('texture_urls_0_'+channel+'.png')
        tex=texture(src,'T_Stable_'+part+'_'+channel,channel)
        MAT.set_material_instance_texture_parameter_value(mat,channel,tex)
    MAT.update_material_instance(mat)
    save(mat)
    return mat


def ground():
    folder=ROOT+'/Materials'
    name='M_StableTraffic'
    if ASSETS.does_asset_exist(folder+'/'+name):
        return
    mask=texture(SOURCE/'AssemblyR1/StableTraffic.png','T_StableTraffic','mask')
    mat=TOOLS.create_asset(name,folder,ue.Material,ue.MaterialFactoryNew())
    mat.set_editor_property('material_domain',ue.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property('blend_mode',ue.BlendMode.BLEND_TRANSLUCENT)
    alpha=sample(mat,mask,ue.MaterialSamplerType.SAMPLERTYPE_MASKS)
    MAT.connect_material_property(alpha,'R',ue.MaterialProperty.MP_OPACITY)
    uv=MAT.create_material_expression(mat,ue.MaterialExpressionTextureCoordinate)
    uv.set_editor_property('u_tiling',18)
    uv.set_editor_property('v_tiling',21)
    base='/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_'
    for prop,suffix,kind in ((ue.MaterialProperty.MP_BASE_COLOR,'Albedo',ue.MaterialSamplerType.SAMPLERTYPE_COLOR),
                             (ue.MaterialProperty.MP_NORMAL,'Normal',ue.MaterialSamplerType.SAMPLERTYPE_NORMAL)):
        node=sample(mat,load(base+suffix),kind)
        MAT.connect_material_expressions(uv,'',node,'UVs')
        MAT.connect_material_property(node,'RGB',prop)
    rough=MAT.create_material_expression(mat,ue.MaterialExpressionConstant)
    rough.set_editor_property('r',.89)
    MAT.connect_material_property(rough,'',ue.MaterialProperty.MP_ROUGHNESS)
    finish(mat)


def clay():
    folder=ROOT+'/Materials'
    name='M_StablePackedClay'
    if ASSETS.does_asset_exist(folder+'/'+name):
        return load(folder+'/'+name)
    mat=TOOLS.create_asset(name,folder,ue.Material,ue.MaterialFactoryNew())
    MAT.set_base_material_usage(mat,ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    soil='/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_'
    for suffix,mode,property in [('Albedo',ue.MaterialSamplerType.SAMPLERTYPE_COLOR,ue.MaterialProperty.MP_BASE_COLOR),
                                 ('Normal',ue.MaterialSamplerType.SAMPLERTYPE_NORMAL,ue.MaterialProperty.MP_NORMAL)]:
        node=sample(mat,load(soil+suffix),mode)
        MAT.connect_material_property(node,'RGB',property)
    rough=MAT.create_material_expression(mat,ue.MaterialExpressionConstant)
    rough.set_editor_property('r',.92)
    MAT.connect_material_property(rough,'',ue.MaterialProperty.MP_ROUGHNESS)
    finish(mat)
    return mat


def box(cx,cy,cz,w,d,h,roll=0):
    shape=ue.KBoxElem()
    shape.set_editor_property('center',ue.Vector(cx,cy,cz))
    shape.set_editor_property('rotation',ue.Rotator(roll=roll))
    for prop,val in zip(('x','y','z'),(w,d,h)):
        shape.set_editor_property(prop,val)
    return shape


def collision(key):
    if key=='A01_Roof':
        shapes=[]
        for a,b in zip((-430,-360,-20,20,360),(-360,-20,20,360,430)):
            za,zb=roof_top(a)-8,roof_top(b)-8
            shapes.append(box(0,(a+b)/2,(za+zb)/2,440,math.hypot(b-a,zb-za),13,
                              -math.degrees(math.atan2(zb-za,b-a))))
        return shapes
    if key=='A01_Bent':
        return [box(0,s*382,145,30,30,290) for s in (-1,1)]+[box(0,0,286,29,765,18)]
    if key=='A02':
        shapes=[box(0,0,150,779,19,300)]
        for x in range(-364,365,52):
            h=min(roof_top(-x-26),roof_top(-x+26))-311
            shapes.append(box(x,0,300+h/2,52,18,h))
        return shapes
    if key=='A03':
        return [box(s*139.25,0,150,126.5,22,300) for s in (-1,1)]+[box(0,0,270,152,22,60)]
    if key=='RearHalfDoorSides':
        return [box(s*145.5,0,74,139,13,148) for s in (-1,1)]
    if key=='A08':
        return [box(0,0,101,255,18,20)]+[box(s*115,0,51,19,19,102) for s in (-1,1)]
    if key=='PierShoes':
        return [box(0,s*403,145,34,15,290) for s in (-1,1)]
    if key=='PackedFloor':
        return [box(0,0,-2,2214,792,5)]
    sizes={'A04':(8,146,125),'A05':(495,13,162),'A06':(240,14,132),'A07':(11,225,138),
           'A09':(202,73,63),'RearVentWall':(420,22,283),'GatePier':(20,22,170),
           'FenceRails':(240,7,113),'HayCrib':(123,49,99)}
    if key not in sizes:
        return []
    w,d,h=sizes[key]
    return [box(0,-8 if key=='HayCrib' else 0,h/2,w,d,h)]


def main():
    ground()
    from stable_ground_materials import author
    author()
    sources=sorted((SOURCE/'AssemblyR1/Exchange').glob('SM_Stable_*.fbx'))
    records=[]
    for src in sources:
        key=src.stem.removeprefix('SM_Stable_')
        address=ROOT+'/Meshes/'+src.stem
        stamp='2-'+hashlib.sha256(src.read_bytes()).hexdigest()
        mesh=load(address) if ASSETS.does_asset_exist(address) else None
        if not mesh or ASSETS.get_metadata_tag(mesh,'StableFabrication')!=stamp:
            mesh=import_fbx(src,ROOT+'/Meshes')
            for index,slot in enumerate(mesh.static_materials):
                name=str(slot.get_editor_property('imported_material_slot_name'))
                if name in ('A01','A02','A03','A04','A05','A06','A07','A08','A09'):
                    material=atlas(name)
                elif name=='water':
                    material=load('/Game/WorldGeneration/TemperateHills/VillageCarpenter/InteriorR1/M_CarpenterWashWater')
                elif name=='clay':
                    material=clay()
                else:
                    material=load(SURFACES[name])
                mesh.set_material(index,material)
            shapes=collision(key)
            body=mesh.get_editor_property('body_setup')
            geom=body.get_editor_property('agg_geom')
            geom.set_editor_property('box_elems',shapes)
            body.set_editor_property('agg_geom',geom)
            body.set_editor_property('collision_trace_flag',ue.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
            if shapes:
                cooked=ue.GeometryScript_Collision.get_simple_collision_from_static_mesh(mesh)
                ue.GeometryScript_Collision.set_simple_collision_of_static_mesh(cooked,mesh,ue.GeometryScriptSetSimpleCollisionOptions())
            if key.startswith('A0'):
                ns=mesh.get_editor_property('nanite_settings')
                ns.enabled=True
                ns.explicit_tangents=True
                ns.generate_fallback=ue.NaniteGenerateFallback.ENABLED
                ns.fallback_relative_error=.5
                mesh.set_editor_property('nanite_settings',ns)
            ASSETS.set_metadata_tag(mesh,'StableFabrication',stamp)
            save(mesh)
        bounds=mesh.get_bounding_box()
        records.append(dict(key=key,package=address,min_cm=list(bounds.min.to_tuple()),max_cm=list(bounds.max.to_tuple()),
            collision_boxes=len(mesh.get_editor_property('body_setup').get_editor_property('agg_geom').get_editor_property('box_elems'))))
        ue.log('STABLE_SAVED '+key)
    (RUN/'imported.json').write_text(json.dumps(records,indent=2),encoding='utf-8')


main()
