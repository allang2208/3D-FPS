"""Keep saved native rune bindings through every Zhanmadao production entrypoint."""
import json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
def extend(catalog):
    receipt=P/'import_receipt.json'
    if not receipt.exists():return catalog
    data=json.loads(receipt.read_text(encoding='utf-8'))
    if not data.get('assets_saved'):return catalog
    for key,materials in data['bindings'].items():
        part=catalog.get('slots',{}).get('blade_1',{}).get(key)
        if part is None:continue
        part['materials']=materials
        part['rune_layout_revision']='ZhanmadaoBladeContourV1'
    catalog['rune_surface_revision']='ZhanmadaoNativeRuneSurfaceV1'
    beiwei=P.parent/'BeiweiRuneV1/catalog_extension.py'
    if beiwei.exists():catalog=runpy.run_path(str(beiwei))['extend'](catalog)
    return catalog
