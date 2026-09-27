"""Create the M3 assets of the GPU grass interaction system (footstep feedback).

Run headless through Tools/GrassDeform/run_asset_setup_m3.ps1, or through the MCP batch bridge while
an editor holds the project. The script is idempotent: every step checks for the existing asset or
property and only authors what is missing, so it can be re-run after a partial failure. Re-running
after a *contract* change is handled by the version tags below, which rebuild a stale graph instead
of silently keeping it.

Creates under /Game/WorldGeneration/GrassDeform/:
  NS_GrassFootstepPuff     one-shot sprite puff: 8 soft dust sprites, lifetime <=0.75 seconds,
                           self-terminating (the C++ component relies on the system finishing so
                           its puff budget is returned).
  M_GrassFootstepDust      explicitly bound, texture-independent soft coverage and particle tint.
  M_GrassTrampleDecal      deferred decal that darkens the ground where a foot landed. One scalar
                           parameter, "Fade" (1 = fresh, 0 = gone), animated per decal instance by
                           UGrassFootstepFeedbackComponent.
  DA_GrassFootstepFeedback UGrassFootstepFeedbackConfig instance wired to the two assets above and
                           seeded with the grass-ish surface whitelist.

Design notes:
  - It does NOT touch the DynamicMesh hill ground material family
    (Docs/WorldGeneration/ground-material-layered-20260918.md). A deferred decal is composited over
    whatever the ground material draws, so the darkening is achieved without editing the layered
    family, its Wetness contract or its parallax. That is the whole reason the trail is a decal and
    not a material feature.
  - M_GrassTrampleDecal deliberately uses only built-in nodes: it must not depend on a texture that
    the M1 grass library or the ground family could rename. The look is driven by a radial falloff
    and a soft noise break-up authored inline, so the asset stands alone.
  - The puff is CPU-sim with 8 particles per activation and finite lifetime. The C++ side caps
    concurrent systems at PuffMaxActive; this is not a global live-particle counter.

Headless notes (the API shapes this script depends on, all verified against the 5.8 engine source):
  * UMaterial has no 'description' property (Material.h declares none; only UMaterialFunction does,
    MaterialFunction.h:57), so the decal-material version tag rides on asset metadata under
    VERSION_TAG_KEY instead. This is the bug that killed the first run at
    set_editor_property('description', ...) with "Failed to find property 'description'".
  * MaterialEditingLibrary.create_material_expression() is typed to UMaterial only
    (MaterialEditingLibrary.h / .cpp:634). This script creates no material *function*, so every
    graph it authors is a UMaterial and the plain entry point is correct here; new_expression()
    below still routes a function graph through create_material_expression_in_function() so the
    helper stays correct if a function node is ever added.
  * A TextureSample node's UV input pin is addressed as 'UVs', not 'UV' or 'Coordinates'.
  * CustomMaterialOutputType members are upper-cased in Python: CMOT_FLOAT1 .. CMOT_FLOAT4. A bare
    CMOT_FLOAT does not exist.
  * Niagara authoring goes through the UNiagaraToolset_System endpoints (AddEmitter / AddModule /
    RemoveModule / set_*_data). Every one of those calls reports failure through
    UKismetSystemLibrary::RaiseScriptError, i.e. a Python RuntimeError, and every one of them lives
    in NiagaraToolsets -- an *Experimental* plugin outside the project's control. The puff author
    now owns the material and all required particle values, and requires Niagara compilation
    before saving. Failures remain visible in REPORT['manual']; they are not treated as a
    successfully authored effect.

Plan: Docs/WorldGeneration/grass-interaction-gpu-20260925.md section 5 (and section 7 for budgets).
Consumers: Source/FPSGAME/WorldGeneration/GrassDeform/GrassFootstepFeedbackComponent.{h,cpp}
"""
import json
import traceback
from datetime import datetime

import unreal as u

DEST = '/Game/WorldGeneration/GrassDeform'

EAL = u.EditorAssetLibrary
MEL = u.MaterialEditingLibrary

