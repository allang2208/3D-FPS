"""Carpentered tavern screens. Building-local dimensions are Unreal centimetres."""
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.geometry import normal


OUT = Path(__file__).resolve().parents[4] / 'SourceAssets/HillsVillageTavern/KitchenScreen'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
COLORS = {'Oak': (.21,.13,.072), 'Endgrain': (.29,.18,.085), 'Plaster': (.56,.49,.37),
          'Rot': (.14,.12,.09), 'Iron': (.095,.078,.06), 'Daub': (.24,.16,.081)}
MATS = {}
for key, color in COLORS.items():
    MATS[key] = bpy.data.materials.new(key)
    MATS[key].diffuse_color = (*color, 1)


def rings_faces(count):
    return [tuple(reversed(range(count)))] + [
        (i, (i+1)%count, count+(i+1)%count, count+i) for i in range(count)
    ] + [tuple(range(count,count*2))]


def convert(point):
    x,y,z = point
    return (x*.01,-y*.01,z*.01)


class Screen:
    def __init__(self, ruined):
        self.ruined = ruined
        self.name = 'SM_TavernKitchenScreen' + ('Ruined' if ruined else '')
        self.rng = random.Random(7707)
        self.verts, self.faces, self.surfaces, self.hulls = [], [], [], []
        self.west = False

    def point(self,u,d,z):
        return Vector((125-d,u,z) if self.west else (u,-35+d,z))

    def shape(self, verts, faces, mat, grain, hull=False, ends=()):
        verts=list(map(Vector,verts))
        start=len(self.verts)
        self.verts.extend(map(convert,verts))
        if hull:
            self.hulls.append((list(map(convert,verts)), [tuple(reversed(f)) for f in faces]))
        axis=Vector(grain).normalized()
        u0,v0=self.rng.random(),self.rng.random()
        for j,face in enumerate(faces):
            points=[verts[i] for i in face]
            n=normal(points)
            long=axis-n*axis.dot(n)
            end=j in ends and mat in ('Oak','Rot')
            if long.length_squared<.00001:
                long=n.cross(Vector((0,0,1)) if abs(n.z)<.8 else Vector((1,0,0)))
            long.normalize()
            across=long.cross(n)
            scale=68 if end else (153 if mat=='Plaster' else 105)
            uv=[(u0+p.dot(across)/scale,v0+p.dot(long)/scale) for p in points]
            self.faces.append(tuple(start+i for i in reversed(face)))
            self.surfaces.append(('Endgrain' if end else mat, list(reversed(uv))))

    def beam(self, a,b, width,depth,mat='Oak',hull=True, ease=.65):
        # Section width runs in the screen plane, depth through its thickness.
        a=self.point(*a); b=self.point(*b)
        axis=(b-a).normalized()
        depth_dir=self.point(0,1,0)-self.point(0,0,0)
        depth_dir-=axis*axis.dot(depth_dir)
        if depth_dir.length_squared<.003:
            depth_dir=Vector((0,0,1))
        depth_dir.normalize()
        width_dir=depth_dir.cross(axis)
        hw,hd=width/2,depth/2
        k=min(ease,hw*.32,hd*.32)
        section=[(-hw+k,-hd),(hw-k,-hd),(hw,-hd+k),(hw,hd-k),
                 (hw-k,hd),(-hw+k,hd),(-hw,hd-k),(-hw,-hd+k)]
        verts=[p+u*width_dir+d*depth_dir for p in (a,b) for u,d in section]
        self.shape(verts,rings_faces(8),mat,axis,hull,(0,9))

    def peg(self,u,d,z,toward,mat='Endgrain',r=1.35):
        ring=[(math.cos(i*math.tau/8)*r,math.sin(i*math.tau/8)*r) for i in range(8)]
        verts=[self.point(u+dx,k,z+dz) for k in (d+.42,d-.42) for dx,dz in ring]
        self.shape(verts,rings_faces(8),mat,self.point(0,toward,0)-self.point(0,0,0))

    def slab(self,u0,u1,lo,hi,d0,d1,mat,hull=False):
        pts=[(u0,lo),(u1,lo),(u1,hi),(u0,hi)]
        verts=[self.point(u,d,z) for d in (d1,d0) for u,z in pts]
        self.shape(verts,rings_faces(4),mat,Vector((0,0,1)),hull)

    def panel(self,u0,u1,lo,hi,damage):
        if not self.ruined or not damage:
            self.slab(u0,u1,lo,hi,-5.1,5.1,'Plaster',True)
            return
        # Independent face skins return into a broken edge. The recessed daub core
        # and horizontally woven osiers only show where the lime is missing.
        self.slab(u0,u1,lo,hi,-.9,.9,'Daub',True)
        self.hulls[-1]=([convert(self.point(u,d,z)) for d in (5.1,-5.1)
                         for u,z in ((u0,lo),(u1,lo),(u1,hi),(u0,hi))],
                        [tuple(reversed(f)) for f in rings_faces(4)])
        cx=u0+(u1-u0)*damage[0]; cz=lo+(hi-lo)*damage[1]
        rx=min((u1-u0)*.40,(hi-lo)*.35)*damage[2]; rz=rx*1.04
        angles=[i*math.tau/22 for i in range(22)]
        angles.extend(math.atan2(z-cz,u-cx)%math.tau for u,z in ((u0,lo),(u1,lo),(u1,hi),(u0,hi)))
        angles.sort()
        outer=[]; inner=[]; inset=[]
        for t in angles:
            dx,dz=math.cos(t),math.sin(t)
            lim=min((u1-cx)/dx if dx>1e-8 else (u0-cx)/dx if dx< -1e-8 else math.inf,
                    (hi-cz)/dz if dz>1e-8 else (lo-cz)/dz if dz< -1e-8 else math.inf)
            outer.append((cx+dx*lim,cz+dz*lim))
            radius=min(lim*.91,1/math.hypot(dx/rx,dz/rz)*self.rng.uniform(.70,1.14))
            inner.append((cx+radius*dx,cz+radius*dz))
            inset.append((cx+(radius-.9)*dx,cz+(radius-.9)*dz))
        for side in (-1,1):
            for j in range(len(outer)):
                i=(j+1)%len(outer)
                for coords,depths,mat in (
                    ([outer[j],outer[i],inner[i],inner[j]],[5.1]*4,'Plaster'),
                    ([inner[j],inner[i],inset[i],inset[j]],[5.1,5.1,2.7,2.7],'Daub')
                ):
                    verts=[self.point(u,side*d,z) for (u,z),d in zip(coords,depths)]
                    face=(0,1,2,3) if side==-1 else (3,2,1,0)
                    self.shape(verts,[face],mat,Vector((0,0,1)))
        # Confine laths to the chipped area's bounding box beneath the remaining skin.
        ua=max(u0,cx-rx*1.18); ub=min(u1,cx+rx*1.18)
        za=max(lo,cz-rz*1.18); zb=min(hi,cz+rz*1.18)
        for side in (-1,1):
            for u in range(math.ceil(ua)+3,math.floor(ub),10):
                self.beam((u,side*2.0,za),(u+.75,side*2.0,zb),1.7,1.5,'Rot',False,.25)
            for row,z in enumerate(range(math.ceil(za)+1,math.floor(zb),4)):
                count=max(2,math.ceil((ub-ua)/8))
                last=(ua,side*2.7,z)
                for k in range(1,count+1):
                    new=(ua+(ub-ua)*k/count,side*(2.45+.72*((k+row)%2)),
                         z+.68*math.sin(k*1.35+row))
                    self.beam(last,new,1.35,1.05,'Rot',False,.22)
                    last=new

    def bay(self,u0,u1,lo,hi,spall=None,brace=False):
        self.panel(u0,u1,lo,hi,spall)
        if brace:
            for face in (-1,1):
                self.beam((u0+4,face*4.9,lo+2),(u1-4,face*4.9,hi-2),
                          10.5,2.6,'Oak',False,.42)

    def frame(self, west, posts, door, screen_end):
        self.west=west
        wood='Rot' if self.ruined else 'Oak'
        start=posts[0]+8
        end=screen_end
        # Long upper plate sits above the shared corner; the west one butts to it.
        self.beam(((start if west else posts[0]-8),0,286),(end,0,286),16,17,wood)
        for u in posts[1:] if west else posts:
            self.beam((u,0,0),(u,0,278),16,16,wood)
            for d in (-1,1):
                for z in (18,266,275):
                    self.peg(u,d*8,z,d)
        for idx,(a,b) in enumerate(zip(posts,posts[1:])):
            u0,u1=a+8,b-8
            if idx==door and west:
                self.beam((u0,0,230),(u1,0,230),16,16,wood)
                self.bay(u0,u1,238,278)
                for d in (-1,1):
                    for u in (a,b): self.peg(u,d*8,230,d)
                continue
            self.beam((u0,0,9),(u1,0,9),18,14,wood)
            if idx==door:
                self.bay(u0,u1,18,97,(.28,.47,.68))
                self.beam((u0,0,212),(u1,0,212),14,15,wood)
                self.bay(u0,u1,219,278)
                continue
            self.beam((u0,0,103),(u1,0,103),10,14,wood)
            self.bay(u0,u1,18,98,(.7,.46,.7) if idx==0 else None)
            self.bay(u0,u1,108,278,(.31,.42,.91) if idx==len(posts)-2 else None,
                     brace=idx in (0,len(posts)-2))
            for d in (-1,1): self.peg(a,d*8,103,d)

    def build(self):
        self.frame(False,[125,232,403,531,645],1,653)
        self.frame(True,[-35,68,177,327,417],2,425)
        self.west=False
        wood='Rot' if self.ruined else 'Oak'
        # Two joined ledge boards meet at the wall centre. Their top is exactly 104 cm.
        self.beam((231,-10.1,100.5),(404,-10.1,100.5),7,19.8,wood,ease=.8)
        self.beam((231,9.35,100.5),(404,9.35,100.5),7,18.7,wood,ease=.6)
        for u in (247,386):
            for side in (-1,1):
                self.beam((u,side*5,77),(u,side*16,97),5.2,5.2,wood,False)
                self.peg(u,side*7,84,side,r=1.5)
        # A swing catch is folded against the hall-side jamb beside the hatch.
        self.slab(398.5,407.5,146,150,-9.0,-8.0,'Iron')
        self.beam((401.4,-10.1,148.3),(403.6,-10.1,162.3),2.7,2.0,wood,False,.32)
        self.peg(401.5,-11.3,148.4,-1,'Iron',1.2)
        for u in (399.7,406.4): self.peg(u,-9.2,147.7,-1,'Iron',.43)
        self.export()

    def export(self):
        data=bpy.data.meshes.new(self.name)
        data.from_pydata(self.verts,[],self.faces)
        data.update()
        keys=list(dict.fromkeys(k for k,_ in self.surfaces))
        for k in keys: data.materials.append(MATS[k])
        uv=data.uv_layers.new(name='Joinery')
        for face,(key,coords) in zip(data.polygons,self.surfaces):
            face.material_index=keys.index(key)
            for i,p in zip(face.loop_indices,coords): uv.data[i].uv=p
        main=bpy.data.objects.new(self.name,data)
        bpy.context.collection.objects.link(main)
        bpy.ops.object.select_all(action='DESELECT')
        main.select_set(True); bpy.context.view_layer.objects.active=main
        tris=main.modifiers.new('Bake triangles','TRIANGULATE')
        bpy.ops.object.modifier_apply(modifier=tris.name)
        collision=bpy.data.collections.new(self.name+' Collision')
        bpy.context.scene.collection.children.link(collision)
        for i,(verts,faces) in enumerate(self.hulls):
            name=f'UCX_{self.name}_{i:02d}'
            mesh=bpy.data.meshes.new(name)
            mesh.from_pydata(verts,[],faces); mesh.update()
            obj=bpy.data.objects.new(name,mesh)
            collision.objects.link(obj)
            obj.display_type='WIRE'; obj.hide_render=True; obj.select_set(True)
        bpy.ops.export_scene.fbx(filepath=str(OUT/(self.name+'.fbx')),use_selection=True,
                                 object_types={'MESH'},axis_forward='-Y',axis_up='Z',
                                 mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,
                                 add_leaf_bones=False)
        collision.hide_viewport=True
        if self.ruined: main.hide_set(True)


for ruined in (False,True): Screen(ruined).build()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TavernKitchenScreens.blend'))
