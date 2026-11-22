"""Rasterize the five editable guild marks into the two independent R2 oak faces."""
from pathlib import Path
import sys
from xml.etree import ElementTree

import numpy as np
from PIL import Image, ImageDraw
from fontTools.pens.basePen import BasePen
from fontTools.svgLib.path import parse_path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'VillageBlacksmith/ForgeR2'))
from weather_wood import grain, n

SOURCE = HERE.parents[2]/'SourceAssets/HillsVillageTradeSigns'


class PaintedPath(BasePen):
    def __init__(self, canvas, path):
        super().__init__(None)
        self.draw = ImageDraw.Draw(canvas)
        self.path = path
        self.scale = canvas.width / 100.
        self.points = []

    def _moveTo(self, pt):
        self.points = [pt]

    def _lineTo(self, pt):
        self.points.append(pt)

    def _curveToOne(self, a, b, end):
        start = np.asarray(self.points[-1])
        for t in np.arange(1, 17)/16:
            point = ((1-t)**3*start + 3*t*(1-t)**2*np.array(a) +
                     3*t*t*(1-t)*np.array(b) + t**3*np.array(end))
            self.points.append(tuple(point))

    def _closePath(self):
        self.points.append(self.points[0])
        self._endPath()

    def _endPath(self):
        points = [(round(x*self.scale), round(y*self.scale)) for x,y in self.points]
        if self.path.get('fill') != 'none':
            self.draw.polygon(points, fill=self.path.get('fill'))
        if self.path.get('stroke'):
            self.draw.line(points, fill=self.path.get('stroke'),
                           width=round(float(self.path.get('stroke-width'))*self.scale), joint='curve')


if __name__ == '__main__':
    for design in sorted(SOURCE.glob('*.svg')):
        canvas = Image.new('RGB', (2*n, 2*n))
        for path in ElementTree.parse(design).getroot():
            parse_path(path.attrib['d'], PaintedPath(canvas,path))
        paint = np.asarray(canvas.resize((n,n), Image.Resampling.LANCZOS), dtype=np.float32)/255.
        faces = [grain(side,paint)[0] for side in (0,1)]
        Image.fromarray(np.concatenate(faces,axis=1)).save(SOURCE/('T_'+design.stem+'Sign_Color.png'))