# ---------------------------------------------------------------------------------------------
# Version tags. Same discipline as setup_assets_m1.py: an asset whose tag does not carry the current
# version is rebuilt from scratch, which is what makes a re-run converge after the contract
# (parameter names, particle budget, decal blend) changes instead of keeping a stale graph.
#
# Where each tag lives: asset metadata, for ALL THREE assets.
#   * M_GrassTrampleDecal      -> UMaterial has no description (M1's finding; Material.h declares
#                                 none -- only UMaterialFunction does, MaterialFunction.h:57).
#   * NS_GrassFootstepPuff     -> UNiagaraSystem has no description either (measured headless
#                                 2026-09-26: "NiagaraSystem: Failed to find property 'description'").
#                                 Same bug class, same fix.
#   * DA_GrassFootstepFeedback -> UGrassFootstepFeedbackConfig is a plain UDataAsset with no version
#                                 UPROPERTY.
# The asset registry tag is serialised with the asset, so it survives save/reload and is what makes
# the rebuild-on-contract-change path converge.
# ---------------------------------------------------------------------------------------------

PUFF_VERSION_TAG = 'puff-v2-soft-dust-20260926'
DECAL_VERSION_TAG = 'decal-v2-substrate-coverage-20260926'
CONFIG_VERSION_TAG = 'cfg-v1'

# Asset-registry metadata key carrying a version tag for assets that expose no description field.
# Must match setup_assets_m1.py so the two scripts read/write the same tag.
VERSION_TAG_KEY = 'GrassDeformVersion'

# Decal material scalar parameter. Must match GrassFootstepFeedbackComponent.cpp
# (GrassFootstepAssets::DecalFadeParameter).
DECAL_FADE_PARAMETER = 'Fade'

# Existing PuffMaxActive configuration ceiling (concurrent systems, not individual particles).
PUFF_MAX_PARTICLES = 64

# Puff lifetime, seconds. Kept below GrassFootstepFeedbackComponent's PuffFallbackLifeSeconds (2.5s),
# which is the component-side backstop if this system ever fails to report that it finished.
PUFF_LIFETIME_SECONDS = 0.75

# Particle count per footstep. One step is a small scuff, not a burst; the concurrency cap in C++
# (PuffMaxActive) bounds the total, this bounds each individual step.
PUFF_SPAWN_COUNT = 8

# Input pin name of a TextureSample node's UV slot. The graph editor *labels* this pin "UV" and the
# engine's name for the input is "Coordinates", but ConnectMaterialExpressions() matches the
# *shortened* pin name, which is 'UVs' (MaterialGraphNode.cpp:602-605). 'UV' and 'Coordinates' both
# fail to resolve. Same constant as setup_assets_m1.py.
TEX_COORD_INPUT = 'UVs'

REPORT = {'created': [], 'patched': [], 'skipped': [], 'manual': [], 'errors': []}

# Set only by main() once every asset step has run to completion. The RESULT line is printed when
# (and only when) this is true, so an all-empty REPORT can never masquerade as a success: a run that
# dies early prints a GRASS_DEFORM_M3_ABORTED line instead of a RESULT block.
_COMPLETED = False


def log(message):
    print('[GrassDeform M3] ' + str(message), flush=True)


def note_manual(message, error=None):
    """Record a non-fatal follow-up for the user, with the exception text when there is one."""
    text = str(message)
    if error is not None:
        text = '%s (%s: %s)' % (text, type(error).__name__, error)
    REPORT['manual'].append(text)
    log('MANUAL: ' + text)


def ensure_directory(path):
    if not EAL.does_directory_exist(path):
        EAL.make_directory(path)
        log('created directory ' + path)


def load_optional(path):
    if not EAL.does_asset_exist(path):
        return None
    obj = EAL.load_asset(path)
    if obj is None:
        raise RuntimeError('Asset exists but could not be loaded: ' + path)
    return obj


def save(asset, key, bucket='created'):
    if not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    if key not in REPORT[bucket]:
        REPORT[bucket].append(key)
    log('saved ' + asset.get_path_name())
    return asset


def create_asset(name, asset_class, factory):
    asset_tools = u.AssetToolsHelpers.get_asset_tools()
    asset = asset_tools.create_asset(name, DEST, asset_class, factory)
    if asset is None:
        raise RuntimeError('Could not create ' + name)
    log('created asset ' + name)
    return asset


def connect(source, source_output, target, target_input):
    if not MEL.connect_material_expressions(source, source_output, target, target_input):
        raise RuntimeError('Could not connect %s.%s -> %s.%s'
                           % (source.get_name(), source_output, target.get_name(), target_input))


def connect_property(source, source_output, prop):
    if not MEL.connect_material_property(source, source_output, prop):
        raise RuntimeError('Could not connect %s to %s' % (source.get_name(), prop))


