#include "FPSPlayerBodyComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "FPSPlayerBodyPoses.h"
#include "FPSBodyBowMotion.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowArmsMeshComponent.h"
#include "../Weapons/Bow/BowPartComponent.h"
#include "../Weapons/Bow/BowFlexMeshComponent.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Items/FPSPotionUseComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/MaterialInstanceDynamic.h"

void UFPSPlayerBodyComponent::CaptureBow(const UBowWeaponComponent& Source,FFPSBodyWeapon& Out) const
{
    Out.PoseFamily=TEXT("Bow");Out.AttachHand=1;Out.GripBone=TEXT("hand_l");
    if(!Source.Viewmodel||!Source.Viewmodel->GetSkeletalMeshAsset())return;
    Out.Source=Source.Viewmodel;
    Out.Mesh=Source.Viewmodel->GetSkeletalMeshAsset();Out.HoldClip=Source.Animations.FindRef(TEXT("Idle"));
    const auto& Ref=Source.Viewmodel->GetSkeletalMeshAsset()->GetRefSkeleton();
    // Compact final-pose contract: two wrists, grip marker, string marker.
    // Fingers use the shared native-body contact packet, not a second rig stream.
    for(const TCHAR* Bone:{TEXT("hand_r"),TEXT("hand_l"),TEXT("bow_grip"),TEXT("bow_nock")})
        Out.MotionBones.Add(Ref.FindBoneIndex(Bone));
    for(int32 I=0;I<Source.Viewmodel->GetSkeletalMeshAsset()->GetMaterials().Num();++I)Out.HiddenMaterials.Add(I);
    for(const auto& Clip:Source.Animations)if(Clip.Value)
    {FFPSBodyBowClip Entry;Entry.Role=Clip.Key;Entry.Sequence=Clip.Value.Get();Out.MotionClips.Add(MoveTemp(Entry));}
    Out.Bow.UpperTip=Source.UpperTipCM;Out.Bow.LowerTip=Source.LowerTipCM;Out.Bow.Brace=Source.BraceNockCM;
    Out.Bow.ArrowRest=Source.ArrowRestCM;Out.Bow.StringRadius=Source.StringRadiusCM;Out.Bow.ArrowRadius=Source.ArrowRadiusCM;
    Out.Bow.ArrowLength=Source.ArrowLengthCM;Out.Bow.FlexDistribution=Source.FlexDistribution;
    const auto Capture=[&](FName Slot)
    {
        const auto* Part=Source.Part(Slot);if(!Part)return;
        FFPSBodyAttachment Spec;Spec.Slot=Slot;Spec.Mesh=Part->PartMesh;
        const UMeshComponent* Visual=Part->FlexVisual?static_cast<const UMeshComponent*>(Part->FlexVisual.Get()):Part->Visual.Get();
        if(Part->FlexVisual)Spec.SkeletalMesh=Cast<USkeletalMesh>(Part->FlexVisual->GetSkinnedAsset());
        Spec.RelativeTransform=Slot==TEXT("riser")?FTransform(FQuat::Identity,Source.GripTrimCM,FVector(Source.BowScale)):Part->GetRelativeTransform();
        if(Visual)for(auto* Material:Visual->GetMaterials())
        {
            while(const auto* Dynamic=Cast<UMaterialInstanceDynamic>(Material))Material=Dynamic->Parent;
            Spec.Materials.Add(Material);
        }
        Out.Parts.Add(MoveTemp(Spec));
    };
    Capture(TEXT("riser"));
    for(FName Slot:Source.SlotOrder)if(Slot!=TEXT("riser"))Capture(Slot);
}

