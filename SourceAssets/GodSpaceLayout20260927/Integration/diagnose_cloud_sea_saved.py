from pathlib import Path
file=Path(__file__).parent/'diagnose_cloud_sea_runtime.py'
exec(compile(file.read_text(encoding='utf8'),str(file),'exec'),{'__file__':str(file),'LOAD_SAVED_HUB':True})
