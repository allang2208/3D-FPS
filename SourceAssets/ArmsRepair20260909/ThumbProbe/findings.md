# Read-only thumb fit review

The reviewed `anatomy` candidate visibly makes the thumb root worse in both reload frame 52 left hand and empty reload frame 75 right hand. Its palm-only edge results are insufficient to accept the candidate.

## Confirmed primary cause

`repair_arms_skinning.py` constructs the thumb normal using the proximal thumb axis crossed with wrist-to-thumb-root. This vector is not consistently oriented between the source and target rigs. Its dot product with the corresponding palm normal is -0.6728 in WRAD and +0.9319 in the target, on both hands. The resulting thumb fit differs from the palm fit by 142.82 degrees.

All basis determinants are +1: this is an axial orientation mismatch, not a negative-determinant reflection. Blending the palm and thumb rotations at equal weights gives singular values (1, 0.3188, 0.3188). Thus, even before runtime animation, this fit can squash two local dimensions to about 32 percent of their rotation-only baseline. It explains the triangular, folded thumb root in the after renders.

The minimal repair is to orient each thumb normal into the same hemisphere as its own anatomical palm normal before building the segment basis:

```python
if sn.dot(sb.col[2]) < 0:
    sn = -sn
if tn.dot(tb.col[2]) < 0:
    tn = -tn
```

Numerical evaluation of this correction reduces the palm/thumb rotation difference to 38.22 degrees; the equal-weight singular values become (1, 0.9449, 0.9449). This is diagnostic evidence, not a rendered acceptance of the corrected mesh. The owner should render the same two views before further weight changes.

## Secondary issues and boundaries

- Palm mapping sends the source thumb root to a point 2.08 target skeletal units from the target thumb root (about 2.08 cm with the target armature's 0.01 object scale). Independent palm and thumb fits therefore disagree in translation as well as orientation. If a residual web crease remains after the hemisphere correction, make the fit transition continuous around that landmark rather than further deleting articulation weights indiscriminately.
- Geometric retarget weights and runtime skin weights are being reused for different jobs. The current `proximal=max(proximal,smooth(.015,.16,palm))` fully transfers distal thumb influence to thumb 01 whenever the source wrist contribution reaches 0.16, irrespective of where the actual thumb joint lies. This is not proven to be the main defect. Inspect remaining thumb joint flexibility before changing this gate.
- The current region measurement requires source wrist weight >0.12 and a palm-forward band. Add a separate thumb region covering source thumb total weight >0.05, plus the wrist/thumb mixed web, so a destroyed thumb cannot hide behind an improved palm statistic.
- Target thumb parent chains are correct (`hand -> thumb_01 -> thumb_02 -> thumb_03`). Sampled idle, reload 52 and empty reload 75 local scales are approximately one. No evidence of parent-chain or animated-scale corruption was found.

Evidence: `thumb_fit_probe.json`, produced by `Tools/AssetPipeline/thumb_fit_probe.py`. The probe reads original and candidate files, saves only this report area, and does not save changes to a blend or Unreal asset.
