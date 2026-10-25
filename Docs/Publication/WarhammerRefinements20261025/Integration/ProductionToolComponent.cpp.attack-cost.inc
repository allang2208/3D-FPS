// Source/FPSGAME/Production/ProductionToolComponent.cpp
// In BeginUse after ApplyToolStats, choose the existing standalone SpendStamina amount.
// Preserve the multiplayer authority transaction and existing insufficient-stamina return.
const double AttackCost=Kind==TEXT("warhammer")&&bBluntHeavy&&!bBluntSprintAttack?
    ToolStats.HeavyReleaseStaminaCost:ToolStats.StaminaCost;
// Existing NM_Standalone SpendStamina call consumes AttackCost instead of ToolStats.StaminaCost.
