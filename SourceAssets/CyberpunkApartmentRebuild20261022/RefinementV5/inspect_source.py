"""Requested source geometry checks and pocket fit calculation; no rendering."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=(ROOT.parent/'RefinementV4/audit_source_models.py').read_text('utf8')
source=source.replace('CyberpunkApartment_Rebuild.blend','ApartmentV5_Source.blend').replace('changed_in_v4','changed_in_v5')
exec(compile(source,str(ROOT/'inspect_models.py'),'exec'),{'__file__':str(ROOT/'inspect_models.py'),'__name__':'__main__'})