void UFPSPlayerBodyComponent::CaptureBowMotion(const FFPSBodyWeapon& Weapon,FFPSBodyMotionSample& Sample,FFPSBodyMotionRig& Rig)
{
    auto* Source=Weapon.Source.Get();
    if(!Source||!Source->IsVisible()||Source->bHiddenInGame||Weapon.MotionBones.Num()!=4)return;
    const auto& Pose=Source->GetComponentSpaceTransforms();
    for(int32 Bone:Weapon.MotionBones)if(!Pose.IsValidIndex(Bone))return;
    CaptureMotionHand(Source,TEXT("hand_r"),0,false,Sample);
    CaptureMotionHand(Source,TEXT("hand_l"),1,false,Sample);
    if(Sample.Fingers!=3)return;
    Sample.Channel=TEXT("Bow");Rig.Valid=true;Rig.Schema=Weapon.MotionSchema;
    for(int32 Bone:Weapon.MotionBones)
    {
        FTransform Contact=Pose[Bone];Contact.SetScale3D(FVector::OneVector);
        Rig.Bones.Add(Contact);
    }
    // Interpolate each marker in its owning wrist's frame. Independent world
    // interpolation would let the string slip away from the drawing fingers.
    Rig.Bones[2]=Rig.Bones[2].GetRelativeTransform(Rig.Bones[1]);
    Rig.Bones[3]=Rig.Bones[3].GetRelativeTransform(Rig.Bones[0]);
}

void UFPSPlayerBodyComponent::SampleBowState(const UBowWeaponComponent& Bow,FFPSBodyState& State) const
{
    State.Family=TEXT("Bow");State.Weapon=*Bow.Definition();State.Action=EFPSBodyAction::None;
    State.BowClip=Bow.CurrentClip;State.BowClipTime=Bow.Viewmodel?Bow.Viewmodel->GetPosition():0.f;
    if(const auto* Clip=Bow.Animations.FindRef(Bow.CurrentClip).Get())State.BowClipLength=Clip->GetPlayLength();
    State.bBowClipLooping=Bow.bCurrentClipLoops;State.BowClipRate=State.bBowClipLooping?1.f:0.f;
    // Send the executor's clock on the first packet too. A frame-difference
    // estimate is zero on clip changes and can retain a forward rate on cancel.
    const auto Rate=[&](float Seconds){return State.BowClipLength/FMath::Max(.001f,Seconds);};
    switch(Bow.Stage)
    {
    case EBowStage::Drawing:State.BowClipRate=Rate(Bow.DrawSeconds);break;
    case EBowStage::LetDown:
    {
        const float T=FMath::Clamp(Bow.Elapsed/FMath::Max(.001f,Bow.StageSeconds),0.f,1.f);
        State.BowClipRate=-Rate(Bow.StageSeconds)*Bow.LetDownPhase*6.f*T*(1.f-T);break;
    }
    case EBowStage::Release:case EBowStage::Recover:State.BowClipRate=Rate(Bow.ReleaseSeconds+Bow.RecoverSeconds);break;
    case EBowStage::Nocking:State.BowClipRate=Rate(Bow.NockSeconds);break;
    case EBowStage::DrawEntry:State.BowClipRate=State.BowClip==TEXT("Draw")?0.f:Rate(Bow.DrawEntrySeconds);break;
    case EBowStage::Equip:State.BowClipRate=Rate(Bow.EquipSeconds);break;
    case EBowStage::QuickCombat:State.BowClipRate=1.f;break;
    default:break;
    }
    State.BowNock=Bow.NockPoint();State.bAiming=Bow.IsAimHeld();
    const bool Entry=Bow.Stage==EBowStage::DrawEntry&&Bow.bEntryNeedsArrow;
    const float Phase=Entry?Bow.Elapsed/FMath::Max(.001f,Bow.DrawEntrySeconds):Bow.Elapsed/FMath::Max(.001f,Bow.NockSeconds);
    State.bBowTakingArrow=(Bow.Stage==EBowStage::Nocking||Entry)&&Phase>=.34f;
    State.bBowArrow=Bow.Stage!=EBowStage::QuickCombat&&(Bow.bArrowNocked||State.bBowTakingArrow);
    const float Seat=Entry?.9f:Bow.NockContactFraction;
    State.BowSeat=FMath::SmoothStep(0.f,1.f,(Phase-Seat)/FMath::Max(.001f,1.f-Seat));
    State.bBowCarryAxis=Entry?FName(Bow.DrawEntryClip())!=FName(TEXT("Draw")):Bow.bNockHasCarryAxis;
    const bool Contacting=(Bow.Stage==EBowStage::Nocking||Entry)&&Phase>=Seat;
    const bool Releasing=Bow.Stage==EBowStage::Release
        ||(Entry&&Bow.ReleaseFeedbackAge>=0.f&&Bow.ReleaseFeedbackAge<Bow.RingSeconds);
    State.BowStringContact=Releasing?0.f:Contacting?(Entry?1.f:State.BowSeat)
        :(Bow.IsDrawing()||Bow.Stage==EBowStage::LetDown||(Bow.Stage==EBowStage::Ready&&Bow.bArrowNocked)?1.f:0.f);
    State.ActionVariant=Bow.CurrentClip;
    State.BowCastTransfer=Bow.CastTransfer();
    const auto* Magic=GetOwner()->FindComponentByClass<UFPSFireballComponent>();
    const auto* Use=GetOwner()->FindComponentByClass<UFPSPotionUseComponent>();
    const bool Support=(Magic&&Magic->IsOccupyingLeftHand())||(Use&&Use->UsesBowSupport())
        ||(Bow.Viewmodel&&Bow.Viewmodel->IsReturningLeftHand());
    if(State.BowCastTransfer>0.f&&State.BowCastTransfer<1.f)
        State.BowCastTransferRate=(Support?1.f:-1.f)/FBowCastHandPose::Seconds;
    State.bBowTwoHandConsume=Use&&(Use->IsTwoHanded()||Use->IsReturningBow());
    State.BowStowWeight=State.bBowTwoHandConsume?Use->OffhandLowerWeight():0.f;
    if(State.BowCastTransfer>0.f||State.bBowTwoHandConsume)State.BowStringContact=0.f;
    if(Bow.Stage==EBowStage::Equip)State.Action=EFPSBodyAction::Equip;
    else if(Bow.Stage==EBowStage::QuickCombat)State.Action=EFPSBodyAction::GunBash;
}

