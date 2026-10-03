"""Pixel-diff pristine vs bottomseal under renders; quantify black-hole reduction."""
from pathlib import Path
import struct, zlib, json

OUT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923\inspect_akm_a762')

def read_png_rgba(path):
    # minimal PNG reader for 8-bit RGBA/RGB
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos = 8
    width = height = None
    idat = b''
    color_type = None
    while pos < len(data):
        length = int.from_bytes(data[pos:pos+4], 'big'); pos += 4
        ctype = data[pos:pos+4]; pos += 4
        chunk = data[pos:pos+length]; pos += length
        pos += 4  # crc
        if ctype == b'IHDR':
            width, height = struct.unpack('>II', chunk[:8])
            color_type = chunk[9]
        elif ctype == b'IDAT':
            idat += chunk
        elif ctype == b'IEND':
            break
    raw = zlib.decompress(idat)
    # parse scanlines with filter 0 assumed after undo
    bpp = {2:3, 6:4}[color_type]
    stride = width * bpp
    rows = []
    i = 0
    prev = bytearray(stride)
    for y in range(height):
        filt = raw[i]; i += 1
        row = bytearray(raw[i:i+stride]); i += stride
        if filt == 1:  # Sub
            for x in range(stride):
                left = row[x-bpp] if x >= bpp else 0
                row[x] = (row[x] + left) & 255
        elif filt == 2:  # Up
            for x in range(stride):
                row[x] = (row[x] + prev[x]) & 255
        elif filt == 3:  # Average
            for x in range(stride):
                left = row[x-bpp] if x >= bpp else 0
                row[x] = (row[x] + ((left + prev[x])//2)) & 255
        elif filt == 4:  # Paeth
            for x in range(stride):
                left = row[x-bpp] if x >= bpp else 0
                up = prev[x]
                ul = prev[x-bpp] if x >= bpp else 0
                p = left + up - ul
                pa, pb, pc = abs(p-left), abs(p-up), abs(p-ul)
                pr = left if pa<=pb and pa<=pc else (up if pb<=pc else ul)
                row[x] = (row[x] + pr) & 255
        elif filt != 0:
            raise RuntimeError('bad filter %d'%filt)
        rows.append(row); prev = row
    return width, height, bpp, rows

def black_hole_score(path, thresh=25):
    w,h,bpp,rows = read_png_rgba(path)
    # count near-black pixels that are interior (not image border)
    black = 0
    # also count black pixels surrounded by non-black (hole interior)
    holes = 0
    gray = [[0]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            o = x*bpp
            r,g,b = rows[y][o], rows[y][o+1], rows[y][o+2]
            lum = (r+g+b)//3
            gray[y][x] = lum
            if lum < thresh:
                black += 1
    for y in range(2, h-2):
        for x in range(2, w-2):
            if gray[y][x] >= thresh:
                continue
            n_lit = sum(1 for dy in range(-2,3) for dx in range(-2,3) if gray[y+dy][x+dx] >= thresh)
            if n_lit >= 12:
                holes += 1
    return {'black': black, 'hole_px': holes, 'w': w, 'h': h}

pairs = {
    'pristine_bodyonly_under': OUT/'A762_bodyonly_under.png',
    'bottomseal_bodyonly_under': OUT/'A762_bottomseal_bodyonly_under.png',
    'mouthpatch_bodyonly_under': OUT/'A762_mouthpatch_bodyonly_under.png',
    'cylpatch_bodyonly_under': OUT/'A762_cylpatch_bodyonly_under.png',
    'ringfill_bodyonly_under': OUT/'A762_ringfill_bodyonly_under.png',
    'pristine_under': OUT/'A762_body_under.png',
    'bottomseal_under': OUT/'A762_bottomseal_under.png',
}
rep = {}
for k,p in pairs.items():
    if p.exists():
        rep[k] = black_hole_score(p)
(OUT/'a762_pixel_holes.json').write_text(json.dumps(rep, indent=2), encoding='utf-8')
print(json.dumps(rep, indent=2))