def new_expression(graph, expression_class):
    """Create one expression node in `graph`, which may be a UMaterial or a UMaterialFunction.

    MaterialEditingLibrary.create_material_expression() is typed to UMaterial only; a material
    *function* graph must go through create_material_expression_in_function(), a separate engine
    entry point (MaterialEditingLibrary.cpp:634 vs .cpp:676). Passing a UMaterialFunction to the
    UMaterial overload raises a binder TypeError. M3 authors no function, but routing here keeps the
    helper correct for either graph.
    """
    if isinstance(graph, u.MaterialFunction):
        expr = MEL.create_material_expression_in_function(graph, expression_class)
    else:
        expr = MEL.create_material_expression(graph, expression_class)
    if expr is None:
        raise RuntimeError('Could not create %s in %s'
                           % (getattr(expression_class, '__name__', expression_class),
                              graph.get_name()))
    return expr


def add_custom(material, desc, code, output_type, pin_names):
    """Author a Custom HLSL node. Input pins are declared in `pin_names` order.

    `output_type` is the *Python* spelling of ECustomMaterialOutputType: CMOT_FLOAT1 / CMOT_FLOAT2 /
    CMOT_FLOAT3 / CMOT_FLOAT4. The binding upper-cases every enum member, so the C++ spelling
    (CMOT_Float1 .. CMOT_Float4) does not resolve from Python, and a bare CMOT_FLOAT does not exist.
    A scalar output is CMOT_FLOAT1.
    """
    expr = new_expression(material, u.MaterialExpressionCustom)
    expr.set_editor_property('desc', desc)
    expr.set_editor_property('code', code)
    expr.set_editor_property('output_type', output_type)
    pins = []
    for name in pin_names:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    expr.set_editor_property('inputs', pins)
    return expr


def scalar_param(material, name, default):
    expr = new_expression(material, u.MaterialExpressionScalarParameter)
    expr.set_editor_property('parameter_name', name)
    expr.set_editor_property('default_value', default)
    return expr


def version_tag(asset):
    """Read the version tag stored in asset metadata (see VERSION_TAG_KEY)."""
    try:
        return str(EAL.get_metadata_tag(asset, VERSION_TAG_KEY))
    except Exception:
        return ''


def set_version_tag(asset, tag):
    """Stamp a version tag into asset metadata.

    Used for every asset here that has no description field: UMaterial (M1's finding) and
    UGrassFootstepFeedbackConfig, which is a plain UDataAsset with no version UPROPERTY. The tag is
    serialised with the asset, so it survives a save/reload and the rebuild-on-change path converges.
    """
    return EAL.set_metadata_tag(asset, VERSION_TAG_KEY, tag)


# ---------------------------------------------------------------------------------------------
# M_GrassTrampleDecal
#
# Deferred decal: the renderer projects this along the decal component's local X axis onto whatever
# the ground draws, so it composites over the DynamicMesh hill terrain without the layered ground
# family being modified at all (plan section 5; the family's own doc forbids restructuring it).
#
# Opacity is a radial falloff broken up by a cheap 2D value hash, so the footprint does not read as
# a perfect circle, multiplied by the "Fade" scalar the component animates per decal instance.
# Emission is zero and the blend mode is translucent with a near-black base colour: a trampled
# footprint is a *darkening*, not a new surface.
# ---------------------------------------------------------------------------------------------

DECAL_CODE = '''
// UV is the decal's own 0..1 projection space. Radial mask with a squared shoulder so the footprint
// is soft at the rim instead of ending on a hard circle edge.
float2 Centered = UV - 0.5;
float Distance = length(Centered) * 2.0;
float Radial = 1.0 - saturate(Distance);
Radial = Radial * Radial * (3.0 - 2.0 * Radial);

// Cheap value noise: a hash on a coarse grid, enough to break the circle up into something that
// reads as disturbed grass rather than a stamp. Kept to a handful of ALU because this runs on every
// decal pixel in the pool.
float2 Grid = Centered * 6.0;
float2 Cell = floor(Grid);
float2 Frac = frac(Grid);
Frac = Frac * Frac * (3.0 - 2.0 * Frac);
float2 Hash = float2(dot(Cell, float2(127.1, 311.7)), dot(Cell, float2(269.5, 183.3)));
Hash = frac(sin(Hash) * 43758.5453);
float Noise = lerp(lerp(Hash.x, Hash.y, Frac.x), lerp(Hash.y, Hash.x, Frac.x), Frac.y);

// The rim of the footprint stays a little stronger than the middle, which is what a sole actually
// leaves behind; Noise carves irregular holes so overlapping steps do not stack into a blob.
float Density = Radial * lerp(0.55, 1.0, Noise);

return saturate(Density * Fade);
'''


