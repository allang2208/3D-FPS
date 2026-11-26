"""Re-author only worn helmet sizes; reuse the accepted detail/material sources."""
import importlib.util,json,sys
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');T=P/'Tools/ModernTacticalSet'
R=P/'SourceAssets/ModernTacticalSet20261113/HelmetHairFitR1'
BASE=R.parent/'HelmetDetailR1'
# Derive from the exact detailed author, retaining its mechanical pieces, UVs,
# native chin fit and 0.65 cm shell wall. Only the crown envelope changes.
source=(T/'helmet1_author.py').read_text(encoding='utf-8')
source=source.replace("R=S/'HelmetDetailR1'","R=S/'HelmetHairFitR1'")
source=source.replace("str(R/'Textures'/f'H1_{name}_{c}.png')","str(S/'HelmetDetailR1'/'Textures'/f'H1_{name}_{c}.png')")
old="cz=top-10.2;rz=11.7;center=np.array([cx,cy,cz]);headtree="
new="cz=top-10.2;fit=read(R/'fit.json')['profiles'][rig];rx=fit['rx'];ry=fit['front_radius'];rear_radius=fit['rear_radius'];rz=fit['rz'];power=fit['vertical_power'];cx,cy,cz=fit['center'];center=np.array([cx,cy,cz]);headtree="
if source.count(old)!=1:raise RuntimeError('Detailed author envelope changed; rebase this scoped adapter')
source=source.replace(old,new)
source=source.replace('phi=math.acos(np.clip((edge-cz)/rz,-1,1))*t;rad=math.sin(phi)',"edge_n=np.clip((edge-cz)/rz,-1,1);phi=math.acos(np.sign(edge_n)*abs(edge_n)**(power/2))*t;rad=max(0,math.sin(phi))**(2/power)")
source=source.replace('ry*rad*c,rz*math.cos(phi)',"(ry if c>=0 else rear_radius)*rad*c,rz*np.sign(math.cos(phi))*abs(math.cos(phi))**(2/power)")
source=source.replace('p=shell(theta,t);return unit((p-center)/np.array([rx*rx,ry*ry,rz*rz]))',"p=shell(theta,t);yr=ry if p[1]>=cy else rear_radius;q=(p-center)/np.array([rx,yr,rz]);h=math.hypot(q[0],q[1]);return unit([q[0]*h**(power-2)/rx,q[1]*h**(power-2)/yr,np.sign(q[2])*abs(q[2])**(power-1)/rz])")
source=source.replace('a=(x/rx)**2+((z-cz)/rz)**2;y=cy+ry*math.sqrt(max(.05,1-a))',"horizontal=max(0,1-abs((z-cz)/rz)**power)**(2/power);y=cy+ry*math.sqrt(max(.05,horizontal-(x/rx)**2))")
source=source.replace("['Revision']='HelmetDetailR1'","['Revision']='HelmetHairFitR1'")
source=source.replace("'independent native '+rig+' scalp envelope'","'independent native '+rig+' head and scalp-hair envelope'")
source=source.replace("    # Native head is available as a hidden author reference, excluded from export.","    for authored_part in A.OBJECTS:clean(authored_part)\n    # Native head is available as a hidden author reference, excluded from export.")
sys.path.insert(0,str(T))
from helmet_hair_mesh_clean import clean
namespace={'__name__':'helmet_hair_detail_author','__file__':str(T/'helmet1_author.py')}
namespace['clean']=clean
exec(compile(source,str(T/'helmet1_author.py'),'exec'),namespace)
args=sys.argv[sys.argv.index('--')+1:]
namespace['build'](args[0],len(args)>1 and args[1]=='HIGH')
