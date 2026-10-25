// Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp
// Replace SmoothedSpeed assignment in FProxy; preserve existing heading, stride and other weapons.
        const bool SprintHammerGait=D->BodyState.Family==TEXT("Tool")&&D->BodyState.Weapon==TEXT("warhammer")&&
            D->BodyState.ActionVariant==TEXT("WarhammerSprintLift");
        SmoothedSpeed=SprintHammerGait?D->Speed:FMath::FInterpTo(SmoothedSpeed,D->Speed,Dt,10.f);
