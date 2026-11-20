"""Write native and inventory EXFIL game meshes, then capture all saved wearable LODs."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("helmet_contour_save.py")),init_globals={
    "HELMET_REVISION":"ExfilReferenceR4","HELMET_MATERIAL_REVISION":"ExfilReferenceR4",
    "HELMET_RECORD_RENDER_STATS":True,"HELMET_LOD_SETTINGS":[(1.,1.),(.50,.18),(.22,.07)],
    "HELMET_WEAR_ONLY":globals().get("HELMET_WEAR_ONLY",False),"HELMET_WEAR_SUFFIX":"_JawFit"})
