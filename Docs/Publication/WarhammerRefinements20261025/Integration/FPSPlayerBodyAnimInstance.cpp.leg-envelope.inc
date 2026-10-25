// Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp
// Requires existing hammer donor/leg ownership layer. Replace old sprint lift-only leg suppression, after HammerCarry suppression.
        const bool HammerSprintSlam=HasHammerAction&&NextSwordKey==TEXT("Warhammer.FullBody.SprintSlam");
        if(HammerSprintLift||HammerSprintSlam)
        {
            const float Progress=FPSBodyPoses::Progress(D->BodyState,D->Clock);
            // One envelope crosses the lift/release boundary. Start planting
            // during stride deceleration and finish at impact, without the old
            // 0 -> carry-weight jump on the first slam frame.
            const float Phase=HammerSprintLift?Progress:1.f+.35f*FMath::Clamp(
                Progress/FMath::Max(.001f,D->BodyState.ContactFraction),0.f,1.f);
            Controls.SwordLegWeight=FMath::SmoothStep(.65f,1.35f,Phase)*
                (1.f-D->CrouchAlpha)*(1.f-D->MotionAlpha)*(1.f-D->AirAlpha)*(1.f-SlideLayer.Weight);
        }
