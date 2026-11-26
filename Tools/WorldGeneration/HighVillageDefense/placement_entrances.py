"""Build local-space entrance overlays from the same parts as the village defenses."""
import sys
from pathlib import Path

import source_mesh
from chapel_gatehouse import CAP, door_surround
from high_watchtower import HALF, LEVELS, Tower, courtyard_leaf, dressed_opening

SOURCE = source_mesh.ROOT / 'SourceAssets/HillsVillageHighWall20261120'
sys.path.insert(0, str(SOURCE / 'Stairs'))
import access_stairs as stairs


class Highlight(Tower):
    def triangle(self, a, b, c, material, offset=(0., 0.)):
        super().triangle(a, b, c, CAP)

    def save(self, name):
        self.boxes.clear()
        super().save(name)

    def chevron(self, x, y, z, dx, dy, width, length):
        """A flat V with its tip at (x,y), pointing along the unit vector (dx,dy)."""
        def point(side, back):
            return (x-dy*side-dx*back, y+dx*side-dy*back, z)
        for sign in (-1,1):
            a,b,c,d=(point(0.,0.),point(sign*width/2.,length),
                     point(sign*width/2.,length*1.42),point(0.,length*.42))
            self.triangle(a,b,c,CAP)
            self.triangle(a,c,d,CAP)


def tower():
    mesh=Highlight(47231)
    for side in (2,1,3):
        mesh.side=side
        sill=0. if side==2 else LEVELS[1]
        dressed_opening(mesh,0.,sill,True)
        mesh.chevron(0.,-HALF-48.,sill+6.,0.,1.,142.,67.)
    mesh.side=0
    courtyard_leaf(mesh)
    mesh.save('SM_TowerEntrances')


def gate():
    # The construction palette places the east gate. The arch and both jambs
    # are the ones actually authored for that variant.
    mesh=Highlight(3857)
    half,rear=434.,264.
    front=rear-2.*half
    for face,direction in ((front,-1),(rear,1)):
        door_surround(mesh,half-188.,236.,500.-75.-236.,face,direction)
    mesh.chevron(0.,front-176.,9.,0.,-1.,214.,85.)
    for sign in (-1,1):
        x=sign*(half-52.)
        mesh.block(x-46.,x+46.,rear-6.,rear+12.,360.,364.,CAP,False)
    mesh.save('SM_StoneGateEntrances')


def access_flight():
    mesh=Highlight(stairs.PAVING_SEED)
    # Reuse the actual tread stones, including their seeded joints and nosings.
    mesh.rng.seed(stairs.PAVING_SEED)
    for _ in range(stairs.PAVING_DRAW_OFFSET):
        mesh.rng.random()
    for i in range(2):
        y=stairs.FLIGHT_START+i*stairs.RUN
        stairs.tread(mesh,-160.,0.,y,1,stairs.RISE*(i+1),i)
        stairs.tread(mesh,0.,160.,y+stairs.RUN,-1,stairs.DECK-i*stairs.RISE,i)
    mesh.chevron(-80.,stairs.FLIGHT_START-8.,4.,0.,1.,123.,57.)
    mesh.chevron(80.,stairs.SOCKET-12.,stairs.DECK+3.,0.,-1.,120.,53.)
    mesh.block(0.,160.,stairs.SOCKET,stairs.SOCKET+12.,stairs.DECK,stairs.DECK+2.,CAP,False)
    mesh.block(148.,160.,stairs.SOCKET+12.,stairs.FLIGHT_START,stairs.DECK,stairs.DECK+2.,CAP,False)
    mesh.save('SM_StairEntrances')


if __name__=='__main__':
    source_mesh.OUT=SOURCE/'PlacementPreview'
    source_mesh.OUT.mkdir(exist_ok=True,parents=True)
    tower()
    gate()
    access_flight()
    timber=Highlight(0)
    timber.chevron(0.,-148.,5.,0.,-1.,185.,78.)
    timber.save('SM_WoodGateExterior')
