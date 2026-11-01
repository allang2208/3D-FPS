from pathlib import Path
code=(Path(__file__).parent/'review.py').read_text().split('# Reconstruct the registered LeaderPose')[0]
code=code.replace("if family=='base':","if False:")
exec(compile(code,'targeted_joint_metrics','exec'))
