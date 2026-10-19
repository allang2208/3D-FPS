"""Apply saved Beiwei blade bindings after the earlier contour materials."""
import json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
def extend(catalog):
    file=P/'import_receipt.json'
    if not file.exists():return catalog
    data=json.loads(file.read_text(encoding='utf-8'))
    if not data.get('assets_saved'):return catalog
    for choice,materials in data['bindings'].items():
        part=catalog.get('slots',{}).get('blade_1',{}).get(choice)
        if part is not None:part['materials']=materials
    catalog['beiwei_rune_revision']='BeiweiRuneV1'
    chixiao=P.parent/'ChixiaoBladeV1/catalog_extension.py'
    if chixiao.exists():catalog=runpy.run_path(str(chixiao))['extend'](catalog)
    return catalog
