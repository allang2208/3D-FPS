"""Scoped 60 Hz right-hand stock clearance across release and regrip."""
from pathlib import Path
O=Path(__file__).resolve().parent
code=(O/'grip_surface.py').read_text()
samples=[('after',i/60) for i in list(range(1,9))+list(range(28,41))]
code=code.replace("[('before',.25),('after',.07),('after',.1),('after',.14),('after',.25),('after',.55)]",repr(samples))
code=code.replace("O/'grip_surface.json'","O/'transition_surface.json'")
exec(compile(code,'transition_surface','exec'))
