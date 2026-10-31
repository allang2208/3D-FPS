from pathlib import Path
import runpy,unreal as u,json
R=Path(__file__).resolve().parent
u.EditorLoadingAndSavingUtils.new_blank_map(False)
progress=R/'production_progress.json';start=json.loads(progress.read_text(encoding='utf8')).get('next_batch',0) if progress.exists() else 0
for i in range(start,24):
    print('URBAN_PRODUCTION_BEGIN',i,flush=True)
    runpy.run_path(str(R/f'batch_{i:02}.py'),run_name='__main__')
    progress.write_text(json.dumps(dict(next_batch=i+1,stage='running' if i<23 else 'assets_saved')),encoding='utf8')
print('URBAN_PRODUCTION_ALL_SAVED',flush=True)
