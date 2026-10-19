"""Retain Chixiao's fitted blade through all Zhanmadao reauthoring entrypoints."""
import json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
def extend(catalog):
    file=P/'import_receipt.json'
    if not file.exists():return catalog
    receipt=json.loads(file.read_text(encoding='utf-8'))
    if not receipt.get('assets_saved'):return catalog
    ex=json.loads((P/'exports.json').read_text(encoding='utf-8'))
    part={k:ex[k] for k in ['trace_base_cm','trace_tip_cm','rune_dimensions_cm']}
    part.update(mesh=receipt['mesh'],materials=receipt['materials'],location_cm=[0,0,0],interface=catalog['interface'],
        appearance='玄钢宽刃 · 银白开锋 · 暗红嵌脊 · 刀根金云纹',rune_layout_revision='ChixiaoContourV1',
        heavy_attack='chixiao_double_slash')
    catalog['slots']['blade_1']['chixiao']=part;catalog['chixiao_blade_revision']='ChixiaoBladeV1'
    zhufeng=P.parent/'ZhufengBladeV1/catalog_extension.py'
    if zhufeng.exists():catalog=runpy.run_path(str(zhufeng))['extend'](catalog)
    return catalog
