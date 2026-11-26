"""Use the selected head's own skin on both sides of the narrow, collar-exposed neck join."""
import json
import os
from pathlib import Path
import unreal as u

root=Path(__file__).resolve().parents[3]
batch=Path(os.environ["ARTISAN_COLLAR_BATCH"])
stage=(batch/"Host").resolve()
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()!=stage:
    raise RuntimeError("Use private copies of the two R4 neck materials")
owner="/Game/Characters/VillageMasterArtisan"
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
P=u.MaterialProperty
im=u.AssetImportTask();im.destination_path=owner+"/WorkwearR6/Textures"
im.filename=str(root/"SourceAssets/HillsVillageHighWall20261120/MasterArtisan/WorkwearR6/T_ArtisanCollarSeam.png")
im.automated=True;im.replace_existing=True;im.save=False
A.import_asset_tasks([im])
tex=u.load_asset(im.destination_path+"/T_ArtisanCollarSeam")
tex.set_editor_property("address_y",u.TextureAddress.TA_CLAMP)
tex.set_editor_property("lod_group",u.TextureGroup.TEXTUREGROUP_CHARACTER)
if not E.save_loaded_asset(tex,False):raise RuntimeError("Collar skin atlas save")
saved=[tex.get_path_name().split(".")[0]]
for slot in ("Head","Neck"):
    m=u.load_asset(owner+"/HeadR4/Materials/M_Artisan"+slot)
    def node(kind,**values):
        n=L.create_material_expression(m,kind)
        for k,v in values.items():n.set_editor_property(k,v)
        return n
    def link(src,pin,dest,to):
        if not L.connect_material_expressions(src,pin,dest,to):raise ValueError(to)
    inp=u.CustomInput();inp.set_editor_property("input_name","Rest")
    sample=node(u.MaterialExpressionCustom,description="Collar junction rest-space UV and feather",
                output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,inputs=[inp],
                code="float2 d=Rest.xy-float2(0.1,-0.85); return float3(0.5+atan2(d.x,d.y)*0.15915494,saturate((Rest.z-152.75)/4.2),1-smoothstep(0.26,1.65,abs(Rest.z-154.75)));")
    rest=node(u.MaterialExpressionVertexInterpolator)
    link(node(u.MaterialExpressionPreSkinnedPosition),"",rest,"")
    link(rest,"",sample,"Rest")
    uv=node(u.MaterialExpressionComponentMask,r=True,g=True,b=False,a=False);link(sample,"",uv,"")
    weight=node(u.MaterialExpressionComponentMask,r=False,g=False,b=True,a=False);link(sample,"",weight,"")
    image=node(u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    link(uv,"",image,"UVs")
    for prop,dest,pin in [(P.MP_BASE_COLOR,image,"RGB"),
                          (P.MP_NORMAL,node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,1,1)),""),
                          (P.MP_ROUGHNESS,node(u.MaterialExpressionConstant,r=.56),""),
                          (P.MP_METALLIC,node(u.MaterialExpressionConstant,r=0.),""),
                          (P.MP_AMBIENT_OCCLUSION,node(u.MaterialExpressionConstant,r=1.),"")]:
        prior=L.get_material_property_input_node(m,prop)
        if not prior:continue
        channel=L.get_material_property_input_node_output_name(m,prop)
        mix=node(u.MaterialExpressionLinearInterpolate)
        link(prior,channel,mix,"A");link(dest,pin,mix,"B");link(weight,"",mix,"Alpha")
        if not L.connect_material_property(mix,"",prop):raise ValueError(str(prop))
    if L.recompile_material(m):raise RuntimeError("Cannot compile "+slot+" seam")
    if not E.save_loaded_asset(m,False):raise RuntimeError("Material save "+slot)
    saved.append(m.get_path_name().split(".")[0])
(batch/"skin-saved.json").write_text(json.dumps(saved,indent=2))
