"""Install the requested real-constellation figures using the existing authoring path."""
import importlib.util
from pathlib import Path

path=Path(__file__).with_name('integrate_white_celestial.py')
spec=importlib.util.spec_from_file_location('pavilion_white_celestial_authoring',path)
authoring=importlib.util.module_from_spec(spec)
spec.loader.exec_module(authoring)
authoring.integrate('C4')