void UFPSPlayerBodyComponent::ClearBow()
{
    for(int32 I=WorldBowParts.Num()-1;I>=0;--I)if(auto* Part=WorldBowParts[I].Get())
    {
        TArray<USceneComponent*> Children;Part->GetChildrenComponents(false,Children);
        for(auto* Child:Children)if(IsValid(Child))Child->DestroyComponent();
        Part->DestroyComponent();
    }
    WorldBowParts.Reset();BowClips.Reset();BowRig=nullptr;SampledBowClip=NAME_None;SampledBowTime=-1.f;
    bHasNativeBowHeldNock=false;
    BowItemInstance.Reset();
}

void UFPSPlayerBodyComponent::BuildBow(const FFPSBodyWeapon& Definition,USkeletalMeshComponent* Rig)
{
    BowRig=Rig;BowSettings=Definition.Bow;BowItemInstance=Definition.ItemInstance;
    auto* Body=GetBodyMesh();if(!Body||!BodyAnimation)return;
    for(int32 Side=0;Side<2;++Side)
    {
        const FName Hand=Side==0?TEXT("hand_r"):TEXT("hand_l");
        BowGripRigs[Side].Initialize(Rig->GetSkeletalMeshAsset()->GetRefSkeleton(),Body->GetSkeletalMeshAsset()->GetRefSkeleton(),Hand,Hand);
    }
    for(const auto& Clip:Definition.MotionClips)if(auto* Asset=Clip.Sequence.LoadSynchronous())BowClips.Add(Clip.Role,Asset);
    UBowPartComponent* Riser=nullptr;
    for(const auto& Spec:Definition.Parts)
    {
        auto* Part=NewObject<UBowPartComponent>(GetOwner(),NAME_None,RF_Transient);
        Part->InitializeAsPart(GetOwner(),Spec.Slot,Riser?static_cast<USceneComponent*>(Riser):Rig);
        if(Spec.Slot==TEXT("riser"))
        {
            Riser=Part;BowRiserMount=Spec.RelativeTransform;
        }
        Part->SetRelativeTransform(Spec.RelativeTransform);
        if(auto* Skeletal=Spec.SkeletalMesh.LoadSynchronous())Part->SetSkeletalMesh(Skeletal);
        else Part->SetMesh(Spec.Mesh.LoadSynchronous());
        if(Spec.Slot==TEXT("string")){Part->AddRod(TEXT("Upper"));Part->AddRod(TEXT("Lower"));}
        if(Spec.Slot==TEXT("arrow"))Part->AddRod(TEXT("Arrow"));
        TArray<USceneComponent*> Children;Part->GetChildrenComponents(true,Children);
        for(auto* Child:Children)if(auto* Mesh=Cast<UMeshComponent>(Child))
            for(int32 I=0;I<Spec.Materials.Num();++I)if(auto* Material=Spec.Materials[I].LoadSynchronous())Mesh->SetMaterial(I,Material);
        Part->SetPartVisible(Part->HasMesh()||Part->RodCount()>0);WorldBowParts.Add(Part);
    }
    UpdateBow();
}