def build_decal_material():
    path = DEST + '/M_GrassTrampleDecal'
    if path in {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserving unsaved changes to ' + path)
    existing = load_optional(path)
    if existing is not None and DECAL_VERSION_TAG in version_tag(existing):
        MEL.recompile_material(existing)
        REPORT['skipped'].append('M_GrassTrampleDecal (exists, ' + DECAL_VERSION_TAG + ')')
        return existing

    if existing is not None:
        log('M_GrassTrampleDecal exists but is not ' + DECAL_VERSION_TAG + '; rebuilding its graph')
        # Keep disconnected old nodes: a running editor can retain rooted runtime references.
        # Replace the output graph without marking those retained expressions as garbage.
        material = existing
        REPORT['patched'].append('M_GrassTrampleDecal rebuilt for ' + DECAL_VERSION_TAG)
    else:
        material = create_asset('M_GrassTrampleDecal', u.Material, u.MaterialFactoryNew())

    # There is deliberately NO set_editor_property('description', ...) here: UMaterial has no such
    # property and the call raises "Failed to find property 'description'". The tag rides on asset
    # metadata instead (set_version_tag above).

    # Both the domain and Substrate coverage are required. Surface-domain MIDs trigger the
    # runtime "decal material must use Deferred Decal domain" warning and render black cards.
    material.set_editor_property('material_domain', u.MaterialDomain.MD_DEFERRED_DECAL)
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    material.set_editor_property('two_sided', False)

    uv = new_expression(material, u.MaterialExpressionTextureCoordinate)
    uv.set_editor_property('coordinate_index', 0)

    body = add_custom(material, 'GrassTrampleDecal', DECAL_CODE,
                      u.CustomMaterialOutputType.CMOT_FLOAT1, ['UV', 'Fade'])
    connect(uv, '', body, 'UV')
    # The one parameter the runtime animates: 1 for a fresh footprint, 0 when the slot retires.
    # Default 0 so a decal placed without a MID (fallback path) is invisible rather than a solid
    # black disc on the terrain.
    connect(scalar_param(material, DECAL_FADE_PARAMETER, 0.0), '', body, 'Fade')
    connect_property(body, '', u.MaterialProperty.MP_OPACITY)

    # Constant near-black base colour: trampled grass is darker, not a different hue.
    dark = new_expression(material, u.MaterialExpressionConstant3Vector)
    dark.set_editor_property('constant', u.LinearColor(0.035, 0.030, 0.022, 1.0))
    connect_property(dark, '', u.MaterialProperty.MP_BASE_COLOR)

    slab = new_expression(material, u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    connect(dark, '', slab, 'BaseColor')
    connect(body, '', slab, 'Opacity')
    rough = new_expression(material, u.MaterialExpressionConstant)
    rough.set_editor_property('r', 1.0)
    zero = new_expression(material, u.MaterialExpressionConstant)
    zero.set_editor_property('r', 0.0)
    connect(rough, '', slab, 'Roughness')
    connect(zero, '', slab, 'Specular')
    connect(zero, '', slab, 'Metallic')
    decal = new_expression(material, u.MaterialExpressionSubstrateConvertToDecal)
    connect(slab, '', decal, str(MEL.get_material_expression_input_names(decal)[0]))
    # Coverage defaults to 1. Connecting legacy Opacity alone leaves the whole projector visible.
    connect(body, '', decal, 'Coverage')
    connect_property(decal, '', u.MaterialProperty.MP_FRONT_MATERIAL)
    set_version_tag(material, DECAL_VERSION_TAG)
    MEL.recompile_material(material)
    save(material, 'M_GrassTrampleDecal')
    return material


# ---------------------------------------------------------------------------------------------
# NS_GrassFootstepPuff
# The standalone author owns its renderer material, particle values and finite lifetime.
# Do not reuse NE_Heat defaults: the old stripped template produced black footstep cards.
# Keep this entry point so future M3 setup runs use the repaired production asset.


def build_puff_system():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(u.Paths.project_dir()) / 'Tools/GrassDeform'))
    from author_footstep_puff import build
    try:
        system = build()
        REPORT['patched'].append('NS_GrassFootstepPuff: soft dust material, 8 particles, lifetime <= 0.75s, Self/Once')
        return system
    except Exception as error:
        traceback.print_exc()
        REPORT['errors'].append('NS_GrassFootstepPuff authoring failed: %s' % error)
        note_manual('Footstep puff repair incomplete. Resolve the error and rerun '
                    'Tools/GrassDeform/author_footstep_puff.py; no incomplete puff was saved.', error)
        return None


