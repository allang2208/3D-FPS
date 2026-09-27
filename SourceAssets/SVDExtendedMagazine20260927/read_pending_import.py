import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
prefixes=('/Game/Weapons/SVDDragunov20260922/ExtendedMagazine20260927','/Game/ColdSteelData/AttachmentIcons20260913/ue_svd_')
rows=[]
for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    path=p.get_path_name()
    if not path.startswith(prefixes):continue
    asset=u.load_asset(path)
    info={'asset':path}
    if asset:
        data=asset.get_editor_property('asset_import_data')
        info['sources']=list(data.extract_filenames()) if data else []
    rows.append(info)
(O/'pending_import.json').write_text(json.dumps(rows,indent=2))
print('SVD_EXTMAG_PENDING '+json.dumps(rows))
