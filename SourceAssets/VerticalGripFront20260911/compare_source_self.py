from pathlib import Path
ROOT=Path(__file__).parent
source=(ROOT/'ReferenceWorkflow/compare_source_self.py').read_text().replace('O=Path(__file__).parent','O=ROOT').replace("[('m4','canted')]+[('akm',v) for v in ['canted','vertical','prism','angled']]","[(w,'vertical') for w in ['m4','akm']]")
exec(compile(source,str(ROOT/'self_generated.py'),'exec'))
