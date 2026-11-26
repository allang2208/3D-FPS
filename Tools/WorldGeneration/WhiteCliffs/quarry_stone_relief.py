"""Build the quarry's near-field stone relief without changing its meshes or scan unwraps."""
from pathlib import Path
import runpy

import unreal as ue

LIB = ue.MaterialEditingLibrary
ASSETS = ue.EditorAssetLibrary
ROOT = "/Game/WorldGeneration/TemperateHills/WhiteCliffs"
TEXTURES = ROOT + "/Textures"
SOURCE = Path(__file__).resolve().parents[3] / "SourceAssets/HillsQuarryCutYard/StoneRelief"
TAG = "Quarry.Relief."
SHADING = runpy.run_path(str(Path(__file__).with_name("quarry_relief_shading.py")))

# (material subfolder, texture family, height cm, maximum UV displacement, grain strength).
# The three atlas caps stay within approximately one source texel at game resolution.
PROFILES = {
    "M_CliffA": ("", "CliffA", .92, .00040, .26),
    "M_CliffB": ("", "CliffB", 1.08, .00040, .29),
    "M_LimestoneSpoil": ("", "Spoil", .23, .00030, .18),
    "M_LimestoneCut": ("", "Stone", .54, .0060, .65),
    "M_QuarryWeatheredBed": ("CutYard", "Cliff", .78, .0065, .84),
    "M_QuarryFreshBreak": ("CutYard", "Stone", .57, .0055, .76),
    "M_QuarryBeddedLime": ("Approach", "Cliff", 1.12, .0075, 1.18),
    "M_QuarryRivenLime": ("Approach", "Cliff", 1.34, .0090, 1.28),
    "M_QuarryTooledLime": ("Approach", "Stone", .43, .0045, .81),
}

# The scan bump is registered to its own unwrap. Stay near its original sample even on
# grazing slopes and resolve fine slopes only while the pixel footprint supports them.
SCAN_NORMAL = """
float2 dx=ddx(UV), dy=ddy(UV);
float pitch=1./2048.;
float lodFootprint=max(length(dx),length(dy))/pitch;
float visible=(1.-smoothstep(1.35,4.5,lodFootprint))*(1.-smoothstep(240.,750.,length(P)));
[branch] if(visible<.002) return normalize(BaseN);
float2 ex=float2(pitch,0), ey=ex.yx;
float hx=Texture2DSampleGrad(GrainTex,GrainTexSampler,UV+ex,dx,dy).g-
         Texture2DSampleGrad(GrainTex,GrainTexSampler,UV-ex,dx,dy).g;
float hy=Texture2DSampleGrad(GrainTex,GrainTexSampler,UV+ey,dx,dy).g-
         Texture2DSampleGrad(GrainTex,GrainTexSampler,UV-ey,dx,dy).g;
return normalize(float3(BaseN.xy-float2(hx,hy)*Tune.x*visible*BaseN.z,BaseN.z));
"""

CUT_COLOR = """
float3 stone=Base;
float l=dot(stone,float3(.213,.715,.072));
float chalk=lerp(l,.17+.31*(l-.17),smoothstep(.18,.67,l)*.88);
float fracture=lerp(.81,1.04,smoothstep(.23,.75,Height));
return chalk*float3(.73,.72,.67)*fracture*lerp(.77,1.,saturate(Open))*(.87+.34*BreakField.x);
"""


def required(path):
    asset = ue.load_asset(path)
    if not asset:
        raise RuntimeError("Missing quarry material dependency " + path)
    return asset


def save(asset):
    if not ASSETS.save_loaded_asset(asset, False):
        raise RuntimeError("Could not save " + asset.get_path_name())


def scan_texture(family, reimport=False):
    name = "T_Quarry" + family + "Relief"
    path = TEXTURES + "/" + name
    if reimport or not ASSETS.does_asset_exist(path):
        task = ue.AssetImportTask()
        task.filename = str(SOURCE / (name + ".png"))
        task.destination_path, task.destination_name = TEXTURES, name
        task.automated = True
        task.replace_existing = True
        task.save = False
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        tex = required(path)
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", ue.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("virtual_texture_streaming", False)
        save(tex)
    return required(path)


