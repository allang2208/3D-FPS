#include "FPSPlayerBodyComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "FPSPlayerBodyPoses.h"
#include "FPSBodySwordMotion.h"
#include "FPSBodyRifleMotion.h"
#include "FPSBodyStaffGrip.h"
#include "../FPSGAMECharacter.h"
#include "../Items/FPSPotionUseComponent.h"
#include "../Movement/FPSDoorPushComponent.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "../Weapons/WeaponBipodDeploymentComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffArmsMeshComponent.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../Weapons/Super90WeaponAssets.h"
#include "../Weapons/TubeShotgunAssets.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Animation/AnimSequence.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace
{
FTransform BodyMotionRigidTransform(FTransform T){T.SetScale3D(FVector::OneVector);return T;}
bool Drawn(const UPrimitiveComponent* C){return C&&C->IsVisible()&&!C->bHiddenInGame;}
}

void UFPSPlayerBodyComponent::UpdateSwordGripMount()
{
    if(!BodyAnimation)return;
    const float GripRoll=BodyAnimation->GetCurveValue(TEXT("SwordGripRoll"));
    const float GripSlide=BodyAnimation->GetCurveValue(TEXT("SwordGripSlide"));
    for(auto& Binding:MotionBindings)
    {
        if(Binding.Definition.PoseFamily!=TEXT("Sword")||!Binding.Smoothed.Valid||
            !Binding.FrozenPose.IsValidIndex(Binding.NativeWeaponRoot))continue;
        auto* Root=Binding.Mesh.IsValid()?static_cast<UPrimitiveComponent*>(Binding.Mesh.Get()):Binding.Static.Get();
        if(!Root||IsWorldWeaponStowed(Root))continue;
        // The fitted wrist can turn and slide along the handle independently
        // from the blade. Undo both at the frozen native weapon pivot so an
        // upper/lower hand exchange retains the authored blade trajectory.
        const FTransform Weapon=BodyMotionRigidTransform(Binding.FrozenPose[Binding.NativeWeaponRoot]);
        const FTransform GripCorrection(FQuat(FVector::UpVector,FMath::DegreesToRadians(-GripRoll)),FVector(0,0,-GripSlide));
        const FTransform Pivot=Weapon.Inverse()*GripCorrection*Weapon;
        Root->SetRelativeTransform(Pivot*Binding.Smoothed.Root);
    }
}

bool UFPSPlayerBodyComponent::ResolveWorldWeaponPart(const USkeletalMeshComponent* Source,const UStaticMeshComponent* SourcePart,
    USkeletalMeshComponent*& WorldHost,UStaticMeshComponent*& WorldPart) const
{
    WorldHost=nullptr;WorldPart=nullptr;
    for(int32 I=0;I<LocalWeapons.Num();++I)
    {
        if(LocalWeapons[I].Source.Get()!=Source||!MotionBindings.IsValidIndex(I))continue;
        const int32 Part=LocalWeapons[I].SourceParts.IndexOfByPredicate([&](const auto& P){return P.Get()==SourcePart;});
        const auto& Binding=MotionBindings[I];
        if(!Binding.Parts.IsValidIndex(Part))return false;
        WorldHost=Binding.Mesh.Get();WorldPart=Binding.Parts[Part].Get();
        return Drawn(WorldHost)&&Drawn(WorldPart);
    }
    return false;
}

bool UFPSPlayerBodyComponent::ResolveWorldWeaponFrame(const USkeletalMeshComponent* Source,const USceneComponent* SourceAnchor,
    const FTransform& SourceFrame,FTransform& WorldFrame) const
{
    if(!Source)return false;
    for(int32 I=0;I<LocalWeapons.Num();++I)
    {
        if(LocalWeapons[I].Source.Get()!=Source||!MotionBindings.IsValidIndex(I))continue;
        const auto& Binding=MotionBindings[I];auto* Weapon=Binding.Mesh.Get();
        if(!Drawn(Weapon))return false;
        // The offhand exit is a scene marker below its copied muzzle attachment.
        // Match that ancestor so barrel motion and the actual suppressor length
        // use the same part transform as the geometry being rendered.
        for(auto* Anchor=SourceAnchor;Anchor&&Anchor!=Source;Anchor=Anchor->GetAttachParent())
        {
            const int32 Part=LocalWeapons[I].SourceParts.IndexOfByPredicate([&](const auto& P){return P.Get()==Anchor;});
            if(!Binding.Parts.IsValidIndex(Part))continue;
            auto* VisiblePart=Binding.Parts[Part].Get();if(!Drawn(VisiblePart))continue;
            WorldFrame=SourceFrame.GetRelativeTransform(Anchor->GetComponentTransform())*VisiblePart->GetComponentTransform();
            WorldFrame.SetScale3D(FVector::OneVector);return true;
        }
        // Rifle world poses are rebased to the owning wrist. Mapping component
        // origins would therefore add the viewmodel offset a second time. Use
        // the matching mechanical root, with centimetres independent of the
        // imported bone scale (some native rigs store scale 100).
        const FTransform NativeRoot=BodyMotionRigidTransform(Source->GetSocketTransform(TEXT("WPN_root")));
        const FTransform WorldRoot=BodyMotionRigidTransform(Weapon->GetSocketTransform(TEXT("WPN_root")));
        WorldFrame=SourceFrame.GetRelativeTransform(NativeRoot)*WorldRoot;
        WorldFrame.SetScale3D(FVector::OneVector);return true;
    }
    return false;
}

