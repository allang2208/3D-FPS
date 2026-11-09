"""Clear the forward-seated factory scope during the initial cover reach."""
from pathlib import Path
import importlib.util

spec=importlib.util.spec_from_file_location('m249_repair04_clearance',Path(__file__).resolve().parents[1]/'Repair04/motion_clearance.py')
previous=importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
drape=previous.drape

def hand_route(target,t,empty):
    previous.hand_route(target,t,empty)
    # Leave the finger curl/orientation and cover contact untouched. Move the
    # wrist outward before the index/middle fingers cross the scope eyepiece.
    weight=previous.smooth(t,.42,.50)*(1.-previous.smooth(t,.60,.72))
    target[:,0,3]-=4.2*weight