void UFPSPlayerBodyComponent::UpdateBow()
{
    if(!BowRig||!BodyAnimation||!BowGripRigs[0].IsValid()||!BowGripRigs[1].IsValid())return;
    if(BowItemInstance!=DisplayState.WeaponInstance)
    {
        BodyAnimation->bBowPose=false;bHasNativeBowHeldNock=false;
        UpdateBowVisibility(Character.IsValid()&&Character->IsLocallyControlled()&&!IsThirdPersonViewEnabled());return;
    }
    auto* Clip=BowClips.FindRef(DisplayState.BowClip).Get();
    if(!Clip)Clip=BowClips.FindRef(TEXT("Idle"));
    if(!Clip)return;
    const float Time=FMath::Clamp(DisplayState.BowClipTime,0.f,Clip->GetPlayLength());
    auto* Rig=CastChecked<UFPSBodyWeaponMeshComponent>(BowRig);
    const bool WasTransitioning=Rig->IsHoldTransitionActive();
    Rig->AdvanceHoldTransition(GetWorld()->GetDeltaSeconds());
    const int32 BindingIndex=MotionBindings.IndexOfByPredicate([&](const auto& Binding){return Binding.Mesh.Get()==BowRig;});
    const bool FinalPose=DisplayState.Contacts.Channel==TEXT("Bow")&&DisplayState.Contacts.Fingers==3
        &&HasMatchingMotionRig(BindingIndex)&&MotionBindings[BindingIndex].Definition.MotionBones.Num()==4
        &&MotionBindings[BindingIndex].Definition.ItemInstance==DisplayState.WeaponInstance;
    if(FinalPose)
    {
        auto& Binding=MotionBindings[BindingIndex];auto& Smoothed=Binding.Smoothed;
        const auto& Incoming=DisplayState.Contacts.Rigs[BindingIndex];
        const bool Local=Character.IsValid()&&Character->IsLocallyControlled();
        const float Alpha=Local||!Smoothed.Valid?1.f:1.f-FMath::Exp(-35.f*GetWorld()->GetDeltaSeconds());
        if(!Smoothed.Valid)Smoothed=Incoming;
        else for(int32 I=0;I<4;++I)
        {FTransform Mixed;Mixed.Blend(Smoothed.Bones[I],Incoming.Bones[I],Alpha);Smoothed.Bones[I]=Mixed;}
        auto Pose=BowRig->GetComponentSpaceTransforms();
        for(int32 I=0;I<4;++I)
        {
            const FTransform Contact=I<2?Smoothed.Bones[I]:Smoothed.Bones[I]*Smoothed.Bones[I==2?1:0];
            Pose[Binding.Definition.MotionBones[I]]=Contact;
        }
        // The owner already evaluated walk/run, partial-release and let-down
        // handoffs. Preserve that result rather than replaying the raw clip.
        Rig->PublishMechanicalPose(Pose);
        for(int32 Side=0;Side<2;++Side)
        {
            const FTransform& Hand=Smoothed.Bones[Side];
            BodyAnimation->BowHands[Side]=BowGripRigs[Side].Mount.Inverse()*Hand;
            if(Side==1)BowRig->SetRelativeTransform(Hand.Inverse()*BowGripRigs[Side].Mount);
        }
        BodyAnimation->EquipmentGripHands=3;BodyAnimation->bBowPose=true;
        SampledBowClip=NAME_None;SampledBowTime=-1.f;
    }
    else if(SampledBowClip!=Clip->GetFName()||!FMath::IsNearlyEqual(SampledBowTime,Time,.0001f)||WasTransitioning)
    {
        if(MotionBindings.IsValidIndex(BindingIndex))MotionBindings[BindingIndex].Smoothed.Valid=false;
        if(SampledBowClip!=Clip->GetFName())
        {
            if(!SampledBowClip.IsNone())Rig->CaptureHoldTransition(.12f);
            BowRig->PlayAnimation(Clip,false);BowRig->SetPlayRate(0.f);
        }
        BowRig->SetPosition(Time,false);BowRig->TickAnimation(0.f,false);BowRig->RefreshBoneTransforms();
        SampledBowClip=Clip->GetFName();SampledBowTime=Time;
        const auto& Pose=BowRig->GetComponentSpaceTransforms();
        for(int32 Side=0;Side<2;++Side)
        {
            BowGripRigs[Side].Transfer(Pose,BodyAnimation->EquipmentFingers);
            FTransform Hand=Pose[BowGripRigs[Side].SourceHand];Hand.SetScale3D(FVector::OneVector);
            BodyAnimation->BowHands[Side]=BowGripRigs[Side].Mount.Inverse()*Hand;
            if(Side==1)BowRig->SetRelativeTransform(Hand.Inverse()*BowGripRigs[Side].Mount);
        }
        BodyAnimation->EquipmentGripHands=3;BodyAnimation->bBowPose=true;
    }
    const auto Find=[&](FName Slot)->UBowPartComponent*
    {for(auto Part:WorldBowParts)if(Part&&Part->SlotName==Slot)return Part;return nullptr;};
    auto* Riser=Find(TEXT("riser"));if(!Riser)return;
    // Match AnimatedRiserMount: marker position/rotation, authored centimetre
    // scale and camera-axis trim. Imported marker scale must not scale the bow.
    FTransform RiserInRig=BowRig->GetSocketTransform(TEXT("bow_grip"),RTS_Component);
    RiserInRig.SetScale3D(BowRiserMount.GetScale3D());
    RiserInRig.AddToTranslation(BowRiserMount.GetLocation());Riser->SetRelativeTransform(RiserInRig);
    FVector Nock=DisplayState.BowClip.IsNone()?BowSettings.Brace:DisplayState.BowNock;
    if(DisplayState.BowStringContact>0.f&&BowRig->DoesSocketExist(TEXT("bow_nock")))
    {
        // Use the same sampled/blended frame as the drawing hand. After release
        // the string returns independently, using the source's logical nock.
        const FVector HandPoint=BowRig->GetSocketTransform(TEXT("bow_nock"),RTS_Component).GetLocation();
        Nock=FMath::Lerp(BowSettings.Brace,RiserInRig.InverseTransformPosition(HandPoint),DisplayState.BowStringContact);
    }
    FVector Upper=BowSettings.UpperTip,Lower=BowSettings.LowerTip;
    Riser->ApplyStringLoad(Nock,BowSettings.Brace,BowSettings.FlexDistribution);Riser->FlexTips(Upper,Lower);
    if(auto* String=Find(TEXT("string")))
    {String->SetPartVisible(true);String->StretchRod(0,Upper,Nock,BowSettings.StringRadius);String->StretchRod(1,Lower,Nock,BowSettings.StringRadius);}
    if(auto* Arrow=Find(TEXT("arrow")))
    {
        Arrow->SetPartVisible(DisplayState.bBowArrow);
        if(DisplayState.bBowArrow)
        {
            FVector Tail=Nock,Axis=(BowSettings.ArrowRest-Nock).GetSafeNormal();
            if(DisplayState.bBowTakingArrow&&BowRig->DoesSocketExist(TEXT("bow_nock")))
            {
                const FTransform NockMarker=BowRig->GetSocketTransform(TEXT("bow_nock"),RTS_Component);
                Tail=FMath::Lerp(RiserInRig.InverseTransformPosition(NockMarker.GetLocation()),Nock,DisplayState.BowSeat);
                const FVector CarryAxis=DisplayState.bBowCarryAxis
                    ?RiserInRig.InverseTransformVectorNoScale(NockMarker.GetRotation().GetForwardVector()).GetSafeNormal()
                    :(BowSettings.ArrowRest-Tail).GetSafeNormal();
                Axis=FMath::Lerp(CarryAxis,(BowSettings.ArrowRest-Tail).GetSafeNormal(),DisplayState.BowSeat).GetSafeNormal();
            }
            Arrow->StretchRod(0,Tail,Tail+Axis*BowSettings.ArrowLength,BowSettings.ArrowRadius);
        }
    }
    const bool HideOwner=Character.IsValid()&&Character->IsLocallyControlled()&&!IsThirdPersonViewEnabled();
    UpdateBowVisibility(HideOwner);
}

