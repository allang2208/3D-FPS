// Integration reference only: preserve shared host declarations and prerequisites.

// Source line 65
bool UOffhandKukriComponent::CanQuickCombat() const
{
    const auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Pair=P?P->FindComponentByClass<UStaffOffhandMeleeComponent>():nullptr;
    if(Pair&&Pair->IsEquipped())
        return Pair->CanQuickCombat()&&!bQuickCombat&&!bUppercut&&P->CanStartQuickCombatPriority();
    // Presentation is allowed to yield to reload, inspection and consumables.
    // F first interrupts those actions; ADS, sprint and a fading stance cannot
    // choose a different weapon or require the knife hand to be visible already.
    return bEquipped&&P&&P->HasInventoryWeapon()&&P->IsPistolWeapon()&&!P->HasOffhandPistol()&&
        Arms&&Arms->GetSkeletalMeshAsset()&&Blade&&Blade->GetStaticMesh()&&
        (!bDrawHatchet||UsesNativeAxe())&&!bQuickCombat&&!bUppercut&&P->CanStartQuickCombatPriority();
}

// Source line 79
float UOffhandKukriComponent::GetQuickCombatLength() const
{return bHatchetQuickCombat?OffhandAxeQuickMotion::Length:OffhandKukriStrike::Length;}

// Source line 82
float UOffhandKukriComponent::GetQuickCombatContact() const
{return bHatchetQuickCombat?OffhandAxeQuickMotion::ContactAt:OffhandKukriStrike::Contacts[0];}

// Source line 85
float UOffhandKukriComponent::GetQuickCombatRelease() const
{return bHatchetQuickCombat?OffhandAxeQuickMotion::ReleaseAt:.32f;}

