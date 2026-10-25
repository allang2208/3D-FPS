// Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp
// Replace respective assignment first lines only, retaining following JogTarget ternary line.
        const float JogTarget=(D->BodyState.bSprinting||SprintHammerGait)&&!D->BodyState.bAiming?
        const float PlayRate=FMath::Clamp(SmoothedSpeed/SourceSpeed,0.f,SprintHammerGait?4.f:FMath::Lerp(1.8f,1.35f,Pace.Alpha));
