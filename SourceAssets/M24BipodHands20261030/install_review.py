from pathlib import Path
code=(Path(__file__).parent.parent/'M24LeftElbowReview20261028/install.py').read_text()
exec(compile(code.replace("(O/'install_receipt.json')","(O/'elbow_install_receipt.json')").replace('overwrite_existing_target=False','overwrite_existing_target=True'),'install_bipod_elbow','exec'))
import runpy
runpy.run_path(str(O/'install.py'),init_globals={'REVIEW_REVISION':True})
