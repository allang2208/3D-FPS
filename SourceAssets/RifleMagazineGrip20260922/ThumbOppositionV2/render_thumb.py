"""Reuse the scoped source-pose display with this revision's thumb geometry."""
from pathlib import Path
O=Path(__file__).parent
code=(O.parent/'render_grasp.py').read_text()
code=code.replace("data=json.loads((O/'fit_input.json').read_text())", "data=json.loads((O.parent/'fit_input.json').read_text())")
code=code.replace("name='draft_fit' if '--draft' in sys.argv else 'grasp_fit'", "name='selected_grasp'")
exec(compile(code,str(O/'render_thumb.py'),'exec'))