def normandy_texture(family):
    donor = required("/Game/UnrealNormandy/Textures/T_" + family + "Surface_03A_RHAOM")
    if (not donor.virtual_texture_streaming and not donor.srgb and
            donor.compression_settings in (ue.TextureCompressionSettings.TC_MASKS, ue.TextureCompressionSettings.TC_DEFAULT)):
        return donor
    # Explicit gradient texture-object reads require an ordinary linear texture. Never
    # change the import settings of a Normandy map used elsewhere in the hills.
    path = TEXTURES + "/T_Quarry" + family + "Packed"
    if not ASSETS.does_asset_exist(path):
        duplicate = ASSETS.duplicate_asset(donor.get_path_name(), path)
        if not duplicate:
            raise RuntimeError("Could not duplicate " + donor.get_path_name())
        duplicate.set_editor_property("srgb", False)
        duplicate.set_editor_property("compression_settings", ue.TextureCompressionSettings.TC_MASKS)
        duplicate.set_editor_property("virtual_texture_streaming", False)
        duplicate.set_editor_property("max_texture_size", 2048)
        save(duplicate)
    return required(path)


def wire(source, target, pin):
    expr, output = source if isinstance(source, tuple) else (source, "")
    if not LIB.connect_material_expressions(expr, output, target, pin):
        raise RuntimeError("Cannot connect " + expr.get_name() + " to " + target.get_name() + "." + pin)


def bind(source, prop):
    expr, output = source if isinstance(source, tuple) else (source, "")
    if not LIB.connect_material_property(expr, output, prop):
        raise RuntimeError("Cannot bind " + expr.get_name() + " to " + str(prop))


