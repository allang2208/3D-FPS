    else if(bInspecting)
    {
        namespace Feel=RuneSwordInspectFeel;
        const float From=Elapsed, Rate=LightningHaste::ActionSpeed(GetOwner());
        Elapsed=FMath::Min(End,Elapsed+Delta*Rate);SamplePose(Elapsed);
        if(Elapsed<Feel::CatchAt)
        {
            InspectAir.PlayBeat(this,From,Elapsed,Feel::TurnPeak,.60f,Rate);
            InspectAir.PlayBeat(this,From,Elapsed,Feel::ReturnPeak,.38f,Rate);
        }
        if(From<Feel::CatchAt&&Elapsed>=Feel::CatchAt)
        {
            InspectAir.Stop();
            if(InspectCatchSound)UGameplayStatics::PlaySound2D(this,InspectCatchSound,RuneSwordInspectFeel::CatchVolume,RuneSwordInspectFeel::CatchPitch);
        }
        if(Elapsed>=End)
        {
            InspectAir.Stop();
            bInspecting=false;
            const bool GroundStride=Character->GetCharacterMovement()->IsMovingOnGround()
                && !Character->bWeaponJumpAirborne && !Character->IsSliding();
            SetClip(GroundStride&&Character->GetVelocity().SizeSquared2D()>400.f?TEXT("Walk"):TEXT("Idle"),true);
        }
    }
