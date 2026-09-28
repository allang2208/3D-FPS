"""Compile/save only the laser hit-spot material; no editor UI or game test."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name('create_laser_materials.py')), init_globals={
    'LASER_KINDS': ['Dot'],
    'LASER_RECEIPT_FOLDER': 'Saved/LaserDotNoHistory20260927',
})
