"""Transfer measured hill relief onto the 1 m village grid. Arguments: source directory."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
sys.path.insert(0, str(TOOLS.parent / 'AbandonedVillage'))
from layout_geometry import house_paths, plot_geometry, wall_segments
from village_ground_relief import box, distance, mill_yard_gap
from village_tread import ramp

# ISM groups baked into the village sublevel that can ride the terrain as a unit per instance.
FOLLOW = ('SM_Grass', 'SM_SoftWildGrass', 'SM_PlantType', 'flower_', 'SM_Stone_0',
          'SM_DebrisScatter', 'SM_ForestTwig', 'SM_MortarChunk', 'SM_H_RubblePile',
          'SM_DeadTree_', 'SM_Meadow_lowGrass', 'SM_Hazel_', 'SM_QuarryChip', 'SM_MillFieldstone')


def generate(out, *, site_weights=False, wall_flanks=False):
    layout_dir = ROOT/'SourceAssets/TemperateHillsVillage'
    layout = json.loads((layout_dir/'layout.json').read_text('utf-8-sig'))
    pieces = json.loads((layout_dir/'house-pieces.json').read_text('utf-8-sig'))
    contacts = json.loads((out/'contacts.json').read_text('utf-8'))
    source = np.fromfile(out/'reference.f32', '<f4')
    forest = source[:505*505].reshape(505, 505)
    old_cm = source[505*505:].reshape(146, 119)
    row, col = np.indices(old_cm.shape)
    wx, wy = -172+col, 252+row
    x, y = 323.-wy, wx+113.  # village local metres

    # This contiguous road-free donor is on a wooded slope of the live Landscape.
    # Filter the complete DEM before cropping so the donor has no artificial rim.
    patch = np.s_[189:312, 63:162]   # world XY from (-189,-63) to (-91,59), inclusive
    fine = gaussian_filter(forest, .85) - gaussian_filter(forest, 3.5)
    middle = gaussian_filter(forest, 3.5) - gaussian_filter(forest, 10.)
    donor = fine + middle
    coords = [189 + row*122./145, 63 + col*98./118]
    sample = lambda band: map_coordinates(band, coords, order=1, prefilter=False)
    ground_shape = sample(middle)*.73 + sample(fine)*.82
    # Smoothly limit the extremes while retaining their local shapes and signs.
    land = np.where(ground_shape>=0, 78*np.tanh(ground_shape/78), 60*np.tanh(ground_shape/60))

    clear = np.full(old_cm.shape, 1000.)
    def protect(field):
        np.minimum(clear, field, out=clear)
    for plot in layout['houses']:
        shape = plot_geometry(plot, pieces[plot[2]], layout)
        protect(box(x,y,shape['center'],shape['half'],shape['angle']))
        protect(distance(x,y,[shape['entry'],shape['step']])-.95)
        if plot[0]=='05':
            protect(mill_yard_gap(x,y,shape))
    for yard in layout['service_clearings']:
        protect(box(x,y,yard['center'],yard['half'],yard['yaw']))
    if not wall_flanks:
        for piece, width in wall_segments(layout):
            protect(distance(x,y,[piece[1:3],piece[3:5]])-width)
    # The same octagonal perimeter seats both the ruined wall and its repaired version.
    ex, ey = layout['surface_extent_m']
    cut = 6.
    corners = [(ex-cut,ey),(-ex+cut,ey),(-ex,ey-cut),(-ex,-ey+cut),
               (-ex+cut,-ey),(ex-cut,-ey),(ex,-ey+cut),(ex,ey-cut)]
    if not wall_flanks:protect(distance(x,y,corners+[corners[0]])-.78)
    protect(box(x,y,(ex,5.),(3.3,4.8)))
    protect(box(x,y,(-ex,0.),(3.3,5.5)))
    cx, cy = layout['chapel']['center']
    front, back, side, _ = layout['chapel']['yard']
    protect(box(x,y,(cx+(front+back)/2,cy),((back-front)/2,side)))
    protect(np.hypot(x-(cx+front-9),y-cy)-5.)   # forecourt shrine and its plinth
    protect(box(x,y,(-40.8,-9.),(4.4,3.6)))   # smith yard changes state, from the same stored datum
    forecourt = layout['tavern_forecourt']
    ox,oy = forecourt['origin']
    angle = np.deg2rad(forecourt['yaw'])
    dx,dy = -.35,-2.38
    protect(box(x,y,(ox+dx*np.cos(angle)-dy*np.sin(angle),oy+dx*np.sin(angle)+dy*np.cos(angle)),
                (4.60,1.72),forecourt['yaw']))
    # Actor-local boxes use the same axes as the layout. Rasterize only the small
    # expanded box per contact. A 1.45 m collar locks all vertices of a touched triangle.
    for a,b,c,d,name,instanced in contacts:
        if wall_flanks and "wall" in name.lower():continue  # Seated on the actual segment below in the wall-grading recipe.
        if instanced and name.startswith(FOLLOW):
            continue
        near = (x>=a-6)&(x<=c+6)&(y>=b-6)&(y<=d+6)
        if np.any(near):
            gap = np.hypot(np.maximum.reduce((a-x[near],x[near]-c,np.zeros(near.sum()))),
                           np.maximum.reduce((b-y[near],y[near]-d,np.zeros(near.sum()))))
            clear[near] = np.minimum(clear[near],gap)
    setback = ramp((clear-1.45)/3.6)
    seam = np.minimum.reduce((col,118-col,row,145-row))
    # R3 has a handful of baked apron grasses within the first 4.4 m.
    join = ramp((seam-1.)/4.) * ramp((row-5.)/4.)

    roads = [(r['points'],r['width']) for r in layout['roads']] + house_paths(layout,pieces)
    road_gap=np.full(old_cm.shape,1000.)
    for points,width in roads:
        np.minimum(road_gap,distance(x,y,points)-width*.5,out=road_gap)
    cx,cy,rx,ry = layout['square']
    np.minimum(road_gap,(np.hypot((x-cx)/rx,(y-cy)/ry)-1.)*min(rx,ry),out=road_gap)
    # Also read the finished road paint, which includes newer shop paths and turnouts.
    road=np.asarray(Image.open(layout_dir/'RoadMask.png').convert('RGBA'))[...,0]/255.
    paint=map_coordinates(road,[(.5+y/(2*ey))*road.shape[0]-.5,(.5+x/(2*ex))*road.shape[1]-.5],
                          order=1,mode='constant',cval=0.,prefilter=False)
    open_ground = ramp((road_gap+.1)/3.6) * (1-ramp((paint-.18)/.53))
    if site_weights:
        return setback, open_ground
    road_height = 5.*np.tanh(sample(middle)/75.)
    delta = np.rint((road_height+(land-road_height)*open_ground)*setback*join).astype('i1')
    absolute = np.rint(old_cm).astype('i2')+delta
    for name,cm in [('H_MeasuredSlope',forest[patch]),('H_SlopeRelief',donor[patch]),
                    ('H_VillageDelta',delta),('H_Village',absolute)]:
        Image.fromarray((32768+np.rint(cm).astype('i4')).astype('uint16')).save(out/(name+'.png'))
    delta.tofile(out/'village-delta.i8')
    generated = ROOT/'Source/FPSGAME/WorldGeneration/ForestVillageReliefData.inl'
    lines = ['// Generated by generate_village_relief.py from the measured forest Landscape.',
             'constexpr const TCHAR* GroundDressingPrefixes[] = {'+
             ', '.join('TEXT("'+v+'")' for v in FOLLOW)+'};',
             'constexpr int8 ReliefCm[Rows][Columns] = {']
    lines.extend('    {'+','.join(map(str,line))+'},' for line in delta.tolist())
    generated.write_text('\n'.join([*lines,'};','']),encoding='utf-8')
    mask = (open_ground>.80)&(setback>.85)&(join>.85)
    stats = dict(village_origin_xy_m=[-172,252],village_grid_xy=[119,146],sample_spacing_m=1,
                 encoding_16bit_png='32768 = 0 cm, rows increase along world Y',
                 donor_source='/Game/ForestPathStudy/Maps/L_ForestPathForest',
                 donor_bounds_xy_m=[[-189,-63],[-91,59]],donor_grid_xy=[99,123],
                 donor_elevation_range_m=round(float(np.ptp(forest[patch])*.01),2),
                 gaussian_sigma_m=[.85,3.5,10.],contact_boxes=len(contacts),houses=len(layout['houses']),
                 delta_cm=[int(delta.min()),int(delta.max())],open_p10_p90_cm=np.percentile(delta[mask],[10,90]).round().astype(int).tolist(),
                 changed_vertices=int(np.count_nonzero(delta)),locked_vertices=int(np.count_nonzero(setback*join==0)),
                 road_center_limit_cm=5, open_sample_count=int(mask.sum()))
    (out/'generation.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    print(json.dumps(stats,indent=2))


if __name__=='__main__':
    generate(Path(sys.argv[1]))

