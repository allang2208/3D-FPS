#include "FPSPlayerBodyComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "FPSPlayerBodyPoses.h"
#include "../FPSGAMECharacter.h"
#include "../Items/FPSPotionUseComponent.h"
#include "../Movement/FPSDoorPushComponent.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "../Weapons/WeaponBipodDeploymentComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffArmsMeshComponent.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace
{
FTransform Rigid(FTransform T){T.SetScale3D(FVector::OneVector);return T;}
bool Drawn(const UPrimitiveComponent* C){return C&&C->IsVisible()&&!C->bHiddenInGame;}
}

FFPSBodyGripRig* UFPSPlayerBodyComponent::MotionMap(USkeletalMeshComponent* Source,FName Hand,int32 Side)
{
    auto* Body=GetBodyMesh();if(!Source||!Source->GetSkeletalMeshAsset()||!Body||!Body->GetSkeletalMeshAsset())return nullptr;
    if(MotionBodyAsset.Get()!=Body->GetSkeletalMeshAsset()){MotionMaps.Reset();MotionBodyAsset=Body->GetSkeletalMeshAsset();}
    for(int32 I=0;I<MotionMaps.Num();++I)if(MotionMaps[I].Source==Source&&MotionMaps[I].Hand==Hand&&MotionMaps[I].Side==Side)
    {if(MotionMaps[I].SourceAsset==Source->GetSkeletalMeshAsset())return &MotionMaps[I].Rig;MotionMaps.RemoveAt(I);break;}
    auto& Map=MotionMaps.AddDefaulted_GetRef();Map.Source=Source;Map.SourceAsset=Source->GetSkeletalMeshAsset();Map.Hand=Hand;Map.Side=Side;
    Map.Rig.Initialize(Source->GetSkeletalMeshAsset()->GetRefSkeleton(),Body->GetSkeletalMeshAsset()->GetRefSkeleton(),Hand,Side==0?TEXT("hand_r"):TEXT("hand_l"));
    AddTickPrerequisiteComponent(Source);
    return &Map.Rig;
}
void UFPSPlayerBodyComponent::CaptureMotionHand(USkeletalMeshComponent* Source,FName Hand,int32 Side,bool Wrist,FFPSBodyMotionSample& Sample)
{
    auto* Map=MotionMap(Source,Hand,Side);if(!Map||!Map->IsValid())return;
    const auto& Pose=Source->GetComponentSpaceTransforms();if(!Pose.IsValidIndex(Map->SourceHand))return;
    TArray<FTransform> Native;Map->Transfer(Pose,Native);if(Native.IsEmpty())return;
    Sample.Fingers|=1<<Side;
    for(int32 D=0;D<Map->Digits.Num();++D)for(int32 J=0;J<3;++J)
        Sample.Hands[Side].Fingers[D*3+J]=Native[Map->Digits[D].Target[J]].GetRotation();
    if(Wrist)
    {
        Sample.Wrists|=1<<Side;
        // The gameplay eye stays at the character in F6; these are body-space
        // contacts, independent of the third-person observation camera.
        Sample.Hands[Side].Wrist=Rigid(Map->Mount.Inverse()*Rigid(Pose[Map->SourceHand])
            *Source->GetComponentTransform().GetRelativeTransform(GetBodyMesh()->GetComponentTransform()));
    }
}
void UFPSPlayerBodyComponent::CaptureMotion(FFPSBodyState& State)
{
    auto& Sample=State.Contacts;Sample=FFPSBodyMotionSample();auto* Pawn=Character.Get();if(!Pawn||!GetBodyMesh())return;
    const auto* Magic=Pawn->FindComponentByClass<UFPSFireballComponent>();
    const auto* Quick=Pawn->FindComponentByClass<UFPSQuickCombatComponent>();
    const auto* Staff=Pawn->FindComponentByClass<UStaffWeaponComponent>();
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
        if(Cast){Sample.Channel=TEXT("StaffCast");State.Action=EFPSBodyAction::Cast;State.ActionVariant=TEXT("StaffCast");}
    }
    else if(Cast)Sample.Channel=TEXT("Cast");
    else if(Bash&&State.Family==TEXT("Unarmed"))Sample.Channel=TEXT("Fist");
    Sample.Rigs.SetNum(FMath::Min(LocalWeapons.Num(),2));
    for(int32 I=0;I<Sample.Rigs.Num();++I)
    {
        const auto& D=LocalWeapons[I];auto& Rig=Sample.Rigs[I];auto* Source=D.Source.Get();
        if(D.PoseFamily==TEXT("Bow"))continue; // bow owns its existing marker/string sampler
        if(D.PoseFamily.IsNone()&&!Inspect)continue;
        const int32 Side=D.AttachHand;auto* Map=MotionMap(Source,D.GripBone,Side);
        if(!Map||!Map->IsValid())continue;
        const auto& Pose=Source->GetComponentSpaceTransforms();if(!Pose.IsValidIndex(Map->SourceHand))continue;
        Rig.Valid=true;Rig.Schema=D.MotionSchema;
        const FTransform Hand=Rigid(Pose[Map->SourceHand]);
        const FTransform NativeMount=Map->Mount; // CaptureMotionHand may grow the map array.
        const int32 SourceHand=Map->SourceHand;
        const bool NativeMelee=D.PoseFamily==TEXT("Sword")||D.PoseFamily==TEXT("Tool");
        const bool StaffAction=D.PoseFamily==TEXT("Staff")&&(Cast||Bash||Staff->IlluminationGestureAge>=0.f||Staff->IsEquipping()||Staff->IsPrimaryAttacking());
        const auto& HandState=Side==0?State.RightHand:State.LeftHand;
        const bool Drive=NativeMelee||Reload||Inspect||Mount||StaffAction||(Side==1&&Bash)||HandState.bReloading||HandState.bEquipping
            ||(D.PoseFamily==TEXT("Gun")&&State.Action==EFPSBodyAction::Equip);
        CaptureMotionHand(Source,D.GripBone,Side,Drive,Sample);
        if(I==0&&LocalWeapons.Num()==1&&D.PoseFamily!=TEXT("Staff"))
        {
            CaptureMotionHand(Source,TEXT("hand_l"),1,Drive,Sample);Sample.CoupledWrists=Drive;
            if(const auto* Left=MotionMap(Source,TEXT("hand_l"),1);Left&&Left->IsValid()&&Pose.IsValidIndex(Left->SourceHand))
            {
                Sample.HasSupportGrip=true;
                Sample.SupportGrip=Left->Mount.Inverse()*Rigid(Pose[Left->SourceHand]).GetRelativeTransform(Hand)*NativeMount;
            }
        }
        if(NativeMelee&&MotionBindings.IsValidIndex(I)&&MotionBindings[I].FrozenPose.IsValidIndex(SourceHand))
        {
            // Reuse the complete authored swing, not an idle grip plus a pulse.
            // Rebase its hand trajectory around a world-body ready position:
            // the FPS camera's eye height/feedback must not pin both hands to the face.
            const FTransform Ready=NativeMount.Inverse()*Rigid(MotionBindings[I].FrozenPose[SourceHand]);
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
        Rig.Root=Hand.Inverse()*NativeMount;
        Rig.Visible=Drawn(Source);
        if(auto* Static=D.StaticSource.Get())
        {
            Rig.Root=Static->GetComponentTransform().GetRelativeTransform(Rigid(Hand*Source->GetComponentTransform()))*NativeMount;
            Rig.Visible=Drawn(Static);
        }
        for(int32 Bone:D.MotionBones)Rig.Bones.Add(Pose.IsValidIndex(Bone)?Pose[Bone]:FTransform::Identity);
        for(const auto& Weak:D.SourceParts)
        {
            auto* Part=Weak.Get();Rig.Parts.Add(Part?Part->GetComponentTransform().GetRelativeTransform(
                D.StaticSource.IsValid()?D.StaticSource->GetComponentTransform():Source->GetComponentTransform()):FTransform::Identity);
            Rig.VisibleParts.Add(Drawn(Part)?1:0);
        }
        Rig.Sections=0;
        for(int32 M=0;M<FMath::Min(32,Source->GetNumMaterials());++M)
            if(Source->IsMaterialSectionShown(M,0))Rig.Sections|=1u<<M;
    }
    if(Staff&&Staff->IsEquipped()&&!Pawn->HasOffhandPistol()&&(Bash||Cast||Staff->IlluminationGestureAge>=0.f))
        CaptureMotionHand(Staff->ArmsMesh(),TEXT("hand_l"),1,Bash,Sample);
    if(auto* Unarmed=Pawn->FindComponentByClass<UFPSUnarmedIdleComponent>();Unarmed&&Unarmed->IsEquipped())
        for(int32 Side=0;Side<2;++Side)CaptureMotionHand(Unarmed->Arms,Side==0?TEXT("hand_r"):TEXT("hand_l"),Side,Bash,Sample);
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
            const FTransform Hand=Rigid(Source->GetSocketTransform(TEXT("hand_l")));
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
    {Sample.Wrists=Sample.Fingers=0;Sample.PropVisibility=0;Sample.HasSupportGrip=false;Sample.Light=0.f;}
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
    if(Incoming.HasSupportGrip)
    {
        SmoothedContacts.SupportGrip.Blend(SmoothedContacts.SupportGrip,Incoming.SupportGrip,SmoothedContacts.HasSupportGrip?Alpha:1.f);
        BodyAnimation->LeftGripFromRight=SmoothedContacts.SupportGrip;
    }
    else if(SmoothedContacts.HasSupportGrip)BodyAnimation->LeftGripFromRight=BaseSupportGrip;
    SmoothedContacts.HasSupportGrip=Incoming.HasSupportGrip;
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
        if(!R.Valid||R.Schema!=Binding.Definition.MotionSchema||R.Bones.Num()!=Binding.Definition.MotionBones.Num()||R.Parts.Num()!=Binding.Parts.Num())
        {
            if(Binding.Smoothed.Valid)
            {
                Root->SetRelativeTransform(Binding.Mount);
                if(Binding.Mesh.IsValid())Binding.Mesh->PublishMechanicalPose(Binding.FrozenPose);
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
        FPSBodyEquipment::ApplyShadowFlags(Root,Visible&&ShouldWorldBodyCastShadow());
        if(auto* Mesh=Binding.Mesh.Get())
        {
            auto Pose=Binding.FrozenPose;
            for(int32 B=0;B<R.Bones.Num();++B)if(Pose.IsValidIndex(Binding.Definition.MotionBones[B]))Pose[Binding.Definition.MotionBones[B]]=Smooth.Bones[B];
            Mesh->PublishMechanicalPose(Pose);
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
