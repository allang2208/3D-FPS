"""Regrade the gate fork and quarry from the pre-road hillside (no old road underneath)."""
import shutil
import sys
from pathlib import Path
from generate_reference_hill import generate
from prepare_forest_reference import prepare as paint_gate
from prepare_quarry_road import prepare as grade_quarry

if __name__=='__main__':
    out, work = map(Path,sys.argv[1:])
    gate, base = work/'GateHill', work/'GateBase'
    generate(out.parent,gate,trail_variant=True)
    paint_gate(base,root=out.parent,hill=gate)
    for name in ('gate-road.csv','hill.json','reference.f32'):
        shutil.copyfile(base/name,out/name)
    grade_quarry(out,base)
