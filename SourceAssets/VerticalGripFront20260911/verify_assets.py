from pathlib import Path
ROOT=Path(__file__).parent
source=(ROOT/'ReferenceWorkflow/verify_assets.py').read_text().replace('O=Path(__file__).parent','O=ROOT').replace("[('m4','canted')]+[('akm',v) for v in ['canted','vertical','prism','angled']]","[(w,'vertical') for w in ['m4','akm']]").replace('"Canted" if weapon=="m4" else variant','variant.title() if weapon=="m4" else variant').replace("'/Game/Weapons/M4CantedErgonomic' if weapon=='m4' else P+'/GripErgonomic/'+variant","'/Game/Weapons/M4VerticalGripOpposed/'+variant.title() if weapon=='m4' else P+'/GripOpposed/'+variant").replace("'/Game/Weapons/M4CantedThumbClose/'+name","'/Game/Weapons/M4VerticalGripErgonomic/'+variant.title()+'/'+name").replace('GRIP_MIGRATION_READBACK_PASS','FRONT_READBACK_PASS')
# This is a complete validation of the current vertical scope, not an incremental merge.
source=source.replace("report=json.loads((O/'asset_validation.json').read_text()) if (O/'asset_validation.json').exists() else {}", "report={}")
exec(compile(source,str(ROOT/'verify_generated.py'),'exec'))
