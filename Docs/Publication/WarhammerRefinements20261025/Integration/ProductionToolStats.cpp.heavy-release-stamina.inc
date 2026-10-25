// Source/FPSGAME/Production/ProductionToolStats.cpp
// After final clamped stamina calculation; reuse existing independent HeavyChargeSpeedBonus/HeavyChargeSeconds pipeline.
    R.HeavyReleaseStaminaCost=R.StaminaCost*(Blunt?BluntModifiers.HeavyReleaseStamina:1.);