def apply_stone_relief(mat):
    """Update our named nodes in place. The caller owns recompilation and saving."""
    name = mat.get_name()
    if name not in PROFILES:
        return False
    folder, family, depth, uv_cap, grain_strength = PROFILES[name]
    owner = ROOT + "/Materials/" + (folder + "/" if folder else "") + name
    if mat.get_path_name().split(".")[0] != owner:
        return False
    atlas = family in ("CliffA", "CliffB", "Spoil")
    data = scan_texture(family) if atlas else normandy_texture(family)
    nodes = list(LIB.get_material_expressions(mat))
    def label_of(expr):
        return str(expr.get_editor_property("desc"))

    marked = {label_of(n): n for n in nodes if label_of(n).startswith(TAG)}
    mat.modify()

    def node(kind, label):
        key = TAG + label
        if key not in marked:
            marked[key] = LIB.create_material_expression(mat, getattr(ue, "MaterialExpression" + kind))
            marked[key].set_editor_property("desc", key)
        return marked[key]

    def vector(label, values):
        n = node("Constant4Vector", label)
        n.set_editor_property("constant", ue.LinearColor(*values))
        return n

    def custom(label, channels, code, sources):
        n = node("Custom", label)
        if [str(p.get_editor_property("input_name")) for p in n.get_editor_property("inputs")] != list(sources):
            pins = []
            for key in sources:
                pin = ue.CustomInput()
                pin.set_editor_property("input_name", key)
                pins.append(pin)
            n.set_editor_property("inputs", pins)
        n.set_editor_property("output_type", getattr(ue.CustomMaterialOutputType, "CMOT_FLOAT" + str(channels)))
        n.set_editor_property("code", code)
        for pin, source in sources.items():
            wire(source, n, pin)
        return n

    def input_at(expr, index):
        inputs = LIB.get_inputs_for_material_expression(mat, expr)
        return inputs[index] if len(inputs) > index else None

    def upstream(prop, wrapper_label):
        current = LIB.get_material_property_input_node(mat, prop)
        if not current:
            raise RuntimeError(name + " has no authored " + str(prop))
        if label_of(current) == TAG + wrapper_label:
            previous = input_at(current, 0)
            if not previous:
                raise RuntimeError(name + " has lost the source of " + wrapper_label)
            return previous, LIB.get_input_node_output_name_for_material_expression(current, previous) or ""
        return current, LIB.get_material_property_input_node_output_name(mat, prop) or ""

    def texture_node(kind, label, image):
        n = node(kind, label)
        n.set_editor_property("texture", image)
        typ = "MASKS" if image.compression_settings == ue.TextureCompressionSettings.TC_MASKS else "LINEAR_COLOR"
        n.set_editor_property("sampler_type", getattr(ue.MaterialSamplerType, "SAMPLERTYPE_" + typ))
        return n

    props = ue.MaterialProperty
    # The first UV input to the original normal sample defines the unwrap (including
    # the x3 cut-face projection). Leave the slow rotated mineral sample untouched.
    def connected_nodes():
        roots = [LIB.get_material_property_input_node(mat, prop) for prop in
                 (props.MP_BASE_COLOR, props.MP_NORMAL, props.MP_ROUGHNESS,
                  props.MP_AMBIENT_OCCLUSION, props.MP_METALLIC, props.MP_SPECULAR)]
        connected = set()
        while roots:
            current = roots.pop()
            if current and current.get_name() not in connected:
                connected.add(current.get_name())
                roots.extend(LIB.get_inputs_for_material_expression(mat, current))
        return connected

    active = connected_nodes()
    samples = [n for n in nodes if n.get_name() in active and isinstance(n, ue.MaterialExpressionTextureSample) and n.texture and
               not label_of(n).startswith(TAG)]
    normal_sample = next(n for n in samples if n.texture.get_name().endswith("_Normal"))
    parallax_old = marked.get(TAG + "Parallax")
    uv = input_at(parallax_old, 0) if parallax_old else input_at(normal_sample, 0)
    if not uv:
        uv = node("TextureCoordinate", "ScanUV")
    main_samples = [n for n in samples if input_at(n, 0) in (None, uv, parallax_old)]
    if normal_sample not in main_samples:
        raise RuntimeError(name + " ambiguous authored normal coordinates")
    pos = node("WorldPosition", "EyeRelativePosition")
    pos.set_editor_property("world_position_shader_offset", ue.WorldPositionIncludedOffsets.WPT_CAMERA_RELATIVE_NO_OFFSETS)
    view = node("CameraVectorWS", "View")
    height = texture_node("TextureObject", "HeightObject", data)
    far = 600. if family == "Spoil" else 1150.
    offset = custom("Parallax", 2, SHADING["PARALLAX"], {
        "UV": uv, "P": pos, "V": view, "HeightTex": height,
        "Tune": vector("HeightProfile", (depth, uv_cap, 0. if atlas else 1., far))})
    for n in main_samples:
        wire(offset, n, "UVs")

    packed = texture_node("TextureSample", "SurfaceMasks", data)
    wire(offset, packed, "UVs")
    base_n = upstream(props.MP_NORMAL, "GrainNormal")
    if name == "M_LimestoneCut" and isinstance(base_n[0], ue.MaterialExpressionLinearInterpolate):
        base_n[0].set_editor_property("const_alpha", .84)
    strength = vector("GrainProfile", (grain_strength, 23., far * .75, 3. if name == "M_LimestoneCut" else 1.))
    normal_inputs = {"BaseN": base_n, "UV": offset, "P": pos, "GrainTex": height, "Tune": strength}
    normal_code = SCAN_NORMAL if atlas else SHADING["GRAIN_NORMAL"]
    exposed = name in ("M_LimestoneCut", "M_QuarryFreshBreak")
    if exposed:
        break_map = texture_node("TextureObject", "BreakTexture", normandy_texture("Cliff"))
        field = custom("BreakField", 3, SHADING["BREAK_FIELD"], {"P": pos, "StoneTex": break_map})
        break_depth = node("Constant", "BreakDepth")
        break_depth.set_editor_property("r", .62 if name == "M_LimestoneCut" else .29)
        normal_inputs.update(BreakField=field, BreakDepth=break_depth)
        normal_code = SHADING["BREAK_NORMAL"] + normal_code
    normal = custom("GrainNormal", 3, normal_code, normal_inputs)
    bind(normal, props.MP_NORMAL)

    old_rough = upstream(props.MP_ROUGHNESS, "Roughness")
    weather = next((n for n in nodes if n.get_name() in active and isinstance(n, ue.MaterialExpressionCollectionParameter)
                    and str(n.get_editor_property("parameter_name")) == "WeatherWetness"), None)
    if not weather:
        weather = node("CollectionParameter", "Wetness")
        weather.set_editor_property("collection", required("/Game/Weather/Materials/MPC_FPS_Weather"))
        weather.set_editor_property("parameter_name", "WeatherWetness")
    if atlas:
        map_rough = next(n for n in samples if n.texture.get_name().endswith("_Roughness"))
    else:
        map_rough = packed
        bind((packed, "B"), props.MP_AMBIENT_OCCLUSION)
    rough = custom("Roughness", 1, SHADING["ROUGHNESS"], {
        "OldR": old_rough, "MapR": (map_rough, "R"), "Occlusion": (packed, "B"), "Wet": weather,
        "Tune": vector("RoughnessProfile", ROUGH_PROFILE[name])})
    bind(rough, props.MP_ROUGHNESS)

    # Regrade only the exposed cut faces. The dry cap inside the existing weather
    # wrapper keeps detached triangles legible against the dusty spoil in direct sun.
    if exposed:
        color = LIB.get_material_property_input_node(mat, props.MP_BASE_COLOR)
        wrapped = label_of(color) == "Quarry.WorkedStone.Color"
        old = input_at(color, 0) if wrapped else color
        if label_of(old) == TAG + "CutPigment":
            old = input_at(old, 0)
        pigment_code = CUT_COLOR if name == "M_LimestoneCut" else (
            "return Base*float3(.90,.89,.86)*(.94+.19*BreakField.x)*lerp(.92,1.,Open);")
        pigment = custom("CutPigment", 3, pigment_code, {
            "Base": old, "Open": (packed, "B"), "Height": (packed, "G"), "BreakField": field})
        if wrapped:
            wire(pigment, color, "Base")
        else:
            bind(pigment, props.MP_BASE_COLOR)
    elif not atlas:
        # The upstream limestone still supplies its mineral stain, lichen and tooling.
        # Add a little value separation at the lip of a pore and keep the distant face quiet.
        old_color = upstream(props.MP_BASE_COLOR, "PoreTone")
        tone = custom("PoreTone", 3, """
float close=1.-smoothstep(350.,1200.,length(P));
float lip=clamp((H-.49)*.46,-.18,.14);
return Base*(1.+close*(lip-.13*(1.-saturate(AO))));
""", {"Base": old_color, "H": (packed, "G"), "AO": (packed, "B"), "P": pos})
        bind(tone, props.MP_BASE_COLOR)
    if folder in ("Approach", "CutYard"):
        # Previously regenerated procedural graphs retained disconnected portions
        # of older versions. These five materials are fully defined by their builders.
        live = connected_nodes()
        for n in nodes:
            if n.get_name() not in live:
                LIB.delete_material_expression(mat, n)
    return True


