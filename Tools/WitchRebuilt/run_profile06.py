import importlib.util,sys
from pathlib import Path
name='witch_cloth_profile06'
existing=sys.modules.get(name)
if existing and getattr(getattr(existing,'capture',None),'handle',None):raise RuntimeError('Witch capture already running')
spec=importlib.util.spec_from_file_location(name,str(Path(__file__).parent/'profile_cloth06.py'))
module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
module.start(globals().get('WITCH_PROFILE_LABEL','before'))