// Source line 88
bool UOffhandKukriComponent::BeginQuickCombat()
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    if(!P||!CanQuickCombat())return false;
    auto* StaffPair=P->FindComponentByClass<UStaffOffhandMeleeComponent>();
    if(StaffPair&&!StaffPair->IsEquipped())StaffPair=nullptr;
    if(StaffPair)StaffPair->CaptureActionEntry();
    // Equipment stows, casts and the pistol's own actions yield to F (priority interrupt).
    P->InterruptActionsForPriority(false);
    if(StaffPair?!StaffPair->OwnsLeftHand():!OwnsLeftHand())return false;
    auto* Profile=Model.Get();
    const auto State=Profile?Profile->Snapshot():FColdSteelProfile();
    const auto* Item=Profile?Profile->Equipped(State.ActiveWeaponSlot==6?8:11):nullptr;
    if(!Item||!(StaffPair?ColdSteelInventory::IsOneHandedBlade(*Item):IsOffhandKukri(*Item))||Profile->ActiveProductionTool())return false;
    const float Rate=FMath::Max(.05f,LightningHaste::ActionSpeed(P));
    const bool Hatchet=ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("hatchet");
    if(Hatchet&&!(StaffPair?StaffPair->HasNativeChop():UsesNativeAxe()))return false;
    const float Length=Hatchet?OffhandAxeQuickMotion::Length:OffhandKukriStrike::Length;
    const bool SwitchStaffRig=StaffPair&&!Hatchet;
    const float Total=Length+(SwitchStaffRig?StaffOffhandQuickMotion::Entry+StaffOffhandQuickMotion::Return:0.f);
    // The skill cost is paid once; F stays reserved through the selected action's recovery.
    if(!Profile->CommitQuickCombatCast(Total/Rate))return false;
    QuickActionRate=Rate;
    QuickCast=Profile->QuickCombatStats();
    // 200 % of the blade's physical panel plus the quick-melee skill's own damage; the authority
    // recomputes the same number from the declared off-hand item (OffhandKukriThrust.h).
    StrikeDamage=OffhandKukriThrust::Damage(*Item,Profile);
    QuickShot=ColdSteelSkills::Snapshot(P,Item);
    CaptureContactEdge(*Item);
    QuickShot.bRifle=false;QuickShot.bPistol=false;QuickShot.WeakpointPercent=0;
    // A blade thrust: blade toughness conversion (the authority uses the same form for this pair).
    QuickShot.AttackForm=EMonsterAttackForm::Blade;QuickShot.bMeleeStrike=true;
    QuickShot.AttackMeta|=0x80;
    QuickShot.ToughnessDamageMultiplier=QuickCast.ToughnessMultiplier;
    SwingSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("swing_sound")));
    HitSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("hit_sound")));
    // A downward chop uses the equipped axe swing, without the thrust-only stab layer.
    WhooshSound=Hatchet?nullptr:LoadObject<USoundBase>(nullptr,KukriRhythm::StabWhoosh);
    ThudSounds.Reset();
    for(const TCHAR* Path:KukriRhythm::StabThud)if(auto* Thud=LoadObject<USoundBase>(nullptr,Path))ThudSounds.Add(Thud);
    bQuickCombat=true;bImpactConfirmed=bWallHit=bQuickKillPending=false;
    bStaffQuickCombat=StaffPair!=nullptr;
    bHatchetQuickCombat=Hatchet;
    if(Hatchet){StopUpperRift();bUpperRiftStarted=false;PrepareQuickRift();}
    QuickEndTime=Length+(SwitchStaffRig?StaffOffhandQuickMotion::Return:0.f);
    QuickTotalDuration=Total;
    if(auto* Pendant=P->FindComponentByClass<UKukriDecisiveComponent>())Pendant->BeginLocal(QuickShot,true);
    // The accepted strike owns the hands immediately, including the first frame
    // after reload, consumable stow or draw recovery. Discard the interrupted
    // stance-entry and native reload-arm transitions before sampling either rig.
    EntryAge=-1.f;bWasPresenting=true;NativeReloadEnteredAt=-1.;
    if(Hatchet){DrawTime=-1.f;bAwaitingDraw=false;}
    RightWeight=1.f;AimWeight=0.f;bHold=false;
    if(!StaffPair&&Arms)
        QuickNativePistolHand=OffhandKukriPose::HipFraming.InverseTransformPosition(Arms->RightHandInCamera);
    QuickElapsed=SwitchStaffRig?-StaffOffhandQuickMotion::Entry:0.f;
    if(Hatchet&&!StaffPair)
    {
        AxeArms->CaptureLeftEntry(OffhandAxeQuickMotion::Entry,-OffhandAxeQuickMotion::EntryLead/OffhandAxeQuickMotion::Entry);
        AxeArms->SetRelativeLocation(FVector::ZeroVector);
        AxeIdleAge=0.f;
    }
    if(StaffPair)StaffPair->BeginActionPresentation(false,Hatchet);
    QuickHitStop=0.f;QuickImpactAge=-1.f;QuickStrikeAge=-1.f;QuickImpactKick=0.f;
    QuickSwingsPlayed=QuickContactsDone=QuickMasteryHits=0;QuickHitActors.Reset();
    P->ExitSprintForWeapon();
    // The interrupt clears ADS/fire input and returns the gun state to Idle.
    // Release the previous reload/fire/inspect clip for SingleNode rigs too.
    P->ResumeWeaponPose();
    Profile->TrainQuickCombat(Profile->QuickCombatDefinition().UseExperience);
    BeginStrikeFocus();
    return true;
}