# ---------------------------------------------------------------------------------------------
# DA_GrassFootstepFeedback
#
# The whitelist is the interesting part. UFPSFootstepAudioComponent plays ground steps through
# AutoFootstep with SurfaceType_Default (it classifies the bank by name and passes Default to the
# plugin - see Movement/FPSFootstepAudioComponent.cpp), while the animation notify path passes the
# hit's real physical surface. So a whitelist containing only SurfaceType_Grass would never fire in
# the actual game. This seeds BOTH: Default plus every surface type whose project name reads as
# grass / dirt / soil / gravel, and leaves the final narrowing to the user in the editor.
# ---------------------------------------------------------------------------------------------

# EPhysicalSurface is a plain (unnamespaced) UENUM -- ChaosEngineInterface.h:19-22 declares
# `UENUM(BlueprintType) enum EPhysicalSurface : int` at global scope. The Python binder exposes a
# global enum under its bare name with member names upper-cased, so the attribute is
# unreal.PhysicalSurface and the member is SURFACE_TYPE_DEFAULT. There is no unreal.EPhysicalSurface
# and no unreal.PhysicalSurface.SurfaceType_Default -- both spellings raise AttributeError (verified
# headless on this build). This is the same upper-casing rule as CustomMaterialOutputType above.
SURFACE_ENUM = u.PhysicalSurface
SURFACE_TYPE_DEFAULT = SURFACE_ENUM.SURFACE_TYPE_DEFAULT

# Project surface names that count as "the player walked on soft ground".
GRASS_SURFACE_NAME_HINTS = ('grass', 'dirt', 'soil', 'mud', 'gravel', 'sand')


