from pathlib import Path
code=(Path(__file__).parent.parent/'M24IdleArm20261030/install.py').read_text()
code=code.replace('V9 left held-pose correction in two live profiles; contact-aware release and return','Both held thumbs and inspect shoulder/elbow chains; native wrist/gun contacts retained')
code=code.replace('M24_IDLE_ARM_SAVED','M24_GRIP_OUTFIT_SAVED')
code=code.replace("receipt['complete']=True", "receipt['patch_sha256']=hashlib.sha256((O/'profile_patch.json').read_bytes()).hexdigest();receipt['complete']=True")
if (Path(__file__).parent/'profiles_after.json').exists():
    code=code.replace("expected=json.loads((O/'ue_before.json').read_text())['profiles']", "expected=json.loads((O/'profiles_after.json').read_text())")
exec(compile(code,'save_M24_profiles','exec'))
exec(compile((Path(__file__).parent/'read_saved.py').read_text(),'read_saved_M24_tracks','exec'))
