from mathutils import Vector,Matrix
PATH=[(0,0,-.035),(0,0,-.070),(0,.016,-.085)]
def connector_mesh():
    vertices=[];faces=[]
    for start,end in zip(PATH,PATH[1:]):
        a,b=Vector(start),Vector(end);q=(b-a).to_track_quat('Z','Y');centre=(a+b)/2;offset=len(vertices)
        for z in (-1,1):
          for y in (-1,1):
           for x in (-1,1):vertices.append(centre+q@Vector((x*.0018,y*.0018,z*(b-a).length/2)))
        for quad in ((0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)):
          faces.extend([(offset+quad[0],offset+quad[1],offset+quad[2]),(offset+quad[0],offset+quad[2],offset+quad[3])])
    return vertices,faces
