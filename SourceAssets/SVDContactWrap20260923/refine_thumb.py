"""Refine thumb opposition while locking the selected palm and four fingers."""
from pathlib import Path
import json
O = Path(__file__).parent
ns = {'__file__': str(O / 'fit_selected.py')}
exec((O / 'fit_selected.py').read_text().split('def penalty')[0], ns)
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R

fit = json.loads((O / 'grasp_selected.json').read_text())
x = np.array(fit['parameters'])
posed, shell, pads = ns['posed'], ns['shell'], ns['pads']
thumb = {n: ids for n, ids in pads.items() if n.startswith('thumb')}

def apply(t):
    trial = x.copy(); trial[22:] = t
    return posed(trial)

def objective(t):
    _, _, bones, v = apply(t)
    value = .005 * np.sum((t-x[22:])**2)
    for n, ids in thumb.items():
        distance = shell.clearance(v[ids])
        value += np.mean((distance-.3)**2) * (8 if '_02_' in n else 6)
        c = v[ids].mean(0)
        support = np.array([np.interp(c[2], shell.z, shell.support[:,j]) for j in range(48)])
        signed = c[:2]@shell.N.T-support
        w = np.exp((signed-signed.max())/.002); normal = w@shell.N
        normal /= np.linalg.norm(normal)
        value += 90*(1+np.dot(bones[n][:2,1],normal))**2
    return value

affected = np.flatnonzero(np.array([sum(w.get(n,0) for n in ns['names'] if n.startswith('thumb'))
                                  for w in ns['d']['weights']]) > 0)
faces = ns['faces'][np.isin(ns['faces'],affected).any(1)]
edges = ns['edges'][np.isin(ns['edges'],affected).any(1)]
def constraints(t):
    v = apply(t)[3]
    samples = np.concatenate([v[affected],v[edges].mean(1),v[faces].mean(1)])
    return np.r_[shell.clearance(samples)+.55,ns['semantic'](v),4.0-shell.clearance(v[ns['palm']]).mean()]

before_objective = float(objective(x[22:]))
result = minimize(objective,x[22:],method='SLSQP',bounds=ns['bounds'][22:],
                  constraints=[{'type':'ineq','fun':constraints}],options={'maxiter':140,'ftol':.001})
print('SVD_THUMB_REFINEMENT',result.success,result.message,objective(x[22:]),result.fun,flush=True)
if not result.success or constraints(result.x).min() < -.01:
    raise RuntimeError('Refinement is not feasible; existing selected grip retained')
H,Q,p,v = apply(result.x)
x[22:] = result.x
def wxyz(m):
    q=R.from_matrix(m).as_quat();return [float(q[3]),*map(float,q[:3])]
fit['parameters'] = x.tolist()
fit['finger_basis'].update({n:wxyz(Q[n]) for n in Q if n.startswith('thumb')})
opened = {'thumb_01_l':Q['thumb_01_l']@R.from_euler('x',-8,degrees=True).as_matrix(),
          'thumb_02_l':ns['rz'](max(12,x[25]-20)), 'thumb_03_l':ns['rz'](max(6,x[26]-12))}
fit['open_basis'].update({n:wxyz(q) for n,q in opened.items()})
fit['production_clearance_mm'] = float(shell.clearance(ns['sampled_surface'](v,True)).min())
fit['pad_means_mm'] = {n:float(shell.clearance(v[ids]).mean()) for n,ids in pads.items()}
fit['palm_mean_mm'] = float(shell.clearance(v[ns['palm']]).mean())
fit['thumb_refinement'] = {'hand_and_four_finger_bones_locked':True,'objective_before':before_objective,'objective_after':float(result.fun)}
(O/'grasp_refined.json').write_text(json.dumps(fit,indent=2))
print('SVD_REFINED_PADS',fit['pad_means_mm'],'palm',fit['palm_mean_mm'],flush=True)
