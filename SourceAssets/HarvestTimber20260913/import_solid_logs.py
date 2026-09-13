"""Import repaired timber only, then export the saved UE meshes for focused inspection."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).parent/'SolidRepair';SRC=ROOT/'Delivery';DEST='/Game/Items/HarvestTimber'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
def create(name,cls,factory):return u.load_asset(DEST+'/'+name) or A.create_asset(name,DEST,cls,factory)
def import_file(file,name,options=None):
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=DEST;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=False;t.options=options
    A.import_asset_tasks([t]);obj=u.load_asset(DEST+'/'+name)
    if obj is None:raise RuntimeError('Import failed '+name)
    return obj
textures={}
for kind in ('BaseColor','Roughness','Normal'):
    t=import_file(SRC/('T_PoplarSolid_'+kind+'.png'),'T_PoplarSolid_'+kind);t.srgb=kind=='BaseColor'
    if kind=='Normal':
        t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP;t.set_editor_property('flip_green_channel',True)
    elif kind=='Roughness':t.compression_settings=u.TextureCompressionSettings.TC_MASKS
    save(t);textures[kind]=t
bark=create('M_PoplarSolidBark',u.Material,u.MaterialFactoryNew())
for n in list(L.get_material_expressions(bark)):L.delete_material_expression(bark,n)
bark.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
for kind,prop,pin in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR,'RGB'),('Roughness',u.MaterialProperty.MP_ROUGHNESS,'R'),('Normal',u.MaterialProperty.MP_NORMAL,'RGB')]:
    n=L.create_material_expression(bark,u.MaterialExpressionTextureSample);n.texture=textures[kind]
    if kind=='Normal':n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL
    elif kind=='Roughness':n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS
    L.connect_material_property(n,pin,prop)
L.recompile_material(bark);save(bark)
end=u.load_asset(DEST+'/M_PoplarSolidEnd') or E.duplicate_asset(DEST+'/M_PoplarEnd',DEST+'/M_PoplarSolidEnd')
end.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE);L.recompile_material(end);save(end)
report={};exports=ROOT/'UEExport';exports.mkdir(exist_ok=True)
for kind in 'ABC':
    name='SM_PoplarLog_Solid_'+kind
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    opt.static_mesh_import_data.combine_meshes=True
    mesh=import_file(SRC/(name+'.fbx'),name,opt);slots=mesh.static_materials
    for i,slot in enumerate(slots):slot.material_interface=end if 'EndGrain' in str(slot.material_slot_name) else bark;slots[i]=slot
    mesh.set_editor_property('static_materials',slots);save(mesh)
    task=u.AssetExportTask();task.object=mesh;task.filename=str(exports/(name+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True
    export=u.FbxExportOption();export.level_of_detail=False;export.collision=False;task.options=export
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export saved mesh '+name)
    report[name]={'path':mesh.get_path_name(),'bounds':str(mesh.get_bounds()),'materials':[s.material_interface.get_path_name() for s in mesh.static_materials]}
(ROOT/'import.json').write_text(json.dumps(report,indent=2))
u.log('SOLID_TIMBER_IMPORTED_AND_EXPORTED count='+str(len(report)))
