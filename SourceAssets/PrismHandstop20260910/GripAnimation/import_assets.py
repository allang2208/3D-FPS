from pathlib import Path
O=Path(__file__).parent
source=(O/'ReferenceWorkflow/import_assets.py').read_text(encoding='utf-8')
source="""import unreal,json
from pathlib import Path
O=Path(__file__).parent;DEST='/Game/Weapons/M4PrismGrip'
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');assert mesh
report={}
"""+source[source.index('references={'):]
source=source.replace('A_M4_Foregrip_','A_M4_Prism_').replace('FOREGRIP_','PRISM_')
source=source.replace(" report[clip]=", " assert unchanged_error<.01 and contact_error<.01,(clip,unchanged_error,contact_error)\n report[clip]=")
exec(compile(source,str(O/'import_generated.py'),'exec'))
