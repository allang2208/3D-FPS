from native_geometry import *
INDIGO,EDGE,LINING,SILVER,DARKSILVER,BRASS,THREAD,CRYSTAL,RUNE,ETCH=range(10)
TITANIUM=SILVER;GRAPHITE=DARKSILVER

def rounded(w,h,r,n=8):
    out=[]
    for x,z,a in ((w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)):
        for q in np.linspace(a,a+90,n,endpoint=False):out.append([x+r*math.cos(math.radians(q)),z+r*math.sin(math.radians(q))])
    return np.array(out)

def catmull(points,steps=10):
    q=np.array(points,dtype=float);q=np.vstack((q[0],q,q[-1]));out=[]
    for i in range(1,len(q)-2):
        a,b,c,d=q[i-1:i+3]
        for t in np.linspace(0,1,steps,endpoint=False):out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return np.array(out+[q[-2]])

class BeltConstruction(NativeBelt):
    def __init__(self,row):
        super().__init__(row)
        self.parts=[]
        self.scene['asset_name']='星律导能腰带'
        self.scene['production_stage']='Detailed model; no gameplay integration'
        self.scene['front_definition']='Native body forward; inventory display normalized separately'
        # The exporter reads this named group for the AO channel of the same ORM.
        settings=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
        settings.interface.new_socket('Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
        settings.nodes.new('NodeGroupInput');settings.nodes.new('NodeGroupOutput')
        for material in self.mats:
            separate=next((n for n in material.node_tree.nodes if n.bl_idname=='ShaderNodeSeparateColor'),None)
            if separate:
                node=material.node_tree.nodes.new('ShaderNodeGroup');node.node_tree=settings
                material.node_tree.links.new(separate.outputs['Red'],node.inputs['Occlusion'])

    def finish(self,ob,bevel=.055):
        if bevel:
            b=ob.modifiers.new('Manufactured edge radius','BEVEL');b.width=bevel*.01;b.segments=4;b.limit_method='ANGLE';b.angle_limit=math.radians(38);b.use_clamp_overlap=True;b.harden_normals=True
        n=ob.modifiers.new('Preserved planar hard-surface normals','WEIGHTED_NORMAL');n.keep_sharp=True;n.weight=45
        return ob

    def stitch(self,name,path,normals,mat=THREAD,pitch=.26,radius=.015):
        return Cap.stitch(self,name,path,normals,mat,pitch,radius)

    def frame(self,*args,**kwargs):
        return self.finish(Cap.frame(self,*args,**kwargs),0)

    def prism(self,name,outline,y0,y1,mat,bevel=.055):
        a=np.array(outline);n=len(a)
        ps=[[x,y,z] for y in (y0,y1) for x,z in a]
        fs=[list(range(n-1,-1,-1)),list(range(n,n*2))]
        fs += [[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
        return self.finish(self.mesh(name,ps,fs,mat),bevel)

    def ring(self,name,x,y,z,w,h,r=.17,mat=TITANIUM):
        line=[[x+a,y,z+b] for a,b in rounded(w,h,min(w,h)*.30,12)]
        return self.tube(name,[line],r,mat,sides=12,closed=True)

    def fastener(self,name,x,y,z,r=.22,mat=TITANIUM):
        # Recessed hex drive, bevelled rim, actual lower socket floor.
        n=24;ps=[];fs=[]
        for radius,depth,hexagon in [(r,0,False),(r,.065,False),(.84*r,.10,False),(.43*r,.10,True),(.43*r,.025,True)]:
            for k in range(n):
                a=TAU*k/n;rr=radius
                if hexagon:rr*=math.cos(math.pi/6)/math.cos((a%(math.pi/3))-math.pi/6)
                ps.append([x+rr*math.cos(a),y+depth,z+rr*math.sin(a)])
        for j in range(4):
            for k in range(n):fs.append([j*n+k,j*n+(k+1)%n,(j+1)*n+(k+1)%n,(j+1)*n+k])
        fs.extend([list(range(n-1,-1,-1)),list(range(4*n,5*n))])
        return self.mesh(name,ps,fs,mat)
