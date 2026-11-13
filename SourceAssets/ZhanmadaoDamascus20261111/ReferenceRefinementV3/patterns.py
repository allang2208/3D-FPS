"""Original contour steel fields inspired by the user's two blade photographs.

The images guide morphology and contrast; they are not projected onto a blade.
This is material data authoring, without scene rendering or visual test capture.
"""
import json
from pathlib import Path
import bpy
import numpy as np

P = Path(__file__).resolve().parent
NX, NY = 2048, 4096
WX, WZ = 12., 88.


def smooth(a, b, value):
    t = np.clip((value-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def noise(rng, x, z, gx, gz):
    grid = rng.uniform(-1, 1, (gz, gx)).astype(np.float32)
    u, v = x/WX*gx, z/WZ*gz
    ix, iz = np.floor(u).astype(np.int32), np.floor(v).astype(np.int32)
    a, b = u-ix, v-iz
    a, b = (a*a*(3-2*a)).astype(np.float32), (b*b*(3-2*b)).astype(np.float32)
    return ((1-a)*grid[iz % gz, ix % gx] + a*grid[iz % gz, (ix+1) % gx])*(1-b) + (
        (1-a)*grid[(iz+1) % gz, ix % gx] + a*grid[(iz+1) % gz, (ix+1) % gx])*b


def contours(rng, x, z, gx, gz):
    """Smooth distance basins with irregular centres and curved shared borders."""
    cx = rng.uniform(.16, .84, (gz, gx)).astype(np.float32)
    cz = rng.uniform(.16, .84, (gz, gx)).astype(np.float32)
    angle = rng.uniform(-np.pi, np.pi, (gz, gx)).astype(np.float32)
    aspect = rng.uniform(.80, 1.22, (gz, gx)).astype(np.float32)
    size = rng.uniform(.90, 1.13, (gz, gx)).astype(np.float32)
    u, v = x/WX*gx, z/WZ*gz
    ix, iz = np.floor(u).astype(np.int32), np.floor(v).astype(np.int32)
    near = np.full(x.shape, 1e5, dtype=np.float32)
    second = near.copy()
    for dz in [-1, 0, 1]:
        for dx in [-1, 0, 1]:
            row, column = (iz+dz) % gz, (ix+dx) % gx
            px = (u-(ix+dx)-cx[row, column]).astype(np.float32)
            pz = (v-(iz+dz)-cz[row, column]).astype(np.float32)
            theta = angle[row, column]
            co, si = np.cos(theta), np.sin(theta)
            ax = (px*co+pz*si)*aspect[row, column]
            az = (-px*si+pz*co)/aspect[row, column]
            radius = np.sqrt(ax*ax+az*az+.0005)
            phi = np.arctan2(az, ax)
            # Each basin has its own rounded, slightly triangular contour.
            radius *= (1+.085*np.sin(phi*3+theta)+.045*np.cos(phi*2-theta))*size[row, column]
            second = np.minimum(second, np.maximum(near, radius))
            near = np.minimum(near, radius)
    return near-np.log1p(np.exp(-(second-near)*10.))/10.


def layer_response(phase):
    wave = np.cos(phase*2*np.pi)
    broad = smooth(-.04, .83, wave)
    fine = smooth(.78, .995, -wave)*.46
    return np.clip(.045+.91*np.maximum(broad, fine), 0, 1)


def author(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    x, z = np.meshgrid(np.arange(NX, dtype=np.float32)/NX*WX,
                       np.arange(NY, dtype=np.float32)/NY*WZ)
    descriptions = {'Flow': 'elongated nested return-flow contours',
                    'Twist': 'irregular closed raindrop and rosette contours',
                    'Feather': 'paired feather-scroll contours following a longitudinal axis'}
    for index, family in enumerate(descriptions):
        rng = np.random.default_rng(11112026+index*1301+333)
        macro = noise(rng, x, z, 5, 17)
        fine = noise(rng, x, z, 13, 53)
        if family == 'Feather':
            # Mirror the folded structure about the centre, with curved feather
            # branches sweeping toward the blade's sides, as in reference one.
            axis = .11*np.sin(z/WZ*2*np.pi*9)+.065*np.sin(z/WZ*2*np.pi*17)
            lateral = (x-WX*.5-axis+WX*.5) % WX-WX*.5
            folded = np.sqrt(lateral*lateral+.004)
            qx = folded+.10*macro+.035*fine
            qz = z-folded*.92+.19*macro
            radius = contours(rng, qx, qz, 6, 46)
            phase = radius*5.4+.10*macro+.025*fine
        else:
            qx = x+.24*macro+.075*fine
            qz = z+.31*noise(rng, x, z, 6, 31)+.07*fine
            radius = contours(rng, qx, qz, 7, 34 if family == 'Flow' else 54)
            phase = radius*(5.2 if family == 'Flow' else 4.9)+.09*macro+.025*fine
        # Integrate the narrow secondary steel line over its texel footprint.
        pz, px = np.gradient(phase)
        footprint = np.minimum(np.abs(px)+np.abs(pz), .35)
        layers = (layer_response(phase-footprint*.25)+layer_response(phase+footprint*.25))*.5
        height = (layers-.5)*.00065  # 6.5 micrometres peak-to-peak etch
        sx = (np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(2*WX/NX)
        sz = (np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(2*WZ/NY)
        packed = np.stack([layers, .5+.5*np.tanh(sx/.025), .5+.5*np.tanh(sz/.025),
                           np.clip(.5+.27*macro+.055*fine,0,1)], axis=-1).astype(np.float32)
        image = bpy.data.images.new('ReferenceDamascus_'+family, width=NX, height=NY, alpha=True)
        image.colorspace_settings.name = 'Non-Color'
        image.pixels.foreach_set(packed[::-1].ravel())
        image.filepath_raw = str(destination/('Damascus_'+family+'_Field.png'))
        image.file_format = 'PNG'; image.save(); bpy.data.images.remove(image)
        print('DAMASCUS_REFERENCE_FIELD_AUTHORED', family, flush=True)
        del packed, radius, phase, layers, height, sx, sz
    (P/'author-receipt.json').write_text(json.dumps(dict(revision='ReferenceV3',
        patterns=descriptions, resolution=[NX,NY], field_size_cm=[WX,WZ],
        references=['References/feather-scroll.png','References/closed-contours.png'],
        origin='original procedural contour fields', rendered=False, game_tested=False),
        ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    author(P.parent/'Textures')
