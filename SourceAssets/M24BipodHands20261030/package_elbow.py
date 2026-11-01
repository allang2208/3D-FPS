from pathlib import Path
code=(Path(__file__).parent.parent/'M24LeftElbowReview20261028/package_correctives.py').read_text()
exec(compile(code.replace("O/'geometry.json'","O/'skin_geometry.json'"),'package_bipod_elbow','exec'))
