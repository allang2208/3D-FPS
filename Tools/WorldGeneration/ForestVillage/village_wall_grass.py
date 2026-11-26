"""Fill the old settlement-mesh grass exclusion only between the real walls and the forest."""
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from generate_reference_hill import smooth
from generate_slope_grass import WEST, SOUTH, CELL, TILES, ROWS, COLS, grid_at, site_hash


def wall_grass(terrain: Path, destination: Path, baseline: Path):
    config = json.loads((terrain / 'hill.json').read_text())
    vx, vy = config['site_min_m']
    cx, cy = config['village_center_m']
    mask = np.fromfile(baseline, 'u1').reshape(TILES, TILES, ROWS, COLS)
    roads = np.vstack([np.loadtxt(terrain / (name+'-road.csv'), delimiter=',', skiprows=1)[:, :2]
                       for name in ('gate', 'quarry')])
    road_tree = cKDTree(roads)
    paint = np.fromfile(terrain / 'paint.rg8','u1').reshape(1025,1025,2)[...,0].astype('f4')/255.
    wet = np.fromfile(terrain / 'Grass/pond_wet.u8','u1').reshape(4097,4097)
    row,col = np.indices((ROWS,COLS), dtype='u4')
    added = 0
    tiles = 0
    for j in range(int((vy-SOUTH)//CELL), int((vy+145-SOUTH)//CELL)+1):
        for i in range(int((vx-WEST)//CELL), int((vx+118-WEST)//CELL)+1):
            ids = ((j*TILES+i)*ROWS+row)*COLS+col
            h = site_hash(ids)
            x = WEST + CELL*(i+(col+.25+.5*(row%2)+((h&255)/255.-.5)*.20)/COLS)
            y = SOUTH + CELL*(j+(row+.5+(((h>>8)&255)/255.-.5)*.20)/ROWS)
            a,b = np.abs(cy-y),np.abs(x-cx)
            outside = np.maximum.reduce((a-65., b-50., (a+b-109.)*.70710678))
            footprint = (vx<x)&(x<vx+118)&(vy<y)&(y<vy+145)
            eligible = footprint & (outside>.55) & (mask[j,i]==0)
            if not np.any(eligible):
                continue
            margin = road_tree.query(np.stack((x,y),axis=-1))[0]
            drift = .46*np.sin(x*.53+y*.24)+.37*np.cos(y*.31-x*.16)
            transition = smooth(.65,5.8,outside+drift)
            shoulder = smooth(2.5,4.5,margin)*(1.-smooth(.08,.62,grid_at(paint,x,y)))
            dry = wet[np.rint((y-SOUTH)*4).astype(int),np.rint((x-WEST)*4).astype(int)] < 32
            density = transition*shoulder*(.72+.12*drift)
            select = eligible & dry & ((site_hash(ids+np.uint32(3341))&65535)/65536. < density)
            n = int(select.sum())
            if not n:
                continue
            tiles += 1
            added += n
            variation = (site_hash(ids+np.uint32(76543))&65535)/65535.
            spreading = variation>.76
            cm = np.rint((17.+10.*transition+6.*variation)*(1.+.16*spreading)).astype('u1')
            mask[j,i][select] = ((cm<<2) | (1+spreading.astype('u1')))[select]
    mask.tofile(destination)
    return {'added_near_sites':added,'affected_cells':tiles}
