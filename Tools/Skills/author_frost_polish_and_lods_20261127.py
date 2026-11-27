"""Headless UE5 authoring script for Plan A Polish & Performance (2026-11-27).

Deliverables:
  1. /Game/Skills/IceSpike/FrostV2/NS_FrostCrystalsV2:
     Clean non-CDO-locked duplicate of NS_FrostCrystals with every SpriteRenderer
     switched from broken legacy M_FrostCrystalSoft (UE 5.8 DepthFade pin mismatch
     causing opaque grey squares) to photorealistic feathered
     /Game/Skills/AbsoluteZero/M_AbsoluteZeroIceDust. Legacy NS_FrostCrystals stays
     untouched for M07MagicAttack CDO compatibility.
  2. Auto-generated LOD1 (50% tris, screen 0.42) & LOD2 (22% tris, screen 0.16)
     for all 8 sculpted glacial StaticMeshes:
     - /Game/Skills/AbsoluteZero/SM_AZ_GlacierSpire_01..03 & SM_AZ_IceFangCluster
     - /Game/Skills/IceWall/FabIceV3/SM_IceBlock_01..04
  3. Automatic pre-edit backups + SHA-256 receipt in
     F:/FPSGAMEData/ArtProduction/AbsoluteZero/PolishAndNetFix-20261127/.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
PROD = Path('F:/FPSGAMEData/ArtProduction/AbsoluteZero/PolishAndNetFix-20261127')
BEFORE = PROD / 'Before'
BEFORE.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, emitters, ref, setdata

EAL = u.EditorAssetLibrary
SM_SUB = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)

DUST_MAT_PATH = '/Game/Skills/AbsoluteZero/M_AbsoluteZeroIceDust'
SRC_CRYSTALS = '/Game/Skills/IceSpike/FrostV2/NS_FrostCrystals'
DST_CRYSTALS = '/Game/Skills/IceSpike/FrostV2/NS_FrostCrystalsV2'

LOD_MESHES = [
    '/Game/Skills/AbsoluteZero/SM_AZ_GlacierSpire_01',
    '/Game/Skills/AbsoluteZero/SM_AZ_GlacierSpire_02',
    '/Game/Skills/AbsoluteZero/SM_AZ_GlacierSpire_03',
    '/Game/Skills/AbsoluteZero/SM_AZ_IceFangCluster',
    '/Game/Skills/IceWall/FabIceV3/SM_IceBlock_01',
    '/Game/Skills/IceWall/FabIceV3/SM_IceBlock_02',
    '/Game/Skills/IceWall/FabIceV3/SM_IceBlock_03',
    '/Game/Skills/IceWall/FabIceV3/SM_IceBlock_04',
]


def disk_path(asset_path: str) -> Path:
    return ROOT / 'Content' / (asset_path.split('.')[0].removeprefix('/Game/') + '.uasset')


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def backup_if_needed(asset_paths):
    out = {}
    for ap in asset_paths:
        src = disk_path(ap)
        dst = BEFORE / (ap.split('/')[-1] + '.uasset')
        if src.is_file() and not dst.exists():
            shutil.copy2(src, dst)
        out[ap] = str(dst) if dst.is_file() else None
    return out


def author_frost_crystals_v2():
    dust_mat = u.load_asset(DUST_MAT_PATH)
    if not dust_mat:
        raise RuntimeError('Missing dust material: ' + DUST_MAT_PATH)
    system = u.load_asset(DST_CRYSTALS) if EAL.does_asset_exist(DST_CRYSTALS) else EAL.duplicate_asset(SRC_CRYSTALS, DST_CRYSTALS)
    if not system:
        raise RuntimeError('Failed loading/duplicating ' + DST_CRYSTALS)

    em_names = emitters(system)
    if not em_names:
        raise RuntimeError('NS_FrostCrystalsV2 has no emitters')

    updated = []
    for em in em_names:
        setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, em, renderer=0), {
            'Material': dust_mat.get_path_name(),
            'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
            'SubImageSize': {'X': 1, 'Y': 1},
            'bSubImageBlend': False,
            'Alignment': 'Unaligned',
            'FacingMode': 'FaceCamera',
            'SortMode': 'ViewDepth',
            'PivotInUVSpace': {'X': 0.5, 'Y': 0.5},
            'bCastShadows': False,
            'CutoutTexture': None,
            'bUseMaterialCutoutTexture': False,
            'MotionVectorSetting': 'Disable',
        })
        updated.append(em)

    if not u.RainAssetEditor.compile_rain(system):
        raise RuntimeError('Niagara compile failed for ' + DST_CRYSTALS)
    EAL.set_metadata_tag(system, 'FrostCrystalsV2.Revision', 'PolishAndNetFix_20261127')
    if not EAL.save_loaded_asset(system, False):
        raise RuntimeError('Failed saving ' + DST_CRYSTALS)
    print('FROST_CRYSTALS_V2_SAVED', system.get_path_name(), 'emitters=', updated, flush=True)
    return {'asset': DST_CRYSTALS, 'emitters': updated, 'material': dust_mat.get_path_name()}


def generate_mesh_lods():
    rows = []
    for ap in LOD_MESHES:
        mesh = u.load_asset(ap)
        if not mesh:
            raise RuntimeError('Missing static mesh: ' + ap)
        old_slots = list(mesh.get_editor_property('static_materials'))
        options = u.StaticMeshReductionOptions()
        options.auto_compute_lod_screen_size = False
        options.reduction_settings = [
            u.StaticMeshReductionSettings(percent_triangles=p, screen_size=s)
            for p, s in ((1.0, 1.0), (0.50, 0.42), (0.22, 0.16))
        ]
        mesh.set_editor_property('static_materials', old_slots)
        lod_count = SM_SUB.set_lods(mesh, options)
        if not EAL.save_loaded_asset(mesh, False):
            raise RuntimeError('Failed saving LOD mesh: ' + ap)
        actual_lods = SM_SUB.get_lod_count(mesh)
        tris = [mesh.get_num_triangles(i) for i in range(actual_lods)]
        print('MESH_LOD_SAVED', ap, 'lods=', actual_lods, 'tris=', tris, flush=True)
        rows.append({'asset': ap, 'lod_count': actual_lods, 'triangles_by_lod': tris, 'set_lods_ret': lod_count})
    return rows


def main():
    backups = backup_if_needed([DST_CRYSTALS] + LOD_MESHES)
    crystals_info = author_frost_crystals_v2()
    lod_rows = generate_mesh_lods()

    saved = {}
    for ap in [DST_CRYSTALS] + LOD_MESHES:
        dp = disk_path(ap)
        if not dp.is_file():
            raise RuntimeError('Missing saved asset on disk: ' + str(dp))
        saved[ap] = {
            'disk': str(dp),
            'bytes': dp.stat().st_size,
            'sha256': sha256(dp),
        }

    receipt = {
        'version': 'FrostPolishAndNetFix_20261127',
        'backups': backups,
        'frost_crystals_v2': crystals_info,
        'mesh_lods': lod_rows,
        'saved_assets': saved,
        'runtime_tested': False,
    }
    PROD.mkdir(parents=True, exist_ok=True)
    receipt_path = PROD / 'published.json'
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    print('POLISH_RECEIPT_SAVED', str(receipt_path), 'count=', len(saved), flush=True)


if __name__ == '__main__':
    main()
