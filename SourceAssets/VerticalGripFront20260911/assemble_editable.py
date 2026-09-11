from pathlib import Path
ROOT=Path(__file__).parent
source=(ROOT/'ReferenceWorkflow/assemble_editable.py').read_text().replace('O=Path(__file__).parent','O=ROOT').replace("[('m4','canted')]+[('akm',v) for v in ['canted','vertical','prism','angled']]","[(w,'vertical') for w in ['m4','akm']]").replace('"Canted" if weapon=="m4" else variant','variant.title() if weapon=="m4" else variant')
exec(compile(source,str(ROOT/'ReferenceWorkflow/assemble_editable.py'),'exec'))
