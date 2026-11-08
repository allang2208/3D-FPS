// Integration reference only: preserve shared host declarations and prerequisites.

// Source line 14
bool UStaffOffhandMeleeComponent::CanQuickCombat() const
{
    return CanQuickCombat(false);
}

// Source line 26
void UStaffOffhandMeleeComponent::CaptureActionEntry()
{
    if(const auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>())
    {
        ActionStaffEntry=Staff->ActionPoseInCamera();
        bActionEntryCharge=!Staff->IsPrimaryAttacking()&&StaffChargeFlow::UsesKeys(ActionStaffEntry);
    }
    // Capture before the priority interrupt cancels consumables/casts. Blend the live left pose while lowering it.
    if(Arms)Arms->CaptureEntry(StaffOffhandQuickMotion::Entry*.5f);
}

// Source line 37
void UStaffOffhandMeleeComponent::BeginActionPresentation(bool Uppercut,bool bUseHatchetChop)
{
    bUpperPresentation=Uppercut;
    bHatchetChopPresentation=!Uppercut&&bUseHatchetChop;
    ActionLength=Uppercut?OffhandKukriUpper::Length:bHatchetChopPresentation?OffhandAxeQuickMotion::Length:OffhandKukriStrike::Length;
    bActionPresentation=true;ActionReturnAge=-1.f;ActionTime=-StaffOffhandQuickMotion::Entry;
    bQuickSupportReturn=false;
    bWasPresenting=true;
    if(bHatchetChopPresentation)
    {
        ActionTime=0.f;
        Arms->ClearEntry();
        Arms->CaptureLeftEntry(.08f);
        Arms->bMirrorRightToLeft=false;
    }
}

// Source line 54
bool UStaffOffhandMeleeComponent::UsesStrikeRig() const
{
    if(bHatchetChopPresentation)return false;
    if(ActionReturnAge>=0.f)return bReturnFromStrike&&ActionReturnAge<StaffOffhandQuickMotion::CancelReturn*.5f;
    if(bWhirlwindPresentation)return false;
    return bActionPresentation&&StaffOffhandQuickMotion::StrikeRig(ActionTime,ActionLength);
}

// Source line 62
bool UStaffOffhandMeleeComponent::QuickStaffClearance(FVector& Offset,FQuat& Rotation) const
{
    namespace M=StaffOffhandQuickMotion;
    if(ActionReturnAge>=0.f&&bQuickSupportReturn)
    {
        const float Return=M::Ease(0.f,M::CancelReturn,ActionReturnAge);
        Offset=QuickSupportReturnOffset*(1.f-Return);
        Rotation=FQuat::Slerp(QuickSupportReturnRotation,FQuat::Identity,Return).GetNormalized();
        return true;
    }
    if(!bActionPresentation||bUpperPresentation||bWhirlwindPresentation)return false;
    const float Progress=bHatchetChopPresentation?ActionTime/ActionLength:
        (ActionTime+M::Entry)/(ActionLength+M::Entry+M::Return);
    const auto Pose=OffhandQuickClearance::Staff(Progress,bHatchetChopPresentation);
    Offset=Pose.Offset;
    Rotation=FRotator(Pose.Angles.X,Pose.Angles.Y,Pose.Angles.Z).Quaternion();
    return true;
}

// Source line 111
void UStaffOffhandMeleeComponent::EndActionPresentation(bool Interrupted)
{
    if(!bActionPresentation)return;
    if(Interrupted)
    {
        bQuickSupportReturn=QuickStaffClearance(QuickSupportReturnOffset,QuickSupportReturnRotation);
        if(const auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>())
            ActionStaffRecovery=ActionStaffPose(Staff->CarryPoseInCamera());
        bReturnFromStrike=UsesStrikeRig();
        ReturnFromLower=bHatchetChopPresentation?0.f:bReturnFromStrike?StaffOffhandQuickMotion::StrikeLower(ActionTime,ActionLength):StaffOffhandQuickMotion::NativeLower(ActionTime,ActionLength);
        ActionReturnAge=0.f;
    }
    else {ActionReturnAge=-1.f;bQuickSupportReturn=false;Arms->ClearEntry();}
    if(bHatchetChopPresentation)
    {
        if(Interrupted)Arms->CaptureLeftEntry(.12f);
        Arms->PlayAnimation(Idle,true);
        Arms->SetPlayRate(0.f);
        bHatchetChopPresentation=false;
    }
    bActionPresentation=false;
}

