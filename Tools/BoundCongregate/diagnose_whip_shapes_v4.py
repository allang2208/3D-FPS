"""Scoped motion-authoring comparisons for the user's whip diagnosis."""
import simulate_whip_v4 as sim
import numpy as np,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
cases=[(120,200,5.,.8,1.4,10,-9.81),(120,200,5.,.8,1.7,10,-9.81),(120,190,20.,1.,1.4,10,-9.81),(120,190,5.,1.,1.4,12,-9.81)]
fig,axes=plt.subplots(2,2,figsize=(16,12))
for index,((a,b,k,c,front,handle,gravity),ax) in enumerate(zip(cases,axes.flat)):
    theta=np.deg2rad(np.linspace(a,b,sim.N))
    sim.p=np.vstack([sim.rest_nodes[0],sim.rest_nodes[0]+np.cumsum(np.column_stack([np.cos(theta),np.zeros(sim.N),np.sin(theta)])*sim.lengths[:,None],axis=0)])
    poses,angles=sim.simulate(front=front,stiffness=k,bend_damping=c,handle=handle,gravity=gravity,damping=200.,body=True)
    np.savez_compressed(sim.OUT/f'candidate_{index}.npz',poses=poses,angles=angles,preload=sim.p)
    for i in [0,20,40,60,80,100,120,160]:ax.plot(poses[i,:,0],poses[i,:,2],label=str(round(i*.008,2)))
    ax.axis('equal');ax.grid();ax.legend();ax.set_title(str((a,b,k,c,front,handle,gravity)))
    print(json.dumps({'case':index,'tip_max_x':poses[:,-1,0].max(),'frame_max':int(np.argmax(poses[:,-1,0])),'driver_max':angles.max()}),flush=True)
fig.savefig(sim.OUT/'candidate_curves.png')
