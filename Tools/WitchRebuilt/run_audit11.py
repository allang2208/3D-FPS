import importlib.util
import sys
from pathlib import Path
name = 'witch_audit11'
prior = sys.modules.get(name)
if prior and getattr(getattr(prior, 'capture', None), 'handle', None):
    raise RuntimeError('Witch audit already active')
spec = importlib.util.spec_from_file_location(name, str(Path(__file__).parent / 'profile_audit11.py'))
module = importlib.util.module_from_spec(spec)
sys.modules[name] = module
spec.loader.exec_module(module)
