# SAN depletion penalty — 2026-10-03

At SAN ≤ 0, hunger and hydration consumption rates are multiplied by 2, and
each effective six-dimensional attribute is multiplied by 0.5. The attribute
penalty applies after base, equipment/enchantment, and passive/mastery attribute
bonuses. It composes multiplicatively with the existing infection penalty.
The fountain conservation blessing still multiplies consumption by 0.9;
SAN depletion plus blessing therefore consumes at 1.8× the ordinary base rate.

`FPSSurvivalComponent` keeps its existing authority-owned, 4 Hz integration.
Tick consumption is split at both blessing expiry and dungeon SAN depletion,
including frames that cross either boundary. Empty-resource timing continues
to gate the existing once-per-second 10%-of-current-maximum-health loss.
SAN depletion itself does not add a second health-loss mechanism.

`FFPSSurvivalState::AttributeMultiplier()` supplies the derived SAN multiplier.
`UColdSteelStatusModel::EffectiveAttributeMultiplier()` combines it with the
infection multiplier. Six attribute queries, HP/MP and stamina maxima, combat
and enhancement calculations, regeneration, and reload attribute contributions
use this same multiplier. Resource base terms and direct equipment resource
bonuses retain their existing formulas.

Depletion/recovery edges from survival ticking, monster SAN attacks, restored
resources, profile restore, and owner replication publish into the attached
pawn's model. Maxima refresh and current health, mana, and stamina clamp to any
lower maximum; recovering SAN restores maxima without granting free resources.
The existing coalesced profile autosave persists SAN, not permanently halved
base attributes. Loading SAN 0 reapplies the derived penalty once. Revival's
existing SAN 60 removes it.

The existing status HUD shows a persistent `sanityCollapse` debuff named
“精神崩溃” until SAN is positive. The status-bar warning explains the multiplier
when a starvation/dehydration warning is not already taking priority.
Existing status notifications occur on entry/exit only; no new tick, per-frame
JSON read, or repeated UI rebuild was added.

Native Editor/Game compilation is required. No editor UI, gameplay tests,
regression commands, screenshots, or acceptance renders are requested or run.