FFPSBodyGripRig* UFPSPlayerBodyComponent::MotionMap(USkeletalMeshComponent* Source,FName Hand,int32 Side)
{
    auto* Body=GetBodyMesh();if(!Source||!Source->GetSkeletalMeshAsset()||!Body||!Body->GetSkeletalMeshAsset())return nullptr;
    if(MotionBodyAsset.Get()!=Body->GetSkeletalMeshAsset()){MotionMaps.Reset();MotionBodyAsset=Body->GetSkeletalMeshAsset();}
    for(int32 I=0;I<MotionMaps.Num();++I)if(MotionMaps[I].Source==Source&&MotionMaps[I].Hand==Hand&&MotionMaps[I].Side==Side)
    {if(MotionMaps[I].SourceAsset==Source->GetSkeletalMeshAsset())return &MotionMaps[I].Rig;MotionMaps.RemoveAt(I);break;}
    auto& Map=MotionMaps.AddDefaulted_GetRef();Map.Source=Source;Map.SourceAsset=Source->GetSkeletalMeshAsset();Map.Hand=Hand;Map.Side=Side;
    Map.Rig.Initialize(Source->GetSkeletalMeshAsset()->GetRefSkeleton(),Body->GetSkeletalMeshAsset()->GetRefSkeleton(),Hand,Side==0?TEXT("hand_r"):TEXT("hand_l"));
    if(Side==0&&Hand==TEXT("hand_r")&&Cast<UStaffArmsMeshComponent>(Source))
        if(const auto* Staff=Source->GetOwner()->FindComponentByClass<UStaffWeaponComponent>())
            FPSBodyStaffGrip::AdaptMount(Map.Rig,Staff->GripVariant());
    AddTickPrerequisiteComponent(Source);
    return &Map.Rig;
}
void UFPSPlayerBodyComponent::CaptureMotionHand(USkeletalMeshComponent* Source,FName Hand,int32 Side,bool Wrist,FFPSBodyMotionSample& Sample,const TArray<FTransform>* PoseOverride)
{
    auto* Map=MotionMap(Source,Hand,Side);if(!Map||!Map->IsValid())return;
    const auto& Pose=PoseOverride?*PoseOverride:Source->GetComponentSpaceTransforms();if(!Pose.IsValidIndex(Map->SourceHand))return;
    TArray<FTransform> Native;
    if(Side==0&&Hand==TEXT("hand_r")&&Cast<UStaffArmsMeshComponent>(Source))
    {
        const auto* Staff=Source->GetOwner()->FindComponentByClass<UStaffWeaponComponent>();
        FPSBodyStaffGrip::Transfer(*Map,Source->GetSkeletalMeshAsset()->GetRefSkeleton(),Pose,Native,Staff?Staff->GripVariant():0);
    }
    if(Native.IsEmpty())Map->Transfer(Pose,Native);
    if(Native.IsEmpty())return;
    Sample.Fingers|=1<<Side;
    for(int32 D=0;D<Map->Digits.Num();++D)for(int32 J=0;J<3;++J)
        Sample.Hands[Side].Fingers[D*3+J]=Native[Map->Digits[D].Target[J]].GetRotation();
    if(Wrist)
    {
        Sample.Wrists|=1<<Side;
        // The gameplay eye stays at the character in F6; these are body-space
        // contacts, independent of the third-person observation camera.
        Sample.Hands[Side].Wrist=BodyMotionRigidTransform(Map->Mount.Inverse()*BodyMotionRigidTransform(Pose[Map->SourceHand])
            *Source->GetComponentTransform().GetRelativeTransform(GetBodyMesh()->GetComponentTransform()));
    }
}
void UFPSPlayerBodyComponent::CaptureMotion(FFPSBodyState& State)
{
    auto& Sample=State.Contacts;Sample=FFPSBodyMotionSample();auto* Pawn=Character.Get();if(!Pawn||!GetBodyMesh())return;
    const auto* Magic=Pawn->FindComponentByClass<UFPSFireballComponent>();
    const auto* Quick=Pawn->FindComponentByClass<UFPSQuickCombatComponent>();
    const auto* Book=Pawn->FindComponentByClass<USpellbookComponent>();
    const bool BookFocus=Book&&Book->IsFocusActive();
    if(BookFocus)if(auto* Pages=Book->FloatingBookMesh();Drawn(Pages)&&Pages->GetSkeletalMeshAsset())
    {
        Sample.FloatingBook=true;
        Sample.BookFrame=Pages->GetComponentTransform().GetRelativeTransform(GetBodyMesh()->GetComponentTransform());
        Sample.BookPose=Pages->GetComponentSpaceTransforms();
        Sample.BookGold=FVector3f(Book->FocusGoldParameters());
    }
    const auto* Staff=Pawn->FindComponentByClass<UStaffWeaponComponent>();
    const auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();
    const auto* Bipod=Pawn->FindComponentByClass<UWeaponBipodDeploymentComponent>();
    auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>();
    auto* Door=Pawn->FindComponentByClass<UFPSDoorPushComponent>();
    const bool Reload=State.Action==EFPSBodyAction::Reload||State.Action==EFPSBodyAction::ReloadEmpty;
    const bool Inspect=State.Action==EFPSBodyAction::Inspect;
    const bool Cast=Magic&&Magic->IsGestureActive();
    const bool Bash=Quick&&Quick->IsOccupyingLeftHand();
    const bool Mount=Bipod&&Bipod->GetDeploymentBlend()>0.f;
    Sample.Channel=Reload?FName(TEXT("Reload")):Inspect?FName(TEXT("Inspect")):FName(NAME_None);
    if(Mount)Sample.Channel=TEXT("Bipod");
    if(Staff&&Staff->IsEquipped())
    {
        Sample.Light=StaffCastMotion::Ease(Staff->IlluminationBlend);
        if(Staff->IlluminationGestureAge>=0.f){Sample.Channel=TEXT("StaffLight");State.Action=EFPSBodyAction::StaffLight;}
        if(Bash){Sample.Channel=Pawn->HasOffhandPistol()?TEXT("StaffOffhandBash"):TEXT("StaffPunch");State.ActionVariant=Sample.Channel;}
        // Channel identifies the casting hand; ActionVariant retains the real
        // Gather/Ready/Release/Recover phase published by the spell executor.
        if(Cast&&Magic->IsStaffCasting())Sample.Channel=TEXT("StaffCast");
    }
    else if(Cast)Sample.Channel=TEXT("Cast");
    else if(Bash&&State.Family==TEXT("Unarmed"))Sample.Channel=TEXT("Fist");
    if(Bash&&Quick->GetStyle()==EQuickCombatStyle::SpellbookPush)
    {Sample.Channel=TEXT("SpellbookPush");State.ActionVariant=Sample.Channel;}
    Sample.Rigs.SetNum(FMath::Min(LocalWeapons.Num(),2));
    for(int32 I=0;I<Sample.Rigs.Num();++I)
    {
        const auto& D=LocalWeapons[I];auto& Rig=Sample.Rigs[I];auto* Source=D.Source.Get();
        if(D.PoseFamily==TEXT("Bow"))continue; // bow owns its existing marker/string sampler
        if(D.PoseFamily.IsNone()&&!Inspect)continue;
        if(D.PoseFamily==TEXT("Spellbook")&&!Drawn(Source))
        {
            Rig.Valid=true;Rig.Schema=D.MotionSchema;Rig.Visible=false;
            continue; // the primary's support hand owns reload/inspection while the book is stowed
        }
        const int32 Side=D.AttachHand;auto* Map=MotionMap(Source,D.GripBone,Side);
        if(!Map||!Map->IsValid())continue;
        const FName FullBodyClip=FPSBodySwordMotion::Clip(State);
        const bool FullBodySword=D.PoseFamily==TEXT("Sword")&&BodyAnimation&&
            !FullBodyClip.IsNone()&&BodyAnimation->Clips.FindRef(FullBodyClip);
        UFPSBodyWeaponMeshComponent* CarryRig=nullptr;
        if(D.PoseFamily==TEXT("Sword")&&Sword&&MotionBindings.IsValidIndex(I))
        {
            auto& Binding=MotionBindings[I];
            const bool Ordinary=State.Action==EFPSBodyAction::None&&(Sword->CurrentClip==TEXT("Idle")
                ||Sword->CurrentClip==TEXT("Walk")||Sword->IsTacticalSprintClip(Sword->CurrentClip));
            const bool Moving=Pawn->GetCharacterMovement()->IsMovingOnGround()&&!State.bSliding
                &&Pawn->GetVelocity().SizeSquared2D()>400.f;
            const FName ClipName=Moving?TEXT("Walk"):TEXT("Idle");
            auto* Clip=Ordinary?Sword->Animations.FindRef(ClipName).Get():nullptr;
            if(Clip&&Binding.Mesh.IsValid())
            {
                CarryRig=Binding.Mesh.Get();
                if(Binding.LocomotionClip!=ClipName)
                {
                    // ApplyMotion publishes mechanical bones over a frozen hand pose.
                    // Restore the last complete carry before capturing an idle/walk blend.
                    if(!Binding.LocomotionPose.IsEmpty())
                    {
                        CarryRig->PublishMechanicalPose(Binding.LocomotionPose);
                        CarryRig->CaptureHoldTransition(.12f);
                    }
                    else CarryRig->CaptureHoldTransition(0.f);
                    CarryRig->PlayAnimation(Clip,true);CarryRig->SetPlayRate(0.f);
                    Binding.LocomotionClip=ClipName;Binding.LocomotionTime=0.f;
                }
                const float Delta=GetWorld()->GetDeltaSeconds();
                Binding.LocomotionTime=FMath::Fmod(Binding.LocomotionTime+Delta*(Moving&&State.bSprinting?1.45f:1.f),FMath::Max(.01f,Clip->GetPlayLength()));
                CarryRig->AdvanceHoldTransition(Delta);
                CarryRig->SetPosition(Binding.LocomotionTime,false);CarryRig->TickAnimation(0.f,false);CarryRig->RefreshBoneTransforms();
                Binding.LocomotionPose=CarryRig->GetComponentSpaceTransforms();
                State.ActionVariant=ClipName;
            }
            else {Binding.LocomotionClip=NAME_None;Binding.LocomotionPose.Reset();}
        }
        // Both wrists, fingers, blade bones and socket attachments use this same
        // ordinary carry sample. Sprint enter/loop/exit cannot leak through parts.
        // An authored third-person action owns the wrists. Use only the frozen
        // equipment bind for fingers, sword bones and attachments; an FPS swing
        // must not rotate the blade a second time after the body has moved it.
        const bool FrozenSword=FullBodySword&&MotionBindings.IsValidIndex(I)&&!MotionBindings[I].FrozenPose.IsEmpty();
        const auto& SourcePose=FrozenSword?MotionBindings[I].FrozenPose:
            (CarryRig?CarryRig->GetComponentSpaceTransforms():Source->GetComponentSpaceTransforms());
        const FTransform NativeMount=Map->Mount; // CaptureMotionHand may grow the map array.
        const int32 SourceHand=Map->SourceHand;
        const bool NativeMelee=(D.PoseFamily==TEXT("Sword")&&!FrozenSword)||D.PoseFamily==TEXT("Tool");
        const bool StaffAction=D.PoseFamily==TEXT("Staff")&&(Cast||Bash||Staff->IlluminationGestureAge>=0.f||Staff->IsEquipping()||Staff->IsPrimaryAttacking());
        const auto& HandState=Side==0?State.RightHand:State.LeftHand;
        const bool Drive=NativeMelee||Reload||Inspect||Mount||StaffAction||(Side==1&&(Bash||BookFocus))||HandState.bReloading||HandState.bEquipping
            ||(D.PoseFamily==TEXT("Gun")&&State.Action==EFPSBodyAction::Equip);
        const bool Rifle=State.Family==TEXT("Rifle")&&D.PoseFamily==TEXT("Gun")&&I==0;
        const TArray<FTransform>* RifleCarryPose=nullptr;
        // A firing M870's support palm follows its moving fore-end. Capture
        // that live grip relation while the world-body rifle hold still owns
        // both arm targets and aim; no camera-space wrist targets are driven.
        const bool PumpingM870=Rifle&&Pawn->IsM870Weapon()&&Pawn->IsRevolverFireActionPlaying();
        // Preserve the complete pump as an active network presentation, even
        // though it intentionally leaves gameplay action/ADS in Idle.
        if(PumpingM870&&!Drive&&Sample.Channel.IsNone())Sample.Channel=TEXT("Pump");
        if(Rifle&&!Drive&&!PumpingM870&&MotionBindings.IsValidIndex(I))
        {
            auto& Binding=MotionBindings[I];const int32 Root=Binding.NativeWeaponRoot;
            if(Binding.FrozenPose.IsValidIndex(Root)&&SourcePose.IsValidIndex(Root))
            {
                // FPS tactical sprint releases the support hand. The world
                // rifle keeps its complete hold on the current weapon frame;
                // mechanical bones below still use the live firing sample.
                Binding.LocomotionPose=Binding.FrozenPose;
                const FTransform From=BodyMotionRigidTransform(Binding.FrozenPose[Root]);
                const FTransform To=BodyMotionRigidTransform(SourcePose[Root]);
                for(auto& Bone:Binding.LocomotionPose)Bone=Bone.GetRelativeTransform(From)*To;
                RifleCarryPose=&Binding.LocomotionPose;
            }
        }
        const auto& Pose=RifleCarryPose?*RifleCarryPose:SourcePose;
        if(!Pose.IsValidIndex(SourceHand))continue;
        Rig.Valid=true;Rig.Schema=D.MotionSchema;
        const FTransform Hand=BodyMotionRigidTransform(Pose[SourceHand]);
        CaptureMotionHand(Source,D.GripBone,Side,Drive,Sample,&Pose);
        const bool BookStowed=Pawn->HasOffhandSpellbook()&&!Pawn->IsOffhandSpellbookPresented();
        if(I==0&&(LocalWeapons.Num()==1||BookStowed)&&D.PoseFamily!=TEXT("Staff")&&D.PoseFamily!=TEXT("Spellbook"))
        {
            CaptureMotionHand(Source,TEXT("hand_l"),1,Drive,Sample,&Pose);Sample.CoupledWrists=Drive;
            if(const auto* Left=MotionMap(Source,TEXT("hand_l"),1);Left&&Left->IsValid()&&Pose.IsValidIndex(Left->SourceHand))
            {
                Sample.HasSupportGrip=true;
                Sample.SupportGrip=Left->Mount.Inverse()*BodyMotionRigidTransform(Pose[Left->SourceHand]).GetRelativeTransform(Hand)*NativeMount;
            }
        }
        if(NativeMelee&&MotionBindings.IsValidIndex(I)&&MotionBindings[I].FrozenPose.IsValidIndex(SourceHand))
        {
            // Reuse the complete authored swing, not an idle grip plus a pulse.
            // Rebase its hand trajectory around a world-body ready position:
            // the FPS camera's eye height/feedback must not pin both hands to the face.
            const FTransform Ready=NativeMount.Inverse()*BodyMotionRigidTransform(MotionBindings[I].FrozenPose[SourceHand]);
            const FTransform Current=NativeMount.Inverse()*Hand;
            const FQuat Frame=(GetBodyMesh()->GetComponentQuat().Inverse()*
                FRotator(State.AimPitch,Pawn->GetActorRotation().Yaw,0.f).Quaternion()*FRotator(0,90,0).Quaternion()).GetNormalized();
            const FVector Scale=BodyAnimation?BodyAnimation->PoseScale:FVector::OneVector;
            const float Crouch=BodyAnimation?BodyAnimation->CrouchAlpha:(State.bCrouched?1.f:0.f);
            const FVector Offset=Frame.RotateVector(Current.GetLocation()-Ready.GetLocation())*Scale;
            const FVector ReadyPosition=D.PoseFamily==TEXT("Sword")?FPSBodyPoses::SwordReady(Crouch):FVector(-18,43,111-40*Crouch);
            Sample.Hands[0].Wrist=FTransform((Frame*Current.GetRotation()).GetNormalized(),ReadyPosition*Scale+Offset);
            if(Sample.HasSupportGrip)
                Sample.Hands[1].Wrist=Sample.SupportGrip*Sample.Hands[0].Wrist;
        }
        if(Rifle&&Drive&&FPSBodyRifleMotion::UsesHoldSpace(State)&&Sample.CoupledWrists&&
            MotionBindings.IsValidIndex(I)&&MotionBindings[I].FrozenPose.IsValidIndex(SourceHand))
        {
            const FTransform Ready=NativeMount.Inverse()*BodyMotionRigidTransform(MotionBindings[I].FrozenPose[SourceHand]);
            const FTransform Current=NativeMount.Inverse()*Hand;
            Sample.Hands[0].Wrist=Current.GetRelativeTransform(Ready);
            Sample.Hands[1].Wrist=Sample.SupportGrip*Sample.Hands[0].Wrist;
        }
        // Rifle mechanisms and attachments travel in the owning wrist's frame.
        // Interpolating a moving inverse wrist and absolute bones separately
        // otherwise pulls the magazine away from the sampled support hand.
        Rig.Root=Rifle?NativeMount:Hand.Inverse()*NativeMount;
        Rig.Visible=Drawn(Source);
        Rig.ReloadPropVisible=Drawn(D.ReloadPropSource.Get());
        if(auto* Static=D.StaticSource.Get())
        {
            Rig.Root=Static->GetComponentTransform().GetRelativeTransform(BodyMotionRigidTransform(Hand*Source->GetComponentTransform()))*NativeMount;
            Rig.Visible=Drawn(Static);
        }
        // The consumable owns the left wrist while its equipped gun is stowed.
        // Carry this visibility to the world body and remote presentation too.
        if(Side==1&&Potion&&Potion->IsOffhandWeaponHidden())Rig.Visible=false;
        for(int32 Bone:D.MotionBones)
        {
            const FTransform Transform=SourcePose.IsValidIndex(Bone)?SourcePose[Bone]:FTransform::Identity;
            Rig.Bones.Add(Rifle?Transform.GetRelativeTransform(Hand):Transform);
        }
        for(int32 P=0;P<D.SourceParts.Num();++P)
        {
            auto* Part=D.SourceParts[P].Get();
            if(FrozenSword&&MotionBindings[I].FrozenParts.IsValidIndex(P))
                Rig.Parts.Add(MotionBindings[I].FrozenParts[P]);
            else if(CarryRig&&Part&&D.Parts.IsValidIndex(P))
            {
                const FName Socket=D.Parts[P].Socket;
                const FTransform Local=Part->GetComponentTransform().GetRelativeTransform(Source->GetSocketTransform(Socket));
                Rig.Parts.Add(Local*CarryRig->GetSocketTransform(Socket,RTS_Component));
            }
            else Rig.Parts.Add(Part?Part->GetComponentTransform().GetRelativeTransform(
                D.StaticSource.IsValid()?D.StaticSource->GetComponentTransform():Source->GetComponentTransform()):FTransform::Identity);
            if(Rifle)Rig.Parts.Last()=Rig.Parts.Last().GetRelativeTransform(Hand);
            Rig.VisibleParts.Add(Drawn(Part)?1:0);
        }
        Rig.Sections=0;
        for(int32 M=0;M<FMath::Min(32,Source->GetNumMaterials());++M)
            if(Source->IsMaterialSectionShown(M,0))Rig.Sections|=1u<<M;
    }
    // The cached FPS unarmed fist owns ordinary staff carry/run. Sample the
    // live left hand only when its actual action takes over that free hand.
    if(Staff&&Staff->IsEquipped()&&!Pawn->HasOffhandPistol()&&!Pawn->IsOffhandSpellbookPresented()
        &&(Bash||Staff->IlluminationGestureAge>=0.f))
        CaptureMotionHand(Staff->ArmsMesh(),TEXT("hand_l"),1,Bash,Sample);
    if(auto* Unarmed=Pawn->FindComponentByClass<UFPSUnarmedIdleComponent>();Unarmed&&Unarmed->IsEquipped())
        for(int32 Side=0;Side<(Pawn->HasOffhandSpellbook()?1:2);++Side)CaptureMotionHand(Unarmed->Arms,Side==0?TEXT("hand_r"):TEXT("hand_l"),Side,Bash,Sample);
    // Native overlays run after base weapon motion. Read their actual owning mesh.
    if(Cast&&!Magic->IsStaffCasting())
    {
        Sample.CoupledWrists=false;
        TInlineComponentArray<UFPSCastingMeshComponent*> Sources(Pawn);
        for(auto* Source:Sources)if(Source->bApplyLeftHandCast&&Drawn(Source)&&Source->GetSkeletalMeshAsset())
        {CaptureMotionHand(Source,TEXT("hand_l"),1,true,Sample);break;}
    }
    if(Door&&Door->IsActive())
    {
        Sample.Channel=TEXT("Door");State.Action=EFPSBodyAction::DoorPush;
        Sample.CoupledWrists=false;
        CaptureMotionHand(Door->ActiveHands.Get(),TEXT("hand_l"),1,true,Sample);
    }
    if(Potion&&LocalConsumableSerial!=Potion->PresentationSerial)
    {LocalConsumableSerial=Potion->PresentationSerial;PendingDiscardFlags=0;bPendingBottleDrop=false;}
    if(Potion&&!Potion->IsActive()&&ServerClock()>PendingDiscardUntil)PendingDiscardFlags=0;
    if(Potion&&(Potion->IsActive()||PendingDiscardFlags))
    {
        Sample.Channel=TEXT("Consume");State.Action=EFPSBodyAction::Consume;
        // Both views follow the item's real use clock, including offhand stow.
        // Body markers retime the donor; no animation notify consumes an item.
        const auto& Use=Potion->Motion;const float Age=Potion->Age();
        State.ActionVariant=Potion->PresentationDefinition;
        State.ActionDuration=Use.Duration;State.ActionStartedAt=ServerClock()-Age;
        State.bHasActionProgress=true;
        State.ActionProgress=FMath::Clamp(Age/FMath::Max(Use.Duration,SMALL_NUMBER),0.f,1.f);
        State.ActionWeight=Potion->IsActive()?Use.Layer(Age):0.f;
        State.ContactFraction=Use.DrinkStart/Use.Duration;
        State.ReleaseFraction=Use.DrinkEnd/Use.Duration;
        State.ActionEntryFraction=Use.Grab/Use.Duration;
        Sample.Consumable=Potion->PresentationDefinition;Sample.ConsumableSerial=Potion->PresentationSerial;
        Sample.DiscardFlags=PendingDiscardFlags;
        Sample.DroppedBottle=bPendingBottleDrop;Sample.CoupledWrists=false;
        if(!Potion->IsActive())
        {
            for(int32 I=0;I<3;++I)Sample.Props[I]=PreviousLocalPresentation.Contacts.Props[I];
            Sample.Hands[1]=PreviousLocalPresentation.Contacts.Hands[1];Sample.Fingers|=2;
            // Preserve the release frame for a cancelled bottle. Subsequent
            // frames recover through the normal body hand transition.
            if((PendingDiscardFlags&~PreviousLocalPresentation.Contacts.DiscardFlags)!=0)Sample.Wrists|=2;
        }
        auto* Source=Potion->ActiveHands.Get();CaptureMotionHand(Source,TEXT("hand_l"),1,true,Sample);
        if(auto* Map=MotionMap(Source,TEXT("hand_l"),1);Map&&Map->IsValid())
        {
            const FTransform Hand=BodyMotionRigidTransform(Source->GetSocketTransform(TEXT("hand_l")));
            UStaticMeshComponent* Parts[]={Potion->Bottle,Potion->Liquid,Potion->Stopper};
            for(int32 Part=0;Part<3;++Part)if(Parts[Part])
            {
                Sample.Props[Part]=Parts[Part]->GetComponentTransform().GetRelativeTransform(Hand)*Map->Mount;
                if(Drawn(Parts[Part]))Sample.PropVisibility|=1<<Part;
            }
            Sample.LiquidLevel=Potion->LastWaterLevel;
        }
    }
    else PendingDiscardFlags=0;
    if(FPSBodyPoses::Traversing(State.Motion)||State.Action==EFPSBodyAction::Dead)
    {Sample.Wrists=Sample.Fingers=0;Sample.PropVisibility=0;Sample.HasSupportGrip=false;Sample.Light=0.f;Sample.FloatingBook=false;Sample.BookPose.Reset();}
}

