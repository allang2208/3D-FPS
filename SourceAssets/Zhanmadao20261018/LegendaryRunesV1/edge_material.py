"""Restore the original inlay atlases on the selected blade's two broad faces."""
import unreal as u

L = u.MaterialEditingLibrary
TAG = "ZhanmadaoRuneEdgeV1 "
STEEL = "ZhanmadaoDamascus20261111V2 "
FIELDS = {"BASE_COLOR": "BaseColor", "ROUGHNESS": "Roughness", "METALLIC": "Metallic",
          "NORMAL": "Normal", "ANISOTROPY": "Anisotropy"}


def apply(material, profile):
    nodes = list(L.get_material_expressions(material))
    named = {str(n.get_editor_property("desc")): n for n in nodes}

    def node(cls, label, **settings):
        desc = TAG + label
        value = named.get(desc)
        if value is None:
            value = L.create_material_expression(material, cls)
            named[desc] = value
        value.set_editor_properties(dict(desc=desc, **settings))
        return value

    def wire(source, output, target, name):
        normalize = lambda s: str(s).replace(" ", "").replace("_", "").lower()
        pin = next((str(n) for n in L.get_material_expression_input_names(target)
                    if normalize(n) == normalize(name)), name)
        if not L.connect_material_expressions(source, output, target, pin):
            raise RuntimeError("Cannot connect " + target.get_name() + "." + name)

    def custom(label, channels, code, **inputs):
        value = node(u.MaterialExpressionCustom, label, code=code,
                     output_type=getattr(u.CustomMaterialOutputType, "CMOT_FLOAT" + str(channels)))
        pins = []
        for name in inputs:
            pin = u.CustomInput()
            pin.set_editor_property("input_name", name)
            pins.append(pin)
        value.set_editor_property("inputs", pins)
        for name, item in inputs.items():
            source, output = item if isinstance(item, tuple) else (item, "")
            wire(source, output, value, name)
        return value

    def original_input(target, name):
        names = L.get_material_expression_input_names(target)
        sources = L.get_inputs_for_material_expression(material, target)
        for pin, upstream in zip(names, sources):
            if str(pin) == name and upstream:
                return upstream, str(L.get_input_node_output_name_for_material_expression(target, upstream))
        raise RuntimeError("Missing " + name + " on " + target.get_name())

    def texture_parameter(name, sampler):
        # Reuse an already resident donor as the neutral default. Only equipped
        # rune artwork is requested at runtime, and style zero skips its samples.
        native = next((n for n in nodes if isinstance(n, u.MaterialExpressionTextureSample)
                      and n.get_editor_property("texture") and n.get_editor_property("sampler_type") == sampler
                      and not str(n.get_editor_property("desc")).startswith(TAG)), None)
        default = (native.get_editor_property("texture") if native else u.load_asset(
            "/Game/Weapons/Zhanmadao20261018/ChixiaoBladeV1/Textures/T_Chixiao_" +
            ("BaseColor" if name == "DaoInlayColor" else "ORM") + "_V1"))
        if not default:
            raise RuntimeError("No default texture for " + name)
        return node(u.MaterialExpressionTextureObjectParameter, name, parameter_name=name,
                    texture=default, sampler_type=sampler)

    style = node(u.MaterialExpressionScalarParameter, "style", parameter_name="DaoInlayStyle", default_value=0.)
    color = texture_parameter("DaoInlayColor", u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    orm = texture_parameter("DaoInlayORM", u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    geom = named[STEEL + "profile interpolator"]
    normal = named[STEEL + "normal interpolator"]
    z0, z1 = profile["blade_z"]
    z, arc = profile["z"], profile["arc"]
    start = (z[0] - z0) / (z1 - z0)
    scale = ((z[-1] - z[0]) / (z1 - z0)) / (arc[-1] - arc[0])
    uv = custom("source atlas coordinates", 2,
                f"return float2(G.z,1.-({start:.10f}+(G.y-{arc[0]:.10f})*{scale:.10f}));", G=geom)
    # Width and end gates are from the final Chixiao and Zhufeng atlas recipes.
    # Filter the thin double rails with the source art's mip footprint.
    coverage = custom("face coverage", 1, """
if (Style < .5) return 0.;
float u = UV.x, t = 1.-UV.y;
bool crimson = Style < 1.5;
float shoulder = .095+.170*smoothstep(.06,.24,t)*(1.-smoothstep(.74,.97,t));
float outer = crimson ? shoulder : .125;
float inner = crimson ? .051 : .054;
float gate = crimson ? smoothstep(.065,.105,t)*(1.-smoothstep(.91,.97,t))
                     : smoothstep(.065,.10,t)*(1.-smoothstep(.92,.96,t));
float band = smoothstep(inner-.003,inner+.003,u)*(1.-smoothstep(outer-.004,outer+.004,u));
float railA = crimson ? .043 : .048, railB = crimson ? shoulder+.008 : .132;
float width = crimson ? .0018 : .0016;
float aa = max(.00001,fwidth(u));
float railDist = min(abs(u-railA),abs(u-railB));
float rails = (1.-smoothstep(1.3*width,2.2*width+aa*.5,railDist));
return max(band,rails)*gate*smoothstep(.35,.76,abs(normalize(N).y))
       *(1.-saturate(Keepout*3.))*(1.-saturate(Ink.a));
""", Style=style, UV=uv, N=normal,
                      Keepout=named["DaoLongitudinal20261110V2 decoration keepout"],
                      Ink=next(n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
                               and "RuneTexture" in str(n.get_editor_property("code"))))

    def sample(label, texture, channels, swizzle):
        return custom(label, channels, """
float2 dx=ddx(UV),dy=ddy(UV);
[branch] if(Coverage<=0.) return 0.;
return Texture2DSampleGrad(Art,ArtSampler,saturate(UV),dx,dy).""" + swizzle + ";",
                      Art=texture, UV=uv, Coverage=coverage)

    pigment = sample("original color", color, 3, "rgb")
    surface = sample("original roughness and metal", orm, 2, "gb")
    slab = L.get_material_property_input_node(material, u.MaterialProperty.MP_FRONT_MATERIAL)
    for field, pin in FIELDS.items():
        inputs = {"Finish": named[STEEL + field], "Coverage": coverage}
        if field == "BASE_COLOR":
            inputs["Pigment"] = pigment
            value = "Pigment"
        elif field in ("ROUGHNESS", "METALLIC"):
            inputs["Surface"] = surface
            value = "Surface.x" if field == "ROUGHNESS" else "Surface.y"
        elif field == "NORMAL":
            native = original_input(named[STEEL + field], "Base")
            upstream = native[0]
            if isinstance(upstream, u.MaterialExpressionCustom) and "Base" in [
                    str(pin) for pin in L.get_material_expression_input_names(upstream)]:
                native = original_input(upstream, "Base")
            inputs["Native"] = native
            value = "Native"
        else:
            value = "0."
        result = "lerp(Finish," + value + ",Coverage)"
        channels = 3 if field in ("BASE_COLOR", "NORMAL") else 1
        out = custom(field, channels, "return " + result + ";", **inputs)
        prop = getattr(u.MaterialProperty, "MP_" + field)
        if not L.connect_material_property(out, "", prop):
            raise RuntimeError("Cannot connect property " + field)
        wire(out, "", slab, pin)
