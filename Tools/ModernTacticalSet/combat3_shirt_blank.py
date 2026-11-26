"""Build the native continuous shirt blank before physical fold settling."""
from pathlib import Path
T=Path('D:/FPS3D/FPSGAME/Tools/ModernTacticalSet')
code=(T/'combat2_world_shirt.py').read_text(encoding='utf-8').replace('CombatShirtR2','CombatShirtR3')
code=code.replace('fold=(.36*np.sin(longitudinal*1.18+.75*np.cos(theta))+.12*np.sin(longitudinal*.62-theta*2))*elbow','fold=np.zeros_like(longitudinal)')
code=code.replace('fold+=.22*np.sin(wrist_dist*1.7+.55*np.sin(theta*2))*np.exp(-((wrist_dist-6)/3.1)**2)','fold+=0')
code=code.replace('ease=.76+.18*np.cos(theta)**2-.48*cuff+fold','ease=1.05+.12*np.cos(theta)**2-.70*cuff')
code=code.replace('clearance+=(1-arm)*(.13*np.sin((p[:,2]-98)*1.2+abs(p[:,0])*.3)*hem*side)','clearance+=(1-arm)*0')
exec(compile(code,str(T/'combat2_world_shirt.py'),'exec'),{'__file__':str(T/'combat2_world_shirt.py'),'__name__':'__main__'})