// Source line 162
void UOffhandKukriComponent::AdvanceQuickCombat(float Delta)
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    auto* StaffPair=bStaffQuickCombat&&P?P->FindComponentByClass<UStaffOffhandMeleeComponent>():nullptr;
    if(bStaffQuickCombat&&(!StaffPair||!StaffPair->OwnsLeftHand()||
        AFPSGAMEPlayerController::BlocksActionContinuation(Cast<APlayerController>(P->GetController()))))
    {CancelQuickCombat();return;}
    // Keep the accepted action clock through haste expiry and recovery. The
    // authority window and third-person timeline use this same committed rate.
    const float Rate=QuickActionRate;
    const float SwingAt=bHatchetQuickCombat?OffhandAxeQuickMotion::SwingAt:OffhandKukriStrike::Swings[0];
    const float ContactAt=GetQuickCombatContact();
    // The impact rattle and the contact accent are real time; the hit-stop freezes the author clock.
    if(QuickImpactAge>=0.f)QuickImpactAge+=Delta;
    if(QuickStrikeAge>=0.f)QuickStrikeAge+=Delta;
    float Remaining=Delta;
    int32 Guard=0;
    while(Remaining>UE_SMALL_NUMBER&&bQuickCombat&&++Guard<64)
    {
        if(QuickHitStop>0.f)
        {
            const float Pause=FMath::Min(Remaining,QuickHitStop);
            QuickHitStop-=Pause;Remaining-=Pause;
            continue;
        }
        float Step=FMath::Min(Remaining*Rate,1.f/120.f);
        if(QuickSwingsPlayed<OffhandKukriStrike::SlashCount&&
            QuickElapsed<SwingAt-UE_KINDA_SMALL_NUMBER)
            Step=FMath::Min(Step,SwingAt-QuickElapsed);
        if(QuickContactsDone<OffhandKukriStrike::SlashCount&&
            QuickElapsed<ContactAt-UE_KINDA_SMALL_NUMBER)
            Step=FMath::Min(Step,ContactAt-QuickElapsed);
        if(QuickElapsed<QuickEndTime-UE_KINDA_SMALL_NUMBER)
            Step=FMath::Min(Step,QuickEndTime-QuickElapsed);
        Step=FMath::Max(Step,1e-4f);
        const float Before=QuickElapsed;
        QuickElapsed=FMath::Min(QuickEndTime,QuickElapsed+Step);
        if(StaffPair)StaffPair->SetActionTime(QuickElapsed);
        Remaining=FMath::Max(0.f,Remaining-(QuickElapsed-Before)/Rate);
        while(QuickSwingsPlayed<OffhandKukriStrike::SlashCount&&
            QuickElapsed>=SwingAt-UE_KINDA_SMALL_NUMBER)
        {
            // The stab whoosh under the swing: the drive-in is the fastest move of the action.
            if(WhooshSound)UGameplayStatics::PlaySound2D(this,WhooshSound,KukriRhythm::StabWhooshVolume,1.05f);
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,
                KukriQuickRhythm::SwingVolume,bHatchetQuickCombat?HatchetChopRhythm::Swing.SwingPitch:
                    KukriQuickRhythm::SwingPitch*(1.f+.06f*QuickSwingsPlayed));
            ++QuickSwingsPlayed;
        }
        while(QuickContactsDone<OffhandKukriStrike::SlashCount&&
            QuickElapsed>=ContactAt-UE_KINDA_SMALL_NUMBER)
        {
            ++QuickContactsDone;bImpactConfirmed=false;bWallHit=false;
            QuickContact();
        }
        if(QuickElapsed>=QuickEndTime-UE_KINDA_SMALL_NUMBER)
        {
            bQuickCombat=false;QuickHitActors.Reset();
            FinishQuickCombat();
        }
    }
    if(!bQuickCombat)return;
    if(Model.IsValid())
        Model->UpdateQuickCombatAction((QuickEndTime-QuickElapsed)/Rate+QuickHitStop,QuickTotalDuration/Rate);
    UpdateStrikeFocus(bHatchetQuickCombat?.75f*FMath::SmoothStep(.30f,.35f,QuickElapsed)*(1.f-FMath::SmoothStep(.40f,.59f,QuickElapsed)):
        OffhandKukriStrike::SampleCurve(OffhandKukriStrike::CameraBlur,QuickElapsed));
}

// Source line 359
void UOffhandKukriComponent::FinishQuickCombat()
{
    if(bStaffQuickCombat)
        if(auto* Pair=GetOwner()->FindComponentByClass<UStaffOffhandMeleeComponent>())
            Pair->EndActionPresentation(QuickElapsed<QuickEndTime-UE_KINDA_SMALL_NUMBER);
    if(bHatchetQuickCombat)
    {
        const bool Interrupted=QuickElapsed<QuickEndTime-UE_KINDA_SMALL_NUMBER;
        if(!bStaffQuickCombat&&AxeArms)
        {
            if(Interrupted)AxeArms->CaptureLeftEntry(.12f);
            else AxeArms->ClearEntry();
        }
        if(Interrupted)StopUpperRift();
    }
    bStaffQuickCombat=false;bHatchetQuickCombat=false;
    auto* Profile=Model.Get();
    if(Profile)
    {
        Profile->FinishQuickCombatCast();
        if(bQuickKillPending)Profile->TrainQuickCombat(Profile->QuickCombatDefinition().KillExperience);
    }
    bQuickKillPending=false;
    EndStrikeFocus();
    UpdateStrikeFocus(0.f);
    if(Arms)Arms->StrikeTime=-1.f;
}

// Source line 387
void UOffhandKukriComponent::CancelQuickCombat()
{
    if(!bQuickCombat)return;
    bQuickCombat=false;QuickHitActors.Reset();
    FinishQuickCombat();
}