def build_config(puff, decal):
    path = DEST + '/DA_GrassFootstepFeedback'
    config = load_optional(path)
    if config is None:
        # UDataAssetFactory defaults to the plain UDataAsset class, so the concrete class has to be
        # stated explicitly or the asset would not have the whitelist / asset-reference properties.
        factory = u.DataAssetFactory()
        factory.set_editor_property('data_asset_class', u.GrassFootstepFeedbackConfig)
        config = create_asset('DA_GrassFootstepFeedback', u.GrassFootstepFeedbackConfig, factory)
        set_version_tag(config, CONFIG_VERSION_TAG)
    else:
        REPORT['skipped'].append('DA_GrassFootstepFeedback (exists; re-wiring the asset refs)')
        set_version_tag(config, CONFIG_VERSION_TAG)

    # Wire the two assets. Always re-pointed: they are the whole reason this script and the class
    # exist together, and a stale path after a rename would silently disable the trail. The C++
    # properties are TSoftObjectPtr, and the Python binding accepts the UObject directly.
    if puff is not None:
        config.set_editor_property('puff_system', puff)
    else:
        note_manual('DA_GrassFootstepFeedback.PuffSystem was left EMPTY because '
                    'NS_GrassFootstepPuff could not be authored (see the Niagara manual entry). '
                    'The component then falls back to decal + stamp only: the footstep trail still '
                    'works, the particle puff does not.')

    if decal is not None:
        config.set_editor_property('decal_material', decal)
    else:
        note_manual('DA_GrassFootstepFeedback.DecalMaterial was left EMPTY because '
                    'M_GrassTrampleDecal could not be created; point it at the decal material '
                    'by hand or re-run this script.')

    # Seed the whitelist only when it is empty, so a user who narrowed it is never overridden by a
    # re-run of this script.
    existing_surfaces = config.get_editor_property('surfaces')
    if len(existing_surfaces) == 0:
        surfaces = set()
        # SurfaceType_Default is what the running game actually reports (see the note above), so it
        # is always seeded; without it the feature would be inert in the real game loop.
        surfaces.add(SURFACE_TYPE_DEFAULT)
        hinted = 0
        try:
            # UPhysicsSettings::PhysicalSurfaces is the same list UFPSFootstepAudioComponent reads
            # to name its own banks, so the two classifications stay consistent by construction.
            # NOTE: this list is EMPTY in the current project (measured headless 2026-09-26), so the
            # name-hint loop below adds nothing today and the whitelist is {Default}. That is not a
            # failure: Default alone is sufficient for the feature to fire, because the game's own
            # footstep path passes SurfaceType_Default. The loop is kept so that naming surfaces in
            # Project Settings > Physics later is picked up automatically on a re-run -- but only if
            # the whitelist is still empty, which is why the manual note below matters when it is
            # not. Do not narrow the whitelist to nothing: an empty whitelist disables the feature.
            settings = u.get_default_object(u.PhysicsSettings)
            for entry in settings.get_editor_property('physical_surfaces'):
                label = str(entry.get_editor_property('name')).lower()
                if any(hint in label for hint in GRASS_SURFACE_NAME_HINTS):
                    surfaces.add(entry.get_editor_property('type'))
                    hinted += 1
                    log('  + whitelisted surface %s' % label)
        except Exception as error:
            log('could not enumerate physical surfaces (%s); seeding Default only' % error)
        config.set_editor_property('surfaces', surfaces)
        REPORT['patched'].append('DA_GrassFootstepFeedback surface whitelist (%d entries)'
                                 % len(surfaces))
        if hinted == 0:
            note_manual(
                'DA_GrassFootstepFeedback surface whitelist was seeded with SurfaceType_Default '
                'only, because Project Settings > Physics > Physical Surface names are currently '
                'empty, so no surface name reads as grass/dirt/soil. The feature still works: the '
                'game reports SurfaceType_Default for ground steps. If you later name your surface '
                'slots (e.g. "Grass"), either add those types to the whitelist by hand or clear the '
                'Surfaces array and re-run this script, which will pick the names up.')
    else:
        log('surface whitelist already populated (%d entries); leaving it alone'
            % len(existing_surfaces))

    # Runtime budget. Seeded only when the property is still unset, so a user retune survives a
    # re-run. DecalPoolSize = 12 is the plan section 5 pool size (and matches the class default).
    if config.get_editor_property('decal_pool_size') <= 0:
        config.set_editor_property('decal_pool_size', 12)
    if config.get_editor_property('decal_life_seconds') <= 0.0:
        config.set_editor_property('decal_life_seconds', 6.0)
    if config.get_editor_property('puff_max_active') <= 0:
        config.set_editor_property('puff_max_active', PUFF_MAX_PARTICLES)

    save(config, 'DA_GrassFootstepFeedback')
    return config


# ---------------------------------------------------------------------------------------------

def main():
    global _COMPLETED

    log('start ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    ensure_directory(DEST)

    # Decal first: it is the asset the C++ component needs to show anything at all, so it is
    # authored before the version-sensitive Niagara step.
    decal = build_decal_material()
    puff = build_puff_system()
    config = build_config(puff, decal)

    if config is not None and len(config.get_editor_property('surfaces')) == 0:
        note_manual(
            'DA_GrassFootstepFeedback has an EMPTY surface whitelist, so the component will stay '
            'inert. Add the physical surfaces that should trigger the grass feedback (and note that '
            'the running game reports SurfaceType_Default for ground steps, so that entry is '
            'normally required).')

    if config is not None:
        # Report the wiring that was actually written, so a reader does not have to trust that the
        # property writes above stuck.
        log('DA_GrassFootstepFeedback: surfaces=%s puff=%s decal=%s pool=%s'
            % (len(config.get_editor_property('surfaces')),
               config.get_editor_property('puff_system'),
               config.get_editor_property('decal_material'),
               config.get_editor_property('decal_pool_size')))

    log('done. created=%s patched=%s skipped=%d manual=%d errors=%d'
        % (REPORT['created'], REPORT['patched'], len(REPORT['skipped']), len(REPORT['manual']),
           len(REPORT['errors'])))

    # main() reached its end: the RESULT block below is now a genuine completion report.
    _COMPLETED = True
    print('GRASS_DEFORM_M3_RESULT ' + repr(REPORT), flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        # Only a real, complete run prints the RESULT line. A crash prints an ABORTED line with the
        # partial report instead, so an empty-list RESULT can never read as success.
        if _COMPLETED:
            print('GRASS_DEFORM_M3_RESULT ' + repr(REPORT), flush=True)
        else:
            print('GRASS_DEFORM_M3_ABORTED ' + repr(REPORT), flush=True)
        raise SystemExit(1)