void UFPSPlayerBodyComponent::UpdateNativeBowContacts()
{
    auto* Body=GetBodyMesh();
    if(!Body||!BowRig||!BodyAnimation||DisplayState.Family!=TEXT("Bow")||BowItemInstance!=DisplayState.WeaponInstance)return;
    const float Weight=FMath::Clamp(BodyAnimation->GetCurveValue(FPSBodyBowMotion::WeightCurve),0.f,1.f);
    if(Weight<=ZERO_ANIMWEIGHT_THRESH)return;
    const auto Find=[&](FName Slot)->UBowPartComponent*
    {for(auto Part:WorldBowParts)if(Part&&Part->SlotName==Slot)return Part;return nullptr;};
    auto* Riser=Find(TEXT("riser"));if(!Riser)return;
    double Grip[7];
    for(int32 I=0;I<7;++I)Grip[I]=BodyAnimation->GetCurveValue(FPSBodyBowMotion::GripCurves[I]);
    FQuat Rotation(Grip[3],Grip[4],Grip[5],Grip[6]);
    if(Rotation.SizeSquared()<UE_SMALL_NUMBER)return;
    Rotation.Normalize();
    const FTransform NativeGrip(Rotation,FVector(Grip[0],Grip[1],Grip[2]),BowRiserMount.GetScale3D());
    FTransform Left=BowRig->GetSocketTransform(TEXT("hand_l"),RTS_Component);Left.SetScale3D(FVector::OneVector);
    FTransform Right=BowRig->GetSocketTransform(TEXT("hand_r"),RTS_Component);Right.SetScale3D(FVector::OneVector);
    FTransform Marker=BowRig->GetSocketTransform(TEXT("bow_grip"),RTS_Component);
    Marker.SetScale3D(BowRiserMount.GetScale3D());Marker.AddToTranslation(BowRiserMount.GetLocation());
    const FTransform BaseGrip=Marker*Left.Inverse()*BowGripRigs[1].Mount;
    FTransform GripInHand;GripInHand.Blend(BaseGrip,NativeGrip,Weight);
    // Rebase the visible bow to the actual native left wrist after every body
    // layer (including aim and reactions). No previous-frame attachment read.
    BowRig->SetRelativeTransform(FTransform::Identity);
    FTransform BowWorld=GripInHand*Body->GetSocketTransform(TEXT("hand_l"));
    if(BodyAnimation->GetCurveValue(FPSBodyBowMotion::RightHoldCurve)>.5f)
    {
        float V[7];for(int32 I=0;I<7;++I)V[I]=BodyAnimation->GetCurveValue(FPSBodyBowMotion::RightGripCurves[I]);
        const FQuat Q(V[3],V[4],V[5],V[6]);
        BowWorld=FTransform(Q.GetNormalized(),FVector(V[0],V[1],V[2]),BowRiserMount.GetScale3D())*Body->GetSocketTransform(TEXT("hand_r"));
    }
    Riser->SetRelativeTransform(BowWorld.GetRelativeTransform(BowRig->GetComponentTransform()));
    const FTransform RightWorld=Body->GetSocketTransform(TEXT("hand_r"));
    FTransform BaseNock=BowRig->GetSocketTransform(TEXT("bow_nock"),RTS_Component);
    BaseNock.SetScale3D(FVector::OneVector);BaseNock=BaseNock.GetRelativeTransform(Right)*BowGripRigs[0].Mount;
    const FVector NativeNock(BodyAnimation->GetCurveValue(FPSBodyBowMotion::NockCurves[0]),
        BodyAnimation->GetCurveValue(FPSBodyBowMotion::NockCurves[1]),BodyAnimation->GetCurveValue(FPSBodyBowMotion::NockCurves[2]));
    const FVector InHand=FMath::Lerp(BaseNock.GetLocation(),NativeNock,Weight);
    const FVector HandPoint=BowWorld.InverseTransformPosition(RightWorld.TransformPosition(InHand));
    const bool NoSample=DisplayState.BowClip.IsNone();
    if(NoSample||DisplayState.BowCastTransfer>0.f||DisplayState.bBowTwoHandConsume)bHasNativeBowHeldNock=false;
    FVector Nock=NoSample?BowSettings.Brace:DisplayState.BowNock;
    if(!NoSample&&DisplayState.BowStringContact>0.f)
    {
        Nock=FMath::Lerp(BowSettings.Brace,HandPoint,DisplayState.BowStringContact);
        NativeBowHeldNock=Nock;NativeBowHeldSourceNock=DisplayState.BowNock;bHasNativeBowHeldNock=true;
    }
    else if(bHasNativeBowHeldNock)
    {
        // Preserve the actually displayed draw on release. Use the source's
        // rebound fraction, so partial draws and remote interpolation cannot
        // jump the string to a different hand pose before it returns to brace.
        const double Draw=(NativeBowHeldSourceNock-BowSettings.Brace).Size();
        const double Remaining=Draw>.1?FMath::Clamp((DisplayState.BowNock-BowSettings.Brace).Size()/Draw,0.,1.):0.;
        Nock=FMath::Lerp(BowSettings.Brace,NativeBowHeldNock,Remaining);
    }
    FVector Upper=BowSettings.UpperTip,Lower=BowSettings.LowerTip;
    Riser->ApplyStringLoad(Nock,BowSettings.Brace,BowSettings.FlexDistribution);Riser->FlexTips(Upper,Lower);
    if(auto* String=Find(TEXT("string")))
    {String->StretchRod(0,Upper,Nock,BowSettings.StringRadius);String->StretchRod(1,Lower,Nock,BowSettings.StringRadius);}
    if(auto* Arrow=Find(TEXT("arrow"));Arrow&&DisplayState.bBowArrow)
    {
        FVector Tail=Nock,Axis=(BowSettings.ArrowRest-Nock).GetSafeNormal();
        if(DisplayState.bBowTakingArrow)
        {
            const FVector Carry=BowWorld.InverseTransformPosition(RightWorld.TransformPosition(BaseNock.GetLocation()));
            Tail=FMath::Lerp(Carry,Nock,DisplayState.BowSeat);
            const FTransform CarryWorld=BaseNock*RightWorld;
            const FVector CarryAxis=DisplayState.bBowCarryAxis?BowWorld.InverseTransformVectorNoScale(CarryWorld.GetRotation().GetForwardVector()).GetSafeNormal():Axis;
            Axis=FMath::Lerp(CarryAxis,(BowSettings.ArrowRest-Tail).GetSafeNormal(),DisplayState.BowSeat).GetSafeNormal();
        }
        Arrow->StretchRod(0,Tail,Tail+Axis*BowSettings.ArrowLength,BowSettings.ArrowRadius);
    }
}

