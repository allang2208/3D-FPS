"""Reuse Witch Fabric09 with metric weave and the creature's existing masks."""
from pathlib import Path
import json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/GarmentDrapeV25')
DEST='/Game/Monsters/BoundCongregate/GarmentDrapeV25/Materials'
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
AT=u.AssetToolsHelpers.get_asset_tools()


def build():
    settings=json.loads((ROOT/'authoring.json').read_text(encoding='utf8'))['materials']
    source=u.load_asset('/Game/Monsters/WitchRebuilt/Materials/M_WitchRebuilt_Fabric09')
    if not source:
        raise RuntimeError('Retained Witch Fabric09 material is required')
    master=u.load_asset(DEST+'/M_BC_HangingFabricV25') or E.duplicate_asset(source.get_path_name(),DEST+'/M_BC_HangingFabricV25')
    marker='BC V25: metric weave, G wear, B dirt, Alpha remains cloth drive'
    for prop in ('two_sided','used_with_skeletal_mesh','used_with_clothing'):
        master.set_editor_property(prop,True)
    if E.get_metadata_tag(master,'BoundFabricRevision')!=marker:
        original=L.get_material_property_input_node(master,u.MaterialProperty.MP_BASE_COLOR)
        if not original:
            raise RuntimeError('Witch fabric colour graph missing')
        vertex=L.create_material_expression(master,u.MaterialExpressionVertexColor)
        worn=L.create_material_expression(master,u.MaterialExpressionCustom)
        worn.set_editor_property('description',marker)
        worn.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        pins=[]
        for name in ('Color','Mask'):
            pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
        worn.set_editor_property('inputs',pins)
        worn.set_editor_property('code',
            'float2 s=saturate(Mask.gb);'
            'float2 m=lerp(s/12.92,pow((s+0.055)/1.055,2.4),step(0.04045,s));'
            'float edge=pow(1-m.x,2);'
            'float dirt=m.y*0.20;'
            'return Color*(1-dirt)+float3(0.018,0.016,0.010)*edge;')
        for src,pin in ((original,'Color'),(vertex,'Mask')):
            if not L.connect_material_expressions(src,'',worn,pin):
                raise RuntimeError('V25 fabric connection failed '+pin)
        if not L.connect_material_property(worn,'',u.MaterialProperty.MP_BASE_COLOR):
            raise RuntimeError('V25 fabric base colour connection failed')
        for expr in L.get_material_expressions(master):
            if isinstance(expr,u.MaterialExpressionSubstrateShadingModels):
                if not L.connect_material_expressions(worn,'',expr,'BaseColor'):
                    raise RuntimeError('V25 Substrate fabric connection failed')
        errors=L.recompile_material(master)
        if errors:
            raise RuntimeError(str(errors))
        E.set_metadata_tag(master,'BoundFabricRevision',marker)
    if not E.save_loaded_asset(master,False):
        raise RuntimeError('V25 fabric master save failed')
    result={}
    for slot,values in settings.items():
        name='MI_'+slot+'_V25'
        instance=u.load_asset(DEST+'/'+name) or AT.create_asset(name,DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        L.set_material_instance_parent(instance,master)
        parameters={'WeaveTiling':values['weave_tiling'],
                    'RepairWeaveTiling':values['weave_tiling'],
                    'NormalStrength':.32,'Roughness':.86,'RoughnessDetail':.22,
                    'ColorDetail':.50,'Specular':.20}
        for key,value in parameters.items():
            L.set_material_instance_scalar_parameter_value(instance,key,value)
        L.set_material_instance_vector_parameter_value(instance,'ClothColor',u.LinearColor(*values['tint'],1.))
        L.update_material_instance(instance)
        if not E.save_loaded_asset(instance,False):
            raise RuntimeError('V25 fabric instance save failed '+slot)
        result[slot]=instance
    (ROOT/'material-delivery.json').write_text(json.dumps(dict(saved=True,master=master.get_path_name(),
        instances={key:value.get_path_name() for key,value in result.items()},
        alpha_contract='Both tilings equal; Alpha never changes weave density',gameplay_tested=False),indent=2),encoding='utf8')
    return result
