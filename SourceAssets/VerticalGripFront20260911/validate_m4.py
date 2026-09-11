import sys
from pathlib import Path
ROOT=Path(__file__).parent;variant=sys.argv[sys.argv.index('--')+1]
source=(ROOT/'ReferenceWorkflow/validate_source.py').read_text().replace('O=Path(__file__).parent',"O=ROOT/'m4'/variant").replace('A_M4_Foregrip_','A_M4_'+variant.title()+'_')
exec(compile(source,str(ROOT/'ReferenceWorkflow/validate_source.py'),'exec'))
