"""201-private baked PBR and neutral satin finish; author and save materials."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/LMG201/Video26'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE active; Video26 asset import has not started')
receipt={'materials':{},'textures':{},'finish_clones':{},'tested':False}

def record():(O/'materials_receipt.json').write_text(json.dumps(receipt,indent=2))
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def node(mat,cls,**props):
    n=M.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(src,dst,pin):
    n,out=src if isinstance(src,tuple) else (src,'')
    if not M.connect_material_expressions(n,out,dst,pin):raise RuntimeError('Cannot connect '+pin)
def output(src,prop):
    n,pin=src if isinstance(src,tuple) else (src,'')
    if not M.connect_material_property(n,pin,prop):raise RuntimeError('Cannot bind '+str(prop))
def param(mat,key,value,vector=False):
    cls=u.MaterialExpressionVectorParameter if vector else u.MaterialExpressionScalarParameter
    n=next((n for n in M.get_material_expressions(mat) if isinstance(n,cls) and str(n.get_editor_property('parameter_name'))==key),None)
    if n is None:n=node(mat,cls,parameter_name=key)
    n.set_editor_property('default_value',u.LinearColor(*value,1) if vector else value)
    return n
def compile_save(mat):
    errors=M.recompile_material(mat)
    if errors:raise RuntimeError('Material compiler '+mat.get_path_name()+': '+str(errors))
    E.set_metadata_tag(mat,'LMG201FinishRevision','Video26: neutral charcoal, baked high-poly fillets, restrained edge wear')
    save(mat)

def wet_layer(mat):
    if any(str(n)=='WeaponWetness' for n in M.get_scalar_parameter_names(mat)):return
    wet=param(mat,'WeaponWetness',0.)
    sat=node(mat,u.MaterialExpressionSaturate);wire(wet,sat,'')
    for prop,amount in [(u.MaterialProperty.MP_BASE_COLOR,.74),(u.MaterialProperty.MP_ROUGHNESS,.48)]:
        base=M.get_material_property_input_node(mat,prop)
        pin=M.get_material_property_input_node_output_name(mat,prop)
        if not base:continue
        mul=node(mat,u.MaterialExpressionMultiply,const_b=amount);wire((base,pin),mul,'A')
        blend=node(mat,u.MaterialExpressionLinearInterpolate)
        wire((base,pin),blend,'A');wire(mul,blend,'B');wire(sat,blend,'Alpha');output(blend,prop)

def create_baked(group):
    textures={}
    for kind in ['BaseColor','Normal','ORM']:
        src=O/'Textures'/('T_LMG201_V26_'+group+'_'+kind+'.png')
        task=u.AssetImportTask();task.filename=str(src);task.destination_path=P+'/Textures';task.destination_name=src.stem
        task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
        tex=u.load_asset(task.destination_path+'/'+src.stem)
        if not tex or not task.imported_object_paths:raise RuntimeError('Texture import failed '+str(src))
        tex.set_editor_property('srgb',kind=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7 if kind=='BaseColor' else
            u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property('flip_green_channel',kind=='Normal')
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON)
        save(tex);textures[kind]=tex;receipt['textures'][tex.get_path_name()]={'source':str(src),'kind':kind};record()
    name='M_LMG201_Video26_'+group;path=P+'/Materials/'+name
    mat=u.load_asset(path) or A.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew())
    M.delete_all_material_expressions(mat)
    mat.set_editor_property('automatically_set_usage_in_editor',False)
    mat.set_editor_property('used_with_skeletal_mesh',group=='Body')
    mat.set_editor_property('two_sided',False)
    samples={}
    for kind,tex in textures.items():
        samples[kind]=node(mat,u.MaterialExpressionTextureSample,texture=tex,
            sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else
            u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    output((samples['BaseColor'],'RGB'),u.MaterialProperty.MP_BASE_COLOR)
    output((samples['Normal'],'RGB'),u.MaterialProperty.MP_NORMAL)
    for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:
        output((samples['ORM'],pin),prop)
    output(param(mat,'Specular',.5),u.MaterialProperty.MP_SPECULAR)
    wet_layer(mat);compile_save(mat)
    receipt['materials'][group]=mat.get_path_name();record()

for group in ['Body','FrontSight','RearSight']:create_baked(group)

# BodyRollback27: the user reverted the factory body/barrel finish.
# Preserve their Material21 bindings on subsequent authoring runs.
steel={'M_LMG201_BipodBase','M_LMG201_BipodLegA','M_LMG201_BipodLegB'}
paths=['/Game/Weapons/LMG201/Production20260927/SM_LMG201_'+n for n in ['BipodBase','BipodLegA','BipodLegB']]
slot_bindings={};source_cache={}
for path in paths:
    mesh=u.load_asset(path)
    if not mesh:continue
    slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
    for s in slots:
        key=str(s.material_slot_name)
        if key not in steel or not s.material_interface:continue
        original=s.material_interface;source=original.get_path_name()
        if source not in source_cache:
            name=original.get_name()+'_V26';dest=P+'/Materials/'+name
            mat=u.load_asset(dest) or E.duplicate_asset(source,dest)
            if not isinstance(mat,u.Material):continue
            names={str(n) for n in M.get_scalar_parameter_names(mat)}
            vectors={str(n) for n in M.get_vector_parameter_names(mat)}
            if 'FinishColor' in vectors:param(mat,'FinishColor',(.027,.029,.031),True)
            for k,v in [('Metallic',.82),('RoughnessCenter',.40),('SourceColorWeight',.07),('LMG201MicroRoughness',.016)]:
                if k in names:param(mat,k,v)
            wet_layer(mat);compile_save(mat);source_cache[source]=mat.get_path_name()
            receipt['finish_clones'][source]=mat.get_path_name();record()
        slot_bindings.setdefault(mesh.get_path_name(),{})[key]=source_cache[source]
receipt['bindings']=slot_bindings;receipt['status']='materials_compiled_and_saved';record()
print('VIDEO26_MATERIALS_SAVED',len(receipt['materials']),len(receipt['textures']),len(receipt['finish_clones']),flush=True)
