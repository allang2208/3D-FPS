"""Retire the former legendary blades during factory and historical model reimports."""
import runpy
from pathlib import Path

def extend(catalog):
    catalog['slots']['blade_1'].pop('chixiao', None)
    catalog.pop('chixiao_blade_revision', None)
    wind = Path(__file__).resolve().parents[1] / 'ZhufengBladeV1/catalog_extension.py'
    return runpy.run_path(str(wind))['extend'](catalog)
