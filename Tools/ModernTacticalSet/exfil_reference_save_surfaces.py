"""Import the reference helmet's PBR maps and save material graphs in UE."""
from pathlib import Path
import json
import hashlib
import unreal as ue

P=Path(__file__).resolve().parents[2]
REVISION=globals().get("SURFACE_REVISION","ExfilReferenceR4")
PREFIX=globals().get("SURFACE_PREFIX","H1_")
TAG=globals().get("SURFACE_TAG","EXFIL")
SKINNED=REVISION in {"CoyoteGlovesR2","PatrolShirtR2","FieldTrousersR2","RidgeBootsR2"}
R=P/"SourceAssets/ModernTacticalSet20261113"/REVISION
DEST="/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/"+REVISION
E=ue.EditorAssetLibrary
A=ue.AssetToolsHelpers.get_asset_tools()
L=ue.MaterialEditingLibrary


def persist(asset):
    if not asset.get_path_name().startswith(DEST+"/") or not E.save_loaded_asset(asset,False):
        raise RuntimeError(f"Could not save {asset}")


def load_map(name,channel,expected):
    file=R/"Textures"/f"{PREFIX}{name}_{channel}.png"
    if hashlib.sha256(file.read_bytes()).hexdigest()!=expected:
        raise RuntimeError(f"Texture changed during import: {file}")
    path=DEST+"/Textures/"+file.stem
    tex=E.load_asset(path) if E.does_asset_exist(path) else None
    if tex is not None and E.get_metadata_tag(tex,TAG+"SourceSHA")==expected:
        return tex
    task=ue.AssetImportTask()
    task.filename=str(file);task.destination_path=DEST+"/Textures";task.destination_name=file.stem
    task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task])
    tex=E.load_asset(path)
    if not tex:
        raise RuntimeError(f"Failed texture import: {file}")
    clamp=ue.TextureAddress.TA_CLAMP if name=="Label" else ue.TextureAddress.TA_WRAP
    settings={
        "srgb":channel=="BaseColor","flip_green_channel":channel=="NormalGL",
        "compression_no_alpha":True,"address_x":clamp,"address_y":clamp,
        "compression_settings":{"BaseColor":ue.TextureCompressionSettings.TC_DEFAULT,
                                "NormalGL":ue.TextureCompressionSettings.TC_NORMALMAP,
                                "ORM":ue.TextureCompressionSettings.TC_MASKS}[channel]}
    for key,value in settings.items():
        tex.set_editor_property(key,value)
    E.set_metadata_tag(tex,TAG+"SourceSHA",expected);persist(tex)
    return tex


def build_material(name,info):
    maps={channel:load_map(name,channel,sha) for channel,sha in info["sha256"].items()}
    material_name="M_"+PREFIX+name;path=DEST+"/Materials/"+material_name
    material=E.load_asset(path) if E.does_asset_exist(path) else None
    fingerprint=hashlib.sha256(("exfil-surface-2"+json.dumps(info,sort_keys=True)).encode()).hexdigest()
    if material is not None and E.get_metadata_tag(material,TAG+"MaterialSHA")==fingerprint:
        # The editor can set this flag in memory when it previews a skinned mesh.
        # Save once even in that case so the cooked material includes the permutation.
        if SKINNED and (not material.get_editor_property("used_with_skeletal_mesh") or
                        E.get_metadata_tag(material,TAG+"SkinnedUsage")!="1"):
            material.set_editor_property("used_with_skeletal_mesh",True)
            E.set_metadata_tag(material,TAG+"SkinnedUsage","1")
            persist(material)
        return material,maps
    material=material or A.create_asset(material_name,DEST+"/Materials",ue.Material,ue.MaterialFactoryNew())
    if SKINNED:
        material.set_editor_property("used_with_skeletal_mesh",True)
        E.set_metadata_tag(material,TAG+"SkinnedUsage","1")
    material.set_editor_property("two_sided",False)
    material.set_editor_property("use_material_attributes",True)
    fabric=info["sheen"]>0 if "sheen" in info else name in ("Webbing","LoopPile","PadMesh","Stitch")
    material.set_editor_property("shading_model",ue.MaterialShadingModel.MSM_CLOTH if fabric else ue.MaterialShadingModel.MSM_DEFAULT_LIT)
    L.delete_all_material_expressions(material)
    attrs=L.create_material_expression(material,ue.MaterialExpressionMakeMaterialAttributes,80,0)
    L.connect_material_property(attrs,"",ue.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
    for i,(channel,texture) in enumerate(maps.items()):
        n=L.create_material_expression(material,ue.MaterialExpressionTextureSampleParameter2D,-360,230*i)
        n.set_editor_property("parameter_name",channel);n.set_editor_property("texture",texture)
        n.set_editor_property("sampler_type",{"BaseColor":ue.MaterialSamplerType.SAMPLERTYPE_COLOR,
                              "NormalGL":ue.MaterialSamplerType.SAMPLERTYPE_NORMAL,"ORM":ue.MaterialSamplerType.SAMPLERTYPE_MASKS}[channel])
        links={"BaseColor":[("RGB","BaseColor")],"NormalGL":[("RGB","Normal")],
               "ORM":[("R","AmbientOcclusion"),("G","Roughness"),("B","Metallic")]}[channel]
        for output,pin in links:
            if not L.connect_material_expressions(n,output,attrs,pin):
                raise RuntimeError(f"Material link {name}/{pin}")
    spec=L.create_material_expression(material,ue.MaterialExpressionConstant,-140,-100)
    spec.set_editor_property("r",info["specular"]);L.connect_material_expressions(spec,"",attrs,"Specular")
    if fabric and "sheen" in info:
        amount=L.create_material_expression(material,ue.MaterialExpressionConstant,-140,-190)
        amount.set_editor_property("r",info["sheen"])
        tint=L.create_material_expression(material,ue.MaterialExpressionConstant3Vector,-140,-290)
        linear=[((c/255+.055)/1.055)**2.4*.35 for c in info["base_srgb"]]
        tint.set_editor_property("constant",ue.LinearColor(*linear,1.))
        if not L.connect_material_expressions(amount,"",attrs,"ClearCoat") or not L.connect_material_expressions(tint,"",attrs,"SubsurfaceColor"):
            raise RuntimeError("Failed to bind cloth fuzz for "+name)
    if L.recompile_material(material):
        raise RuntimeError(f"Material compilation failed for {name}")
    E.set_metadata_tag(material,TAG+"MaterialSHA",fingerprint);persist(material)
    return material,maps


def main():
    out={"materials":{},"textures":{}}
    for name,info in json.loads((R/"surfaces.json").read_bytes()).items():
        mat,maps=build_material(name,info)
        out["materials"][name]=mat.get_path_name()
        out["textures"].update({t.get_name():t.get_path_name() for t in maps.values()})
    (R/"saved-surfaces.json").write_text(json.dumps(out,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
