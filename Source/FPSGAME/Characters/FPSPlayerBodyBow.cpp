#include "FPSPlayerBodyComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "FPSPlayerBodyPoses.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowArmsMeshComponent.h"
#include "../Weapons/Bow/BowPartComponent.h"
#include "../Weapons/Bow/BowFlexMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/MaterialInstanceDynamic.h"

void UFPSPlayerBodyComponent::CaptureBow(const UBowWeaponComponent& Source,FFPSBodyWeapon& Out) const
{
    Out.PoseFamily=TEXT("Bow");Out.AttachHand=1;Out.GripBone=TEXT("hand_l");
    if(!Source.Viewmodel||!Source.Viewmodel->GetSkeletalMeshAsset())return;
    Out.Mesh=Source.Viewmodel->GetSkeletalMeshAsset();Out.HoldClip=Source.Animations.FindRef(TEXT("Idle"));
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

void UFPSPlayerBodyComponent::SampleBowState(const UBowWeaponComponent& Bow,FFPSBodyState& State) const
{
    State.Family=TEXT("Bow");State.Weapon=*Bow.Definition();State.Action=EFPSBodyAction::None;
    State.BowClip=Bow.CurrentClip;State.BowClipTime=Bow.Viewmodel?Bow.Viewmodel->GetPosition():0.f;
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
}

void UFPSPlayerBodyComponent::BuildBow(const FFPSBodyWeapon& Definition,USkeletalMeshComponent* Rig)
{
    BowRig=Rig;BowSettings=Definition.Bow;
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
    auto* Clip=BowClips.FindRef(DisplayState.BowClip).Get();
    if(!Clip)Clip=BowClips.FindRef(TEXT("Idle"));
    if(!Clip)return;
    const float Time=FMath::Clamp(DisplayState.BowClipTime,0.f,Clip->GetPlayLength());
    auto* Rig=CastChecked<UFPSBodyWeaponMeshComponent>(BowRig);
    const bool WasTransitioning=Rig->IsHoldTransitionActive();
    Rig->AdvanceHoldTransition(GetWorld()->GetDeltaSeconds());
    if(SampledBowClip!=Clip->GetFName()||!FMath::IsNearlyEqual(SampledBowTime,Time,.0001f)||WasTransitioning)
    {
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

void UFPSPlayerBodyComponent::UpdateBowVisibility(bool HideOwner)
{
    const bool Stowed=FPSBodyPoses::Traversing(DisplayState.Motion)||ServerClock()<WorldWeaponsHiddenUntil
        ||DisplayState.Action==EFPSBodyAction::Cast||DisplayState.Action==EFPSBodyAction::Consume
        ||DisplayState.Action==EFPSBodyAction::DoorPush||DisplayState.Family!=TEXT("Bow");
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
