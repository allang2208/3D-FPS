"""Extend the live concrete graph without deleting or replacing its existing nodes.

All existing mesh/actor bindings continue to use the same material. Horizontal
faces explicitly bypass POM. Existing maps use original UV derivatives.
"""
import hashlib,json,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
from restore_wall_relief import ROOT,PROJECT,backup,save
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
PATH='/Game/Dungeons/AtmosphereV2/Materials/M_Concrete'
TAG='DungeonConcretePhysicalRelief20260924'

def install():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ue and ue.get_game_world():raise RuntimeError('Preserve running game')
    if PATH in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved concrete material')
    # The approved scanned release now owns the shared concrete entry.
    sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
    import dungeon_wall_release
    if dungeon_wall_release.publish_concrete():return
    mat=u.load_asset(PATH)
    code=(ROOT/'Scripts/concrete_parallax.ush').read_text()
    signature=hashlib.sha256(code.encode()).hexdigest()
    prior=E.get_metadata_tag(mat,TAG)
    if prior:
        if prior!=signature:raise RuntimeError('Concrete relief graph revision differs')
        print('CONCRETE_RELIEF_ALREADY_SAVED',flush=True);return
    expressions=list(L.get_material_expressions(mat))
    samples=[n for n in expressions if n.__class__.__name__=='MaterialExpressionTextureSample']
    expected={'T_Concrete_BaseColor','T_Concrete_Normal','T_Concrete_Roughness','T_Concrete_Metallic'}
    if {n.get_editor_property('texture').get_name() for n in samples}!=expected or len(expressions)!=4:
        raise RuntimeError('Live concrete graph has changed; preserve it')
    manifest=json.loads((ROOT/'Authored/concrete-height.json').read_text())
    texpath='/Game/Dungeons/AtmosphereV2/WallRelief/Textures/T_Concrete_OriginalPhysicalHeight'
    tex=u.load_asset(texpath)
    if not tex:
        task=u.AssetImportTask();task.filename=manifest['texture'];task.destination_path=texpath.rsplit('/',1)[0]
        task.destination_name=texpath.rsplit('/',1)[1];task.automated=True;task.save=False
        A.import_asset_tasks([task]);tex=u.load_asset(texpath)
        if not tex:raise RuntimeError('Height import failed')
        tex.set_editor_property('srgb',False)
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_HALF_FLOAT)
        save(tex)
    backup(mat);mat.modify()
    def node(kind,**props):
        n=L.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def wire(src,dst,pin='',output=''):
        if not L.connect_material_expressions(src,output,dst,pin):raise RuntimeError('Connection '+pin)
    uv=node('TextureCoordinate')
    view=node('Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
              transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    wire(node('CameraVectorWS'),view)
    dist=node('Distance');wire(node('WorldPosition'),dist,'A');wire(node('CameraPositionWS'),dist,'B')
    inputs={'UV':uv,'View':view,'DistanceCm':dist,'WorldNormal':node('VertexNormalWS'),
            'DepthCm':node('ScalarParameter',parameter_name='WallConcreteReliefDepthCm',default_value=manifest['range_cm']),
            'HeightTex':node('TextureObjectParameter',parameter_name='ConcretePhysicalHeight',texture=tex,
                             sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)}
    custom=node('Custom',code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT2,desc='Original concrete height: vertical wall POM')
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    custom.set_editor_property('inputs',pins)
    for name,src in inputs.items():wire(src,custom,name)
    dx=node('DDX');dy=node('DDY');wire(uv,dx);wire(uv,dy)
    for sample in samples:
        sample.set_editor_property('mip_value_mode',u.TextureMipValueMode.TMVM_DERIVATIVE)
        wire(custom,sample,'UVs');wire(dx,sample,'DDX(UVs)');wire(dy,sample,'DDY(UVs)')
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    mat.set_editor_property('used_with_nanite',True)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    E.set_metadata_tag(mat,TAG,signature)
    L.layout_material_expressions(mat);save(mat)
    report={'stage':'material_saved','material':PATH,'height':texpath,'height_range_cm':manifest['range_cm'],
            'previous_nodes':len(expressions),'new_nodes':len(L.get_material_expressions(mat)),
            'all_four_channels_share_offset':True,'horizontal_faces_bypass':True,'runtime_tested':False}
    (ROOT/'Receipts/concrete-install.json').write_text(json.dumps(report,indent=2))
    print('CONCRETE_WALL_RELIEF_SAVED',json.dumps(report),flush=True)

if __name__=='__main__':install()