// Source line 394
bool UOffhandKukriComponent::GetStrikeFraming(FTransform& Out) const
{
    FVector Wrist,Shoulder,Pole;FQuat Hand;
    if(bQuickCombat)
    {
        Out=OffhandQuickClearance::PistolFrame(OffhandKukriPose::HipFraming,
            QuickElapsed/GetQuickCombatLength(),bHatchetQuickCombat);
        return true;
    }
    if(bUppercut)
    {
        OffhandKukriUpper::SamplePose(UppercutElapsed,Wrist,Hand,Shoulder,Pole,Out);
        return true;
    }
    return false;
}

// Source line 411
void UOffhandKukriComponent::GetCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const
{
    if(bUppercut)
    {
        // The stage-3 reference curve mirrored: a left-hand cut carries the view the other way (its wind-up gather too).
        KukriRhythm::SwingCamera(KukriRhythm::UppercutStage,UppercutElapsed,Rotation,FovDelta,&Location);
        Rotation.Yaw=-Rotation.Yaw;Rotation.Roll=-Rotation.Roll;Location.Y=-Location.Y;
        if(UppercutImpactAge>=0.f)
        {
            const float Shake=KukriRhythm::HitShake(UppercutImpactAge)*UppercutImpactKick;
            Rotation+=FRotator(Shake*.9f,Shake*.35f,Shake*1.4f*-KukriRhythm::Swings[KukriRhythm::UppercutStage].HitRoll);
            Location+=FVector(0.f,Shake*.25f,Shake*.15f);
            FovDelta+=KukriRhythm::ImpactEnvelope(UppercutImpactAge)*UppercutImpactKick*1.4f;
        }
        if(UppercutStrikeAge>=0.f)
        {
            // Real-time contact accent at the impact moment, mirrored with the cut.
            const auto& K=KukriRhythm::Strikes[KukriRhythm::UppercutStage];
            const float E=KukriRhythm::StrikeEnvelope(UppercutStrikeAge);
            Rotation.Pitch+=K.AccentPitch*E;Rotation.Yaw-=K.AccentYaw*E;
            Location.X+=K.AccentPushCM*E;FovDelta+=K.AccentFov*E;
        }
        return;
    }
    if(!bQuickCombat)return;
    // Same author clock as the arm keys: the hit-stop freezes the curve with the pose.
    float BlurStrength=0.f;
    if(bHatchetQuickCombat)
    {
        HatchetDualChopRhythm::Camera(QuickElapsed*OffhandAxeQuickMotion::ClipRate,Rotation,FovDelta,&Location);
    }
    else
    {
        OffhandKukriStrike::Camera(QuickElapsed,Rotation,FovDelta,BlurStrength);
        Rotation*=ThrustCameraScale;FovDelta*=ThrustCameraScale;
        Location=FVector::ZeroVector;
    }
    if(QuickImpactAge>=0.f)
    {
        const float Shake=KukriRhythm::HitShake(QuickImpactAge)*QuickImpactKick;
        Rotation+=FRotator(Shake*.9f,Shake*.35f,Shake*1.4f*KukriQuickRhythm::HitRoll);
        Location+=FVector(0.f,Shake*.25f,Shake*.15f);
        FovDelta+=KukriRhythm::ImpactEnvelope(QuickImpactAge)*QuickImpactKick*KukriQuickRhythm::HitFov;
    }
    if(QuickStrikeAge>=0.f)
    {
        if(bHatchetQuickCombat)
        {
            const auto& K=HatchetChopRhythm::Strike;
            const float E=KukriRhythm::StrikeEnvelope(QuickStrikeAge);
            Rotation.Pitch+=K.AccentPitch*E;Rotation.Yaw-=K.AccentYaw*E;
            Location.X+=K.AccentPushCM*E;FovDelta+=K.AccentFov*E;
            return;
        }
        // Real-time contact accent on the contact frame: the view nods into the thrust, pushes forward
        // and widens, plus a share of the shared quick-melee impulse.
        const float E=KukriRhythm::StrikeEnvelope(QuickStrikeAge)*ThrustAccentScale;
        Rotation.Pitch+=KukriQuickRhythm::AccentPitch*E;Location.X+=KukriQuickRhythm::AccentPushCM*E;
        FovDelta+=KukriQuickRhythm::AccentFov*E;
        FVector ImpulseLocation=FVector::ZeroVector;FRotator ImpulseRotation=FRotator::ZeroRotator;
        QuickCombatImpactShake::Add(QuickStrikeAge,ImpulseLocation,ImpulseRotation);
        Location+=ImpulseLocation*ThrustImpulseScale;
        Rotation+=ImpulseRotation*ThrustImpulseScale;
    }
}