bool UFPSPlayerBodyComponent::HasMatchingMotionRig(int32 Index) const
{
    if(!MotionBindings.IsValidIndex(Index)||!DisplayState.Contacts.Rigs.IsValidIndex(Index))return false;
    const auto& Binding=MotionBindings[Index];const auto& Rig=DisplayState.Contacts.Rigs[Index];
    const auto& Weapon=Binding.Definition;
    const FString& Instance=Weapon.AttachHand==1?DisplayState.OffhandInstance:DisplayState.WeaponInstance;
    return Rig.Valid&&Rig.Schema==Weapon.MotionSchema&&Rig.Bones.Num()==Weapon.MotionBones.Num()
        &&Rig.Parts.Num()==Binding.Parts.Num()&&(Weapon.GunInstance.IsEmpty()||Weapon.GunInstance==Instance);
}

void UFPSPlayerBodyComponent::ApplyMotion(float Delta)
{
    if(!BodyAnimation||!GetBodyMesh()||!GetBodyMesh()->GetSkeletalMeshAsset())return;
    const auto& Incoming=DisplayState.Contacts;
    const bool Local=Character.IsValid()&&Character->IsLocallyControlled();
    const float Alpha=Local||!bMotionSampleValid?1.f:1.f-FMath::Exp(-35.f*Delta);
    for(int32 Side=0;Side<2;++Side)
    {
        auto& H=SmoothedContacts.Hands[Side];const auto& Next=Incoming.Hands[Side];
        H.Wrist.Blend(H.Wrist,Next.Wrist,(SmoothedContacts.Wrists&(1<<Side))?Alpha:1.f);
        for(int32 J=0;J<15;++J)H.Fingers[J]=FQuat::Slerp(H.Fingers[J],Next.Fingers[J],Alpha).GetNormalized();
        BodyAnimation->ActionHands[Side]=H.Wrist;
    }
    SmoothedContacts.Wrists=Incoming.Wrists;bMotionSampleValid=true;
    BodyAnimation->ActionFingerMask=Incoming.Fingers;BodyAnimation->ActionWristMask=Incoming.Wrists;
    BodyAnimation->bCoupledActionWrists=Incoming.CoupledWrists;
    // Equipment and pose properties can arrive in either order. Never apply an
    // old pump's support target to the new gun while its mechanical rig rejects it.
    const bool SupportReady=Incoming.HasSupportGrip&&HasMatchingMotionRig(0);
    if(SupportReady)
    {
        SmoothedContacts.SupportGrip.Blend(SmoothedContacts.SupportGrip,Incoming.SupportGrip,SmoothedContacts.HasSupportGrip?Alpha:1.f);
        BodyAnimation->LeftGripFromRight=SmoothedContacts.SupportGrip;
    }
    else if(SmoothedContacts.HasSupportGrip)BodyAnimation->LeftGripFromRight=BaseSupportGrip;
    SmoothedContacts.HasSupportGrip=SupportReady;
    const auto& Ref=GetBodyMesh()->GetSkeletalMeshAsset()->GetRefSkeleton();
    if(MotionFingerAsset!=GetBodyMesh()->GetSkeletalMeshAsset())
    {
        MotionFingerAsset=GetBodyMesh()->GetSkeletalMeshAsset();
        for(int32 Side=0;Side<2;++Side)
        {
            MotionHalfBones[Side].Reset();int32 D=0;
            for(const TCHAR* Digit:{TEXT("thumb"),TEXT("index"),TEXT("middle"),TEXT("ring"),TEXT("pinky")})
            {
                for(int32 J=0;J<3;++J)
                {
                    const int32 Bone=Ref.FindBoneIndex(*FString::Printf(TEXT("%s_%02d_%s"),Digit,J+1,Side==0?TEXT("r"):TEXT("l")));
                    MotionFingerBones[Side][D*3+J]=Bone;
                    if(Bone!=INDEX_NONE)for(int32 B=Bone+1;B<Ref.GetNum();++B)
                        if(Ref.GetParentIndex(B)==Bone&&Ref.GetBoneName(B).ToString().Contains(TEXT("_half_")))MotionHalfBones[Side].Emplace(B,Bone);
                }
                ++D;
            }
        }
    }
    BodyAnimation->ActionFingers=Ref.GetRefBonePose();
    if(DisplayState.Family==TEXT("Staff")&&(Incoming.Fingers&1)&&
        (BodyAnimation->EquipmentGripHands&1)&&BodyAnimation->EquipmentFingers.Num()==Ref.GetNum())
    {
        // The existing contact packet carries fifteen joints. The staff palm
        // fan belongs to the equipped native grip and is identical on owner
        // and remote bodies; preserve it before overlaying those live joints.
        for(int32 D=1;D<5;++D)
        {
            const int32 Finger=MotionFingerBones[0][D*3];
            if(Finger==INDEX_NONE)continue;
            const int32 Palm=Ref.GetParentIndex(Finger);
            if(Palm!=INDEX_NONE)BodyAnimation->ActionFingers[Palm]=BodyAnimation->EquipmentFingers[Palm];
        }
    }
    for(int32 Side=0;Side<2;++Side)if(Incoming.Fingers&(1<<Side))
    {
        for(int32 J=0;J<15;++J)
        {
            const int32 Bone=MotionFingerBones[Side][J];if(Bone!=INDEX_NONE)BodyAnimation->ActionFingers[Bone].SetRotation(SmoothedContacts.Hands[Side].Fingers[J]);
        }
        for(const auto& Half:MotionHalfBones[Side])
        {
            const FQuat Change=Ref.GetRefBonePose()[Half.Value].GetRotation().Inverse()*BodyAnimation->ActionFingers[Half.Value].GetRotation();
            BodyAnimation->ActionFingers[Half.Key].SetRotation((FQuat::Slerp(FQuat::Identity,Change.Inverse(),.5f)*Ref.GetRefBonePose()[Half.Key].GetRotation()).GetNormalized());
        }
    }
    const FFPSBodyMotionRig Empty;
    for(int32 I=0;I<MotionBindings.Num();++I)
    {
        auto& Binding=MotionBindings[I];const auto& R=Incoming.Rigs.IsValidIndex(I)?Incoming.Rigs[I]:Empty;
        if(Binding.Definition.PoseFamily==TEXT("Bow"))continue;
        auto* Root=Binding.Mesh.IsValid()?static_cast<UPrimitiveComponent*>(Binding.Mesh.Get()):Binding.Static.Get();if(!Root)continue;
        if(!HasMatchingMotionRig(I))
        {
            if(auto* Prop=Binding.ReloadProp.Get())
            {Prop->SetVisibility(false);Prop->SetHiddenInGame(true);FPSBodyEquipment::ApplyShadowFlags(Prop,false);}
            if(Binding.Smoothed.Valid)
            {
                Root->SetRelativeTransform(Binding.Mount);
                if(auto* Mesh=Binding.Mesh.Get())
                {
                    Mesh->PublishMechanicalPose(Binding.FrozenPose);
                    if(TubeShotgunAssets::MatchesMesh(Binding.Definition.Mesh.ToSoftObjectPath().ToString()))
                        Super90WeaponAssets::SetLooseShellVisible(Mesh,false);
                }
                for(int32 P=0;P<Binding.Parts.Num();++P)if(Binding.Parts[P].IsValid())Binding.Parts[P]->SetRelativeTransform(Binding.FrozenParts[P]);
                Binding.Smoothed.Valid=false;Binding.bHasSections=false;
            }
            for(int32 P=0;P<Binding.Parts.Num();++P)if(auto* Part=Binding.Parts[P].Get())
            {
                const bool Show=Root->IsVisible()&&!Root->bHiddenInGame&&Binding.Definition.Parts[P].bVisible;
                if(Part->IsVisible()!=Show)Part->SetVisibility(Show);
                if(Part->bHiddenInGame==Show)Part->SetHiddenInGame(!Show);
                FPSBodyEquipment::ApplyShadowFlags(Part,Show&&ShouldWorldBodyCastShadow());
            }
            continue;
        }
        auto& Smooth=Binding.Smoothed;
        if(!Smooth.Valid||Smooth.Bones.Num()!=R.Bones.Num()||Smooth.Parts.Num()!=R.Parts.Num())Smooth=R;
        else
        {
            Smooth.Root.Blend(Smooth.Root,R.Root,Alpha);
            for(int32 B=0;B<R.Bones.Num();++B)Smooth.Bones[B].Blend(Smooth.Bones[B],R.Bones[B],Alpha);
            for(int32 P=0;P<R.Parts.Num();++P)Smooth.Parts[P].Blend(Smooth.Parts[P],R.Parts[P],Alpha);
        }
        Root->SetRelativeTransform(Smooth.Root);
        const bool Visible=R.Visible&&!IsWorldWeaponStowed(Root)&&!FPSPlayerBodyWorldBodyHidden();
        if(Root->IsVisible()!=Visible)Root->SetVisibility(Visible);
        if(Root->bHiddenInGame==Visible)Root->SetHiddenInGame(!Visible);
        if(auto* Prop=Binding.ReloadProp.Get())
        {
            const bool Show=Visible&&R.ReloadPropVisible;
            if(Prop->IsVisible()!=Show)Prop->SetVisibility(Show);
            if(Prop->bHiddenInGame==Show)Prop->SetHiddenInGame(!Show);
            FPSBodyEquipment::ApplyShadowFlags(Prop,Show&&ShouldWorldBodyCastShadow());
        }
        FPSBodyEquipment::ApplyShadowFlags(Root,Visible&&ShouldWorldBodyCastShadow());
        if(auto* Mesh=Binding.Mesh.Get())
        {
            auto Pose=Binding.FrozenPose;
            for(int32 B=0;B<R.Bones.Num();++B)if(Pose.IsValidIndex(Binding.Definition.MotionBones[B]))Pose[Binding.Definition.MotionBones[B]]=Smooth.Bones[B];
            Mesh->PublishMechanicalPose(Pose);
            if(auto* Prop=Binding.ReloadProp.Get())Prop->MarkRenderDynamicDataDirty();
            if(const auto* Render=Mesh->GetSkeletalMeshAsset()->GetResourceForRendering();Render&&(!Binding.bHasSections||Binding.LastSections!=R.Sections))
            {
                for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
                {
                    const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                    Mesh->ShowMaterialSection(M,S,!Binding.Definition.HiddenMaterials.Contains(M)&&(M>=32||(R.Sections&(1u<<M))),L);
                }
                Binding.bHasSections=true;Binding.LastSections=R.Sections;
            }
        }
        for(int32 P=0;P<Binding.Parts.Num();++P)if(auto* Part=Binding.Parts[P].Get())
        {
            Part->SetRelativeTransform(Smooth.Parts[P]);const bool Show=Visible&&R.VisibleParts[P];
            if(Part->IsVisible()!=Show)Part->SetVisibility(Show);
            if(Part->bHiddenInGame==Show)Part->SetHiddenInGame(!Show);
            FPSBodyEquipment::ApplyShadowFlags(Part,Show&&ShouldWorldBodyCastShadow());
        }
    }
    UpdateConsumable(Incoming);
    UpdateFloatingBook(Incoming,Alpha);
    if(WorldStaffLight&&LastWorldLight!=Incoming.Light)
    {
        LastWorldLight=Incoming.Light;WorldStaffLight->SetIntensity(1000.f*Incoming.Light);
        for(const auto& Material:WorldStaffMaterials)if(Material)Material->SetScalarParameterValue(TEXT("StaffLightAmount"),3.f*Incoming.Light);
    }
    if(WorldStaffLight)
    {
        const bool Visible=Incoming.Light>0.f&&(!Local||IsThirdPersonViewEnabled())&&!FPSPlayerBodyWorldBodyHidden();
        if(WorldStaffLight->IsVisible()!=Visible)WorldStaffLight->SetVisibility(Visible);
    }
}
