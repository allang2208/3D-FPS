// Source/FPSGAME/Production/ProductionToolComponent.cpp
// Replace the initial presentation-only TickComponent early returns; preserve subsequent local presentation.
    InitializeLocalTool();TickRunebound(Delta);TickAuthorityBluntCharge();
    if(Character.IsValid()&&Character->HasAuthority()&&!Character->IsLocallyControlled()&&bBluntServerSprintAttack)
    {
        const double Now=GetWorld()->GetTimeSeconds();
        if(Now<BluntServerReadyAt)UpdateBluntSprintAnchor(Now<BluntServerSprintContactAt);
        else bBluntServerSprintAttack=false;
    }
    if(Character.IsValid()&&Character->HasAuthority()&&!Character->IsLocallyControlled())
    {
        if(bBluntWhirlwind)TickBluntWhirlwind(Delta);
        else if(bBluntUppercut)TickBluntUppercut(Delta);
        else AdvanceBluntSprintReadiness(Delta);
    }
    if(!Pivot){UpdateRuneboundPresentation(Delta,!RuneboundInstance.IsEmpty());UpdateStormDriveLightning(Delta);return;}
    if(!Character.IsValid()||!Character->IsLocallyControlled())
    {UpdateRuneboundPresentation(Delta,!RuneboundInstance.IsEmpty());UpdateStormDriveLightning(Delta);return;}
