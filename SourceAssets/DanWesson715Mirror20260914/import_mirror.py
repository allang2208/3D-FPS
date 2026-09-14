"""Install mirror gun/attachment variants, retaining geometry and wet bindings."""
from pathlib import Path
O=Path(__file__).parent
source=(O.parent/'DanWesson715MetalFinish20260914/import_finish.py').read_text(encoding='utf-8')
source=source.replace("D = '/Game/Weapons/DanWesson715/MetalFinish20260914'","D = '/Game/Weapons/DanWesson715/Mirror20260914'")
source=source.replace("SOURCE = '/Game/Weapons/DanWesson715/Upgrade20260914/SK_DW715_Manny'","SOURCE = '/Game/Weapons/DanWesson715/MetalFinish20260914/SK_DW715_Manny'")
WET_ROUGH='return lerp(lerp(Base,max(.018,Base*.72),Data.a),.035,Data.b*.8);'
source=source.replace('return lerp(lerp(Base,max(.085,Base*.70),Data.a),.065,Data.b*.8);',WET_ROUGH)
source=source.replace('Satin stainless; UV0 HeroUV; baked object-space grain; geometry/rig preserved','Mirror polished steel; UV0 HeroUV; filtered engraving normals; no grain bump; geometry/rig preserved')
source=source.replace('DW715_METAL_FINISH_IMPORT_COMPLETE','DW715_MIRROR_GUN_IMPORTED')
exec(compile(source,str(O/'import_mirror.py'),'exec'),globals())

# The fitted attachment geometry, sockets and reticle sizes are already accepted
# inputs. Clone their current meshes/materials; do not reimport their FBXs.
import json,unreal as u
previous=json.loads((O.parent/'DanWesson715Attachments20260914/installed.json').read_text())
finish=json.loads((O/'attachment-finish.json').read_text());textures={};attachment_materials={};attachment_wets={}
for kind,filename in finish['textures'].items():
    t=u.AssetImportTask();t.filename=filename;t.destination_path=D+'/Attachments/Textures';t.destination_name=Path(filename).stem;t.automated=True;t.replace_existing=True;t.save=False
    A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+t.destination_name)
    tex.srgb=kind=='BaseColor';tex.compression_settings=u.TextureCompressionSettings.TC_BC7;tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    tex.set_editor_property('address_x',u.TextureAddress.TA_MIRROR);tex.set_editor_property('address_y',u.TextureAddress.TA_MIRROR)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE);save(tex);textures[kind]=tex

def replace_coating(material):
    for node in L.get_material_expressions(material):
        if isinstance(node,u.MaterialExpressionTextureSample):
            tex=node.get_editor_property('texture')
            if tex and (tex.get_name().startswith('T_DW715_Attachment_') or tex.get_name().startswith('T_DW715_Mirror_Attachment_')):
                kind='ORM' if tex.get_name().endswith('_ORM') else 'BaseColor'
                node.set_editor_property('texture',textures[kind]);node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        if isinstance(node,u.MaterialExpressionCustom):
            code=node.get_editor_property('code')
            if 'max(.085,Base*.70)' in code:node.set_editor_property('code',WET_ROUGH)
    E.set_metadata_tag(material,'DW715MirrorFinish','Mirror metal only; original optics, masks, normal and emission retained')
    L.recompile_material(material);save(material)

for name,info in previous['materials'].items():
    old=info['path'];path=D+'/Attachments/Materials/'+name
    dry=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(old,path)
    replace_coating(dry);attachment_materials[old]=dry
    old_wet=previous['wet_materials'][old];wet_path=D+'/Attachments/Wet/M_Wet_'+name
    wet=u.load_asset(wet_path) if E.does_asset_exist(wet_path) else E.duplicate_asset(old_wet,wet_path)
    replace_coating(wet);E.set_metadata_tag(wet,'DryWeaponMaterial',dry.get_path_name());save(wet)
    attachment_wets[dry.get_path_name()]=wet

attachment_receipt={}
for key,info in previous['parts'].items():
    original=u.load_asset(info['mesh']);folder=D+'/Attachments/'+(key if key in ['laser','flashlight'] else 'Meshes')
    path=folder+'/'+original.get_name()
    mesh=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(original.get_path_name(),path)
    slots=mesh.static_materials
    for i,slot in enumerate(slots):
        if slot.material_interface.get_path_name() in attachment_materials:
            slot.material_interface=attachment_materials[slot.material_interface.get_path_name()];slots[i]=slot
    mesh.set_editor_property('static_materials',slots);save(mesh)
    attachment_receipt[key]={'mesh':mesh.get_path_name(),'source':info['mesh'],'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}}

for path in ['/Game/Weather/RainVisibility/DA_WeatherPresentation','/Game/Weather/NaturalV2/DA_WeatherPresentation']:
    library=u.load_asset(path);mapping=dict(library.get_editor_property('wet_materials'));mapping.update(attachment_wets);library.set_editor_property('wet_materials',mapping);save(library)
receipt.update(attachments=attachment_receipt,attachment_materials={k:v.get_path_name() for k,v in attachment_materials.items()},
               attachment_wet_materials={k:v.get_path_name() for k,v in attachment_wets.items()},
               state='Mirror gun and four fitted attachment variants imported/saved. No game, render or additional testing.')
(O/'import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('DW715_MIRROR_IMPORT_COMPLETE')
