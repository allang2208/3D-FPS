from pathlib import Path
code=(Path(__file__).parent.parent/'M24IdleArm20261030/install.py').read_text()
code=code.replace('V9 left held-pose correction in two live profiles; contact-aware release and return','M24 normal and empty reload: decisive extraction and ordinary-reload gun anchor; both magazine profiles')
code=code.replace('M24_IDLE_ARM_SAVED','M24_RELOAD_CRISP_SAVED')
code=code.replace("receipt['complete']=True", "receipt['patch_sha256']=hashlib.sha256((O/'profile_patch.json').read_bytes()).hexdigest();receipt['complete']=True")
exec(compile(code,'save_M24_reload_profiles','exec'))
exec(compile((Path(__file__).parent.parent/'M24IdleArm20261030/read_saved.py').read_text(),'read_saved_reload_tracks','exec'))
