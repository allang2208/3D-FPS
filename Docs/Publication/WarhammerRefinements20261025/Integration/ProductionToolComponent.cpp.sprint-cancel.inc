// Source/FPSGAME/Production/ProductionToolComponent.cpp
// Place first in CancelUse; preserve the remaining guard, timer and charge cleanup.
    if(Character.IsValid())
        if(auto* Move=Cast<UFPSCharacterMovementComponent>(Character->GetCharacterMovement()))
        {
            Move->CancelHammerSprintMove(Character->HasAuthority()&&!Character->IsLocallyControlled()?BluntServerAttackId:BluntAttackId);
            if(bBluntSprintAttack&&Character->IsLocallyControlled())Move->RestoreMeleeDashMomentum(false);
        }
