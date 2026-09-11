from pathlib import Path
ROOT=Path(__file__).parent
source=(ROOT/'ReferenceWorkflow/check_geometry.py').read_text().replace('O=Path(__file__).parent','O=ROOT').replace('"Canted" if weapon=="m4" else variant','variant.title() if weapon=="m4" else variant').replace("x.name.startswith('CG_')","x.name.startswith('VG_' if variant=='vertical' else 'PH_')")
exec(compile(source,str(ROOT/'ReferenceWorkflow/check_geometry.py'),'exec'))
