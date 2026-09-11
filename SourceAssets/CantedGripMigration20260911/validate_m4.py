from pathlib import Path
ROOT=Path(__file__).parent
source=(ROOT/'ReferenceWorkflow/validate_source.py').read_text().replace('O=Path(__file__).parent',"O=ROOT/'m4/canted'").replace('A_M4_Foregrip_','A_M4_Canted_')
exec(compile(source,str(ROOT/'validate_m4_generated.py'),'exec'))
