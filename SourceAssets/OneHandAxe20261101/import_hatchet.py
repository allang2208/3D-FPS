"""Import the fitted user-selected axe and original PBR textures; save actual UE assets."""
import json
from pathlib import Path
import unreal as u

P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/OneHandAxe20261101')
DEST='/Game/Weapons/TacticalHatchet20261101'
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary;L=u.EditorAssetLibrary
receipt=dict(complete=False,assets=[],runtime_tested=False)
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name())
    (P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def imported(file,name,dest,options=None):
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=dest;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=False
    if options:
        t.options=options;t.factory=u.FbxFactory()
    A.import_asset_tasks([t])
    asset=u.load_asset(dest+'/'+name)
    if not asset: raise RuntimeError('Import failed: '+name)
    return asset
textures={}
for role,index,srgb,comp in [('BaseColor',1,True,u.TextureCompressionSettings.TC_BC7),
                            ('Normal',0,False,u.TextureCompressionSettings.TC_NORMALMAP),
                            ('MetalRough',2,False,u.TextureCompressionSettings.TC_MASKS)]:
    tex=imported(P/'Textures'/('source_image_%02d.png'%index),'T_TacticalHatchet_'+role,DEST+'/Textures')
    tex.set_editor_property('srgb',srgb);tex.set_editor_property('compression_settings',comp)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if role=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
    tex.set_editor_property('never_stream',False)
    if role=='Normal': tex.set_editor_property('flip_green_channel',True)
    textures[role]=tex;save(tex)
mat=u.load_asset(DEST+'/Materials/M_TacticalHatchet')
if not mat: mat=A.create_asset('M_TacticalHatchet',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
E.delete_all_material_expressions(mat)
mat.set_editor_property('two_sided',True)
mat.set_editor_property('used_with_nanite',True)
def node(cls,**props):
    n=E.create_material_expression(mat,cls)
    for k,v in props.items(): n.set_editor_property(k,v)
    return n
base=node(u.MaterialExpressionTextureSample,texture=textures['BaseColor'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
nrm=node(u.MaterialExpressionTextureSample,texture=textures['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
mr=node(u.MaterialExpressionTextureSample,texture=textures['MetalRough'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
slab=node(u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
for src,channel,pin,prop in [(base,'RGB','BaseColor',u.MaterialProperty.MP_BASE_COLOR),
                            (nrm,'RGB','Normal',u.MaterialProperty.MP_NORMAL),
                            (mr,'G','Roughness',u.MaterialProperty.MP_ROUGHNESS),
                            (mr,'B','Metallic',u.MaterialProperty.MP_METALLIC)]:
    if not E.connect_material_expressions(src,channel,slab,pin): raise RuntimeError('Material input: '+pin)
    E.connect_material_property(src,channel,prop)
if not E.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL): raise RuntimeError('Substrate output')
E.layout_material_expressions(mat);E.recompile_material(mat);save(mat)
ui=u.FbxImportUI();ui.import_mesh=True;ui.import_as_skeletal=False;ui.import_materials=False;ui.import_textures=False;ui.import_animations=False
sm=ui.static_mesh_import_data;sm.combine_meshes=True;sm.auto_generate_collision=True
sm.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
sm.generate_lightmap_u_vs=False
mesh=imported(P/'Export/SM_TacticalHatchet.fbx','SM_TacticalHatchet',DEST,ui)
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
settings=sub.get_lod_build_settings(mesh,0)
settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True
settings.use_high_precision_tangent_basis=True;settings.use_full_precision_u_vs=True
sub.set_lod_build_settings(mesh,0,settings)
ns=mesh.get_editor_property('nanite_settings');ns.enabled=True;mesh.set_editor_property('nanite_settings',ns)
for i in range(len(mesh.static_materials)): mesh.set_material(i,mat)
if not u.TacticalHatchetImportLibrary.finalize_mesh(mesh): raise RuntimeError('Hatchet tangent authoring failed')
L.set_metadata_tag(mesh,'Source','User-supplied Meshy_AI_Tactical_Hatchet_1101133535_texture.glb')
L.set_metadata_tag(mesh,'GripFrame','Kukri shared: cm, +Z head, +X cutting edge, fist origin')
save(mesh)
b=mesh.get_bounding_box();receipt['bounds_cm']={'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z]}
receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('HATCHET_IMPORT_SAVED '+json.dumps(receipt))
