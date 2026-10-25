"""Reproduce the current lower-body blend arithmetic; this is not pose evaluation."""
import json
from pathlib import Path

out=Path(__file__).resolve().parent
rows=[]
dt=1/60
for rate in (1.,1.5,2.):
    speed=600.
    ownership=0.
    lift=.25/rate
    last_lift=None
    for frame in range(31):
        age=frame*dt
        speed*=1-dt*10
        if age<lift:
            last_lift={'age':age,'reported_progress':age/.25,'leg_weight':0.,'smoothed_gait_speed':speed}
        else:
            ownership=min(1.,ownership+dt*12.5)
            carry=1-min(speed/120,1.)
            leg_weight=carry+(1-carry)*ownership
            rows.append({'haste_rate':rate,'real_lift_seconds':lift,'last_lift':last_lift,
                         'first_slam':{'age':age,'smoothed_gait_speed':speed,'leg_weight':leg_weight}})
            break
report={
    'scope':'Current source and configuration review; blend arithmetic at 60 Hz, initial sprint speed 600 cm/s. Not native graph, skin, collision or multiplayer acceptance.',
    'findings':[
        'Ground sprint attack sweeps capsule position without adding locomotion Velocity; body animation Speed still reads Character.GetVelocity().',
        'SprintLift forces attack leg weight to zero; SprintSlam restores carry/attack weight immediately, without matching the current planted foot.',
        'SprintLift body state uses Elapsed / 0.25, but executor finishes lift at 0.25 / HasteActionRate. Donor lift also uses a fixed 0.20-second clock.',
        'Both Jason and Kaitlin have compatible sprint lift/slam role mappings; neither mapping alone resolves the movement/leg clock mismatch.'
    ],
    'arithmetic':rows,
    'native_graph_capture':{'completed':False,'reason':'Shared project build blocked by concurrently changing OffhandKukriStrike.cpp; existing DLL does not contain the new diagnostic command.'},
    'gameplay_changes_made':False,
    'assets_changed':False
}
(out/'source-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for r in rows:
    print(f"rate={r['haste_rate']}: lift final progress={r['last_lift']['reported_progress']:.3f}, attack leg weight 0 -> {r['first_slam']['leg_weight']:.3f}")