void UFPSPlayerBodyComponent::UpdateBowVisibility(bool HideOwner)
{
    const bool Stowed=IsDeathViewActive()||FPSBodyPoses::Traversing(DisplayState.Motion)||ServerClock()<WorldWeaponsHiddenUntil
        ||(DisplayState.bBowTwoHandConsume&&DisplayState.BowStowWeight>=1.f-UE_KINDA_SMALL_NUMBER)
        ||DisplayState.Action==EFPSBodyAction::DoorPush||DisplayState.Family!=TEXT("Bow")||BowItemInstance!=DisplayState.WeaponInstance;
    for(auto Part:WorldBowParts)if(Part)
    {
        const bool Hidden=Stowed||FPSPlayerBodyWorldBodyHidden();
        if(Part->bHiddenInGame!=Hidden)Part->SetHiddenInGame(Hidden,true);
        TArray<USceneComponent*> Children;Part->GetChildrenComponents(true,Children);
        for(auto* Child:Children)if(auto* Primitive=Cast<UPrimitiveComponent>(Child))
        {
            FPSBodyEquipment::ApplyOwnerVisibilityFlags(Primitive,false,HideOwner);
            FPSBodyEquipment::ApplyShadowFlags(Primitive,ShouldWorldBodyCastShadow()&&!Stowed&&Part->IsPartVisible());
        }
    }
}
