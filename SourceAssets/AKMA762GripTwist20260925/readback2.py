"""Read back the 30 imported reload clips from the editor: which FBX each asset
now came from, its length, skeleton, compression and this round's metadata tag,
so the on-disk assets can be tied to the v2 export."""
import json
import unreal as u
from pathlib import Path

try:
    O = Path(__file__).parent
except NameError:  # executed inside the editor through the MCP python bridge
    O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKMA762GripTwist20260925')
P = O.parents[1]
SOURCES = json.loads((P / 'SourceAssets/RifleMagazineGrip20260922/IndexClearanceV4/sources.json')
                     .read_text(encoding='utf-8'))['animations']

rows = {}
problems = []
for job in SOURCES:
    asset = job['asset']
    anim = u.load_asset(asset)
    if not anim:
        problems.append((asset, 'missing'))
        continue
    data = anim.get_editor_property('asset_import_data')
    src = list(data.extract_filenames()) if data else []
    skel = anim.get_editor_property('skeleton')
    comp = anim.get_editor_property('bone_compression_settings')
    tag = u.EditorAssetLibrary.get_metadata_tag(anim, 'GripRefinement2')
    key = '/'.join((job['gun'], job['magazine'], job['family'], job['clip']))
    expect = str(O / 'v2' / job['gun'] / job['magazine'] / job['family'] /
                 (Path(asset).name + '.fbx'))
    row = {'asset': asset, 'import_sources': src, 'length_s': round(anim.get_play_length(), 4),
           'skeleton': skel.get_path_name() if skel else None,
           'compression': comp.get_path_name() if comp else None,
           'tag_grip_refinement2': tag,
           'expected_fbx': expect}
    rows[key] = row
    if not src or Path(src[0]).as_posix().lower() != Path(expect).as_posix().lower():
        problems.append((key, 'import source is not this round FBX: %s' % src))
    if not skel or 'M4_HK416_Skeleton' not in skel.get_path_name():
        problems.append((key, 'unexpected skeleton %s' % (skel.get_path_name() if skel else None)))
    if not comp or 'BC_M4Viewmodel' not in comp.get_path_name():
        problems.append((key, 'unexpected compression %s' % (comp.get_path_name() if comp else None)))
(O / 'readback2.json').write_text(json.dumps({'rows': rows, 'problems': problems}, indent=1), encoding='utf-8')
print('THUMB2_READBACK clips=%d problems=%d' % (len(rows), len(problems)), flush=True)
for k, v in list(rows.items())[:3]:
    print('   ', k, v['length_s'], 's', v['import_sources'][:1], 'tag=%s' % v['tag_grip_refinement2'], flush=True)
for p in problems:
    print('   PROBLEM', p[0], p[1], flush=True)
