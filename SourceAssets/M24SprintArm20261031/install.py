from pathlib import Path
code=(Path(__file__).parent.parent/'M24IdleArm20261030/install.py').read_text()
code=code.replace('V9 left held-pose correction in two live profiles; contact-aware release and return','M24 sprint left elbow hinge and forearm twist; enter loop exit in both profiles; idle and other actions retained')
code=code.replace('M24_IDLE_ARM_SAVED','M24_SPRINT_ARM_SAVED')
code=code.replace("receipt['complete']=True", "receipt['patch_sha256']=hashlib.sha256((O/'profile_patch.json').read_bytes()).hexdigest();receipt['complete']=True")
exec(compile(code,'save_sprint_arm_profiles','exec'))
exec(compile((Path(__file__).parent.parent/'M24IdleArm20261030/read_saved.py').read_text(),'read_saved_sprint_tracks','exec'))
