void UFPSPlayerBodyComponent::SampleKukriState(const UKukriWeaponComponent& K,FFPSBodyState& S,float Now) const
{
    S.Family=TEXT("Kukri");S.Weapon=FName(*Character->ActiveInventoryWeaponDefinition);
    // The lone off-hand blade is the weapon (the inventory weapon identity is the empty main hand's): name it like the
    // server's sample does (SampleRemoteAuthorityState, ActiveKukriWeapon), or observers drop every action as a mismatch.
    if(K.IsLoneOffhand())
        if(const auto* Model=Character->GetGameInstance()?Character->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr)
            if(const auto* Item=Model->ActiveKukriWeapon())S.Weapon=FName(*Item->Definition);
    S.Action=EFPSBodyAction::None;S.ActionVariant=K.CurrentClip;
    const float SkillRate=FMath::Max(.05f,LightningHaste::ActionSpeed(Character.Get()));
    // PressStop is the saved impact-envelope length, not a remaining pause.
    const bool Paused=K.HitStop>0.f||K.WhirlwindPause>0.f;
    const auto Timed=[&](EFPSBodyAction Action,float Length,float Rate)
    {
        Length=FMath::Max(.01f,Length);
        S.Action=Action;S.bHasActionProgress=true;
        S.ActionDuration=Length/FMath::Max(.01f,Rate);
        S.ActionStartedAt=Now-K.Elapsed/FMath::Max(.01f,Rate);
        S.ActionProgress=FMath::Clamp(K.Elapsed/Length,0.f,1.f);
        S.ActionProgressRate=Paused?0.f:Rate/Length;
    };
    const float Length=K.CurrentAnimation?K.CurrentAnimation->GetPlayLength():1.f;
    if(K.bWhirlwind)
    {
        if(K.IsDual())S.ActionVariant=TEXT("DualWhirlwind");
        const auto& T=K.WhirlwindTuning;
        const float End=T.ReadySeconds+T.SpinSeconds+T.RecoverSeconds;
        Timed(EFPSBodyAction::Whirlwind,End,SkillRate);
        S.ContactFraction=T.ReadySeconds/End;S.ReleaseFraction=(T.ReadySeconds+T.SpinSeconds)/End;
        S.WhirlwindTurns=T.TurnDegrees/360.f;
    }
    else if(K.bHeavyCharging)
    {
        Timed(EFPSBodyAction::Charge,KukriHeavyRhythm::ChargeLength,
            KukriHeavyRhythm::ChargeLength/FMath::Max(.01f,K.HeavyRequiredSeconds));
        // AdvanceHeavyCharge waits for a tap, raises at martial speed, then
        // stretches only the loading phase. Observers need that same rate.
        const float Delay=K.bHeavyAuto?0.f:KukriHeavyRhythm::TapSeconds;
        const float Held=GetWorld()?float(GetWorld()->GetTimeSeconds()-K.HeavyChargeStartedAt):0.f;
        const float Rate=Held<Delay||K.Elapsed>=KukriHeavyRhythm::ChargeLength?0.f:
            K.Elapsed<KukriHeavyRhythm::RaiseEnd?SkillRate:
            (KukriHeavyRhythm::ChargeLength-KukriHeavyRhythm::RaiseEnd)/
                FMath::Max(.2f,K.HeavyRequiredSeconds-Delay-KukriHeavyRhythm::RaiseEnd/SkillRate);
        S.ActionProgressRate=Rate/KukriHeavyRhythm::ChargeLength;
    }
    else if(K.bHeavyAttack&&K.bFalconHeavy)
    {
        Timed(EFPSBodyAction::HeavyStrike,Length,K.FalconReleaseRate);
        S.ActionDuration=SwiftFalconHeavy::PlaybackSeconds(Length,K.FalconReleaseRate);
        S.ActionStartedAt=Now-SwiftFalconHeavy::PlaybackSeconds(K.Elapsed,K.FalconReleaseRate);
        S.ActionProgressRate=Paused?0.f:SwiftFalconHeavy::PlaybackRate(K.Elapsed,K.FalconReleaseRate)/Length;
        S.ContactFraction=(K.Shot.MeleeDamagePhase?SwiftFalconHeavy::PullAt:SwiftFalconHeavy::ChopAt)/Length;
        S.ReleaseFraction=(K.Shot.MeleeDamagePhase?SwiftFalconHeavy::PullOut:SwiftFalconHeavy::ChopOut)/Length;
    }
    else if(K.bDashAttack)
    {
        // The pair's first-person chop (DualSprintAttack) is the same sprint attack for the body and observers; the body
        // picks its own dual variant from the matching off-hand (FPSBodyKukriMotion::DualClip).
        S.ActionVariant=TEXT("SprintAttack");
        Timed(EFPSBodyAction::HeavyStrike,Length,SkillRate);
        S.ContactFraction=KukriDashRhythm::ContactStart/Length;S.ReleaseFraction=KukriDashRhythm::ContactEnd/Length;
    }
    else if(K.bQuickCombat)
    {
        Timed(EFPSBodyAction::Pommel,Length,SkillRate);
        S.ContactFraction=KukriQuickRhythm::ContactAt/Length;
        S.ReleaseFraction=FMath::Min(.95f,S.ContactFraction+.12f);
    }
    else if(K.bAttacking||K.bUppercut||K.bHeavyAttack)
    {
        const int32 Stage=FMath::Clamp(K.Stage,0,KukriRhythm::StageCount-1);
        const auto& Swing=KukriRhythm::Swings[Stage];
        // The dual kukri's clips run on their own clocks (the owner's AdvanceAttack / AdvanceHeavy): the two-blade
        // sweeps on DualSweepTempo, the double thrust untimed, the X on DualHeavyTempo -- remote bodies follow the same.
        const bool DualThrust=K.bAttacking&&K.bDualThrust, DualHeavy=K.bHeavyAttack&&K.bDualHeavy;
        const float Tempo=DualHeavy?KukriRhythm::SampleTempo(KukriRhythm::DualHeavyTempo,K.Elapsed):DualThrust?1.f:
            K.bAttacking&&K.bDualSweep?KukriRhythm::DualSweepTempo(Stage,K.Elapsed):KukriRhythm::StageTempo(Stage,K.Elapsed);
        const float Rate=(K.bUppercut||K.bHeavyAttack?SkillRate:K.PlayRate)*Tempo;
        Timed(K.bUppercut||K.bHeavyAttack?EFPSBodyAction::HeavyStrike:
            Stage==2?EFPSBodyAction::Thrust:EFPSBodyAction::Strike,Length,Rate);
        S.ContactFraction=K.StrikeProfile().At/Length;
        S.ReleaseFraction=(DualThrust?KukriRhythm::DualThrustContactEnd:DualHeavy?KukriRhythm::DualHeavyContactEnd:
            Swing.ContactEnd+(K.bAttacking&&K.bDualSweep?KukriRhythm::DualSweepOffset(Stage):0.f))/Length;
    }
    else if(K.bEquipping)Timed(EFPSBodyAction::Equip,Length,SkillRate);
}