def rebuild():
    for family in ("CliffA", "CliffB", "Spoil"):
        scan_texture(family, reimport=True)
    for name, (folder, *_) in PROFILES.items():
        path = ROOT + "/Materials/" + (folder + "/" if folder else "") + name
        mat = required(path)
        apply_stone_relief(mat)
        errors = LIB.recompile_material(mat)
        if errors:
            raise RuntimeError(path + " " + str(errors))
        save(mat)
        ue.log("QUARRY_RELIEF_SAVED " + path)
    ue.log("QUARRY_RELIEF_BUILD_COMPLETE")


ROUGH_PROFILE = {
    "M_CliffA": (.79, .46, .68, .14),
    "M_CliffB": (.81, .48, .72, .15),
    "M_LimestoneSpoil": (.85, .55, .63, .16),
    "M_LimestoneCut": (.78, .51, .67, .11),
    "M_QuarryWeatheredBed": (.80, .49, .78, .15),
    "M_QuarryFreshBreak": (.78, .52, .69, .12),
    "M_QuarryBeddedLime": (.80, .49, .79, .15),
    "M_QuarryRivenLime": (.83, .53, .84, .16),
    "M_QuarryTooledLime": (.76, .47, .63, .10),
}

if __name__ == "__main__":
    rebuild()

