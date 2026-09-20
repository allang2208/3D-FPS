"""Live V4/V5 UE/Blender conversion helpers retained from the rejected V3.

Author scripts extract these functions with AST and supply their calibrated
C, K, rest, smooth and mathutils globals. This file has no authoring side effects.
"""
def from_ue(w):
 return {n:Matrix.LocRotScale(C@Vector(w[n]['p'])*.01,(C@Quaternion(w[n]['q']).to_matrix()@C@K[n]).to_quaternion(),Vector(w[n]['s'])*.01) for n in rest}
def ue_matrix(x):return Matrix.LocRotScale(Vector(x['p']),Quaternion(x['q']),Vector(x['s']))
def to_ue(pose,world):
 return {n:(Matrix.LocRotScale(C@pose[n].translation*100,(C@pose[n].to_quaternion().to_matrix()@K[n].inverted()@C).to_quaternion(),Vector(world[n]['s'])) if n in pose else ue_matrix(v)) for n,v in world.items()}
def qangle(a,b):
 q=a.rotation_difference(b);return 2*math.atan2(Vector((q.x,q.y,q.z)).length,abs(q.w))
def gate(pose,idle,side):
 h='hand_'+side;u='upperarm_'+side
 distance=(pose[h].translation-idle[h].translation).length
 rotation=qangle(pose[h].to_quaternion(),idle[h].to_quaternion())
 shoulder=(pose[u].translation-idle[u].translation).length
 return 1-smooth(max((distance-.003)/.10,(rotation-.025)/.60,(shoulder-.003)/.05))
