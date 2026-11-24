"""Front-view registrations measured on the resting half of RavenQuill-Effect-V1.png."""

CENTER = 442.5
PIXELS_PER_CM = 28.0
# The bottom ferrule meets the existing grip at -5 cm. Preserve the front aspect ratio.
# Horizontal distances from the central ridge, top and lower edges in image pixels.
# The short lower return curls back into the socket behind the three overlapping vanes.
VANES = [
    [(29,314,482),(40,323,472),(58,348,449),(80,363,430),(110,370,413),
     (152,369,405),(203,363,399),(256,354,392),(304,344,383),(347,332,374),
     (371,325,369),(391,317,343),(412,311,311.65)],
    [(31,354,488),(48,377,469),(68,392,450),(95,400,433),(130,401,427),
     (176,399,426),(224,394,427),(268,391,425),(303,389,421),(326,386,405),
     (350,382,382.65)],
    [(32,398,494),(52,411,473),(81,423,454),(108,427,446),(141,429,449),
     (181,432,459),(210,434,461),(243,436,457),(264,435,447),(288,432,432.65)],
    [(29,440,497),(47,440,495),(63,442,472),(85,443,466),(107,445,468),
     (139,452,479),(161,458,482),(183,462,478),(201,466,473),(215,467,467.65)],
]
# The crest is widest at the shoulders and pointed at both ends.
CREST = [(0,321,491),(7,330,484),(18,345,465),(34,359,445),
         (50,370,422),(62,378,399),(72,383,383.8)]
VEINS = [((2,466),(39,416)),((2,448),(50,391)),((2,423),(43,370)),((2,395),(28,349))]
ATLAS_W, ATLAS_H = 2048, 1024
# Atlas rectangles are in texel-edge coordinates, source rectangles in concept pixels.
FIELD = ((0,0,2048,640),(15,279,871,545))
MEDAL = ((0,640,512,1024),(353,285,533,508))

def physical_x(dx):
    return dx/PIXELS_PER_CM

def image_x(x):
    return CENTER+x*PIXELS_PER_CM

def physical_z(py):
    return -5.0+(539-py)/PIXELS_PER_CM

def image_y(z):
    return 539-(z+5.0)*PIXELS_PER_CM

def registered_uv(chart,px,py):
    (l,t,r,b),(x0,y0,x1,y1)=chart
    return ((l+(px-x0)*(r-l)/(x1-x0))/ATLAS_W,
            1-(t+(py-y0)*(b-t)/(y1-y0))/ATLAS_H)
