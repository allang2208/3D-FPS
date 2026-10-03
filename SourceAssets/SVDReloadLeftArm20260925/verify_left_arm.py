"""Read back the ten saved SVD reload animations: source, duration, settings, tag."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
receipt = json.loads((O / 'import_receipt.json').read_text())
out = {}
for key, info in receipt.items():
    anim = u.load_asset(info['asset'])
    if not anim:
        out[key] = dict(ok=False, reason='missing')
        continue
    source = ''
    try:
        source = anim.get_editor_property('asset_import_data').get_first_filename()
    except Exception as exc:
        source = 'unreadable: %s' % exc
    curves = [c.get_editor_property('curve_name') if hasattr(c, 'get_editor_property') else str(c)
              for c in anim.get_editor_property('compressed_data').get_editor_property('compressed_curve_data_names')] \
        if False else []
    out[key] = dict(
        ok=True, asset=anim.get_path_name(), duration=anim.get_play_length(),
        source=source, source_matches=Path(source).resolve() == Path(info['source']).resolve(),
        metadata=str(u.EditorAssetLibrary.get_metadata_tag(anim, 'LeftArmCameraProtection')),
        enable_root_motion=anim.get_editor_property('enable_root_motion'),
        force_root_lock=anim.get_editor_property('force_root_lock'),
        bone_compression=str(anim.get_editor_property('bone_compression_settings').get_path_name()),
        import_error=info['saved_sha256'][:12])
    print('SVD_LEFT_ARM_VERIFY', key, out[key]['duration'], out[key]['source_matches'],
          out[key]['metadata'][:40], flush=True)
(O / 'verify_receipt.json').write_text(json.dumps(out, indent=2))
print('SVD_LEFT_ARM_VERIFY_COMPLETE', len(out), flush=True)
