from pathlib import Path
O=Path(__file__).resolve().parent
code=(O/'inspect_grip.py').read_text()
code=code.replace("rows={'current':base,'donor':native}", "rows={'fitted':{n:Matrix(m) for n,m in json.loads((OUT/'grip_pose.json').read_text()).items()}}")
code=code.replace("'grip_candidates.json'", "'grip_fitted_preview.json'")
exec(compile(code,'grip_preview','exec'))