// Source line 134
FTransform UStaffOffhandMeleeComponent::SampleHatchetBlade(float Time)
{
    Arms->SetRelativeLocation(OffhandAxeQuickMotion::StaffOffset);
    if(Time>=OffhandAxeQuickMotion::CarryStart)
    {
        Arms->ClearEntry();
        if(Time<OffhandAxeQuickMotion::CarryEnd)
        {
            // Both endpoints are sampled on this frame. Keeping the native
            // recovery moving avoids a freeze at the start of a static blend.
            OffhandAxeQuickMotion::Sample(*Arms,HatchetChop,Time*OffhandAxeQuickMotion::ClipRate);
            Arms->CaptureLeftEntry(1.f,(Time-OffhandAxeQuickMotion::CarryStart)/(OffhandAxeQuickMotion::CarryEnd-OffhandAxeQuickMotion::CarryStart));
        }
        OffhandAxeQuickMotion::Sample(*Arms,Idle,Age);
    }
    else OffhandAxeQuickMotion::Sample(*Arms,HatchetChop,Time*OffhandAxeQuickMotion::ClipRate);
    const FTransform Frame=BladeFit*OffhandAxeQuickMotion::BladeWorld(*Arms);
    Blade->SetRelativeTransform(BladeFit*KukriOffhandDraw::Grip());
    return Frame;
}

// Source line 155
FTransform UStaffOffhandMeleeComponent::ActionBladeInCamera(float Time) const
{
    FVector Wrist,Shoulder,Pole;FQuat Hand;FTransform Frame;
    const float SampleTime=FMath::Clamp(Time,0.f,ActionLength);
    if(bUpperPresentation)OffhandKukriUpper::SamplePose(SampleTime,Wrist,Hand,Shoulder,Pole,Frame);
    else OffhandKukriStrike::SamplePose(SampleTime,Wrist,Hand,Shoulder,Pole,Frame);
    const FTransform WristFrame(Hand,StaffOffhandQuickMotion::DonorRightHand(Time,bUpperPresentation)+Wrist);
    const bool Forward=bUpperPresentation&&SampleTime>=OffhandKukriUpper::DigitsAt&&SampleTime<=OffhandKukriUpper::DigitsEnd;
    // Contact query and visible knife consume exactly the same authored frame, never last tick's socket.
    const FTransform Grip=Forward?OffhandKukriUpper::KukriInHand:OffhandKukriPose::KukriInHand;
    return BladeFit*Grip*WristFrame;
}

// Source line 168
void UStaffOffhandMeleeComponent::SampleActionPose()
{
    namespace M=StaffOffhandQuickMotion;
    if(!Arms||!StrikeArms||!Blade||!Camera.IsValid())return;
    if(bHatchetChopPresentation&&bActionPresentation)
    {
        SampleHatchetBlade(ActionTime);
        return;
    }
    const bool Strike=UsesStrikeRig();
    float Lower=Strike?M::StrikeLower(ActionTime,ActionLength):M::NativeLower(ActionTime,ActionLength);
    if(ActionReturnAge>=0.f)
    {
        if(Strike)Lower=FMath::Lerp(ReturnFromLower,1.f,M::Ease(0.f,M::CancelReturn*.5f,ActionReturnAge));
        else if(bReturnFromStrike)Lower=1.f-M::Ease(M::CancelReturn*.5f,M::CancelReturn,ActionReturnAge);
        else Lower=ReturnFromLower*(1.f-M::Ease(0.f,M::CancelReturn,ActionReturnAge));
    }
    if(Strike)
    {
        StrikeArms->StrikeTime=bUpperPresentation?-1.f:FMath::Clamp(ActionTime,0.f,ActionLength);
        StrikeArms->UppercutTime=bUpperPresentation?FMath::Clamp(ActionTime,0.f,ActionLength):-1.f;
        StrikeArms->RightHandInCamera=M::DonorRightHand(ActionTime,bUpperPresentation);
        StrikeArms->PresentationOffset=M::HiddenOffset*Lower;
        StrikeArms->TickAnimation(0.f,false);StrikeArms->RefreshBoneTransforms();
        FTransform Frame=ActionBladeInCamera(ActionTime);Frame.AddToTranslation(M::HiddenOffset*Lower);
        Blade->SetWorldTransform(Frame*Camera->GetComponentTransform());
    }
    else
    {
        // Freeze the idle phase across the action; return to that same native grasp without replaying Equip.
        Arms->SetRelativeLocation(FVector(2.f,-4.f,-1.f)+M::HiddenOffset*Lower);
        Arms->SetPosition(Age,false);Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
        Blade->SetRelativeTransform(BladeFit*KukriOffhandDraw::Grip());
    }
}
