#include "VillageOilCarry.h"
#include "VillageHotOil.h"
#include "VillageOilMotion.h"
#include "VillageSiegeControl.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Movement/PlayerKnockdownComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSPlayerBodyGrip.h"
#include "../Building/ForgeArmsMeshComponent.h"
#include "../Weapons/WoodenTorchArmsComponent.h"
#include "../Weapons/Staff/StaffGripPose.h"
#include "../Weapons/WeaponPresentationMaterials.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/GameStateBase.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "TwoBoneIK.h"
#include "Net/UnrealNetwork.h"

namespace
{
using namespace VillageOilMotion;
double Clock(const UWorld* W){const auto* G=W->GetGameState();return G?G->GetServerWorldTimeSeconds():W->GetTimeSeconds();}
double Ease(double Age,double From,double To){return FMath::SmoothStep(From,To,Age);}
FTransform Grip(int Side,double Tip)
{
    // The handle cylinders run fore-and-aft. Their centres come from the small pot's mesh profile.
    const FQuat PalmRoll(FVector::ForwardVector,FMath::DegreesToRadians(Side?-(46.+3.*Tip):13.-30.*Tip));
    return FTransform(PalmRoll*FRotationMatrix::MakeFromZX(FVector::ForwardVector,FVector::UpVector).ToQuat(),
                      FVector(0,Side?-18.9:18.9,5.6));
}
void DriveArm(const FReferenceSkeleton& Ref,TArray<FTransform>& Pose,int Side,const FVector& Target,
              const FVector& Pole,const TOptional<FQuat>& Rotation)
{
    int32 Hand=Ref.FindBoneIndex(Side?TEXT("hand_l"):TEXT("hand_r"));
    int32 Elbow=Ref.FindBoneIndex(Side?TEXT("lowerarm_l"):TEXT("lowerarm_r"));
    int32 Upper=Ref.FindBoneIndex(Side?TEXT("upperarm_l"):TEXT("upperarm_r"));
    if(!Pose.IsValidIndex(Hand)||!Pose.IsValidIndex(Elbow)||!Pose.IsValidIndex(Upper))return;
    FTransform A=Pose[Upper],B=Pose[Elbow],C=Pose[Hand];
    const FTransform OldA=A,OldB=B,OldC=C;
    AnimationCore::SolveTwoBoneIK(A,B,C,Pole,Target,FVector::Dist(A.GetLocation(),B.GetLocation()),
        FVector::Dist(B.GetLocation(),C.GetLocation()),false,1.,1.);
    const FQuat Follow=(OldC.GetRelativeTransform(OldB)*B).GetRotation();
    C.SetRotation(Rotation.Get(Follow));
    // Roll the forearm skin towards the handle. Leaving all of the roll at the wrist pinches the V7 cuff.
    const FVector Segment=C.GetLocation()-B.GetLocation();
    FQuat Swing,Twist;
    (C.GetRotation()*Follow.Inverse()).GetNormalized().ToSwingTwist(Segment.GetSafeNormal(),Swing,Twist);
    for(int32 I=Upper+1;I<Pose.Num();++I)
    {
        if(I==Hand||I==Elbow)continue;
        if(Ref.BoneIsChildOf(I,Hand))Pose[I]=Pose[I].GetRelativeTransform(OldC)*C;
        else if(Ref.BoneIsChildOf(I,Elbow))
        {
            auto Helper=Pose[I].GetRelativeTransform(OldB)*B;
            const FVector Offset=Helper.GetLocation()-B.GetLocation();
            const double Along=FMath::Clamp(FVector::DotProduct(Offset,Segment)/FMath::Max(1.,Segment.SizeSquared()),0.,1.);
            const FQuat Roll=FQuat::Slerp(FQuat::Identity,Twist,.35+.65*Along);
            Helper.SetLocation(B.GetLocation()+Roll.RotateVector(Offset));
            Helper.SetRotation((Roll*Helper.GetRotation()).GetNormalized());
            Pose[I]=Helper;
        }
        else if(Ref.BoneIsChildOf(I,Upper))Pose[I]=Pose[I].GetRelativeTransform(OldA)*A;
    }
    B.SetRotation((FQuat::Slerp(FQuat::Identity,Twist,.35)*B.GetRotation()).GetNormalized());
    Pose[Upper]=A;Pose[Elbow]=B;Pose[Hand]=C;
}
}
UVillageOilCarry::UVillageOilCarry()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;
}
AFPSGAMECharacter* UVillageOilCarry::Player() const {return Cast<AFPSGAMECharacter>(GetOwner());}
void UVillageOilCarry::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UVillageOilCarry,State);
}
bool UVillageOilCarry::HandsInUse() const
{
    const auto* P=Player();
    const auto* PC=P?Cast<AFPSGAMEPlayerController>(P->GetController()):nullptr;
    if(!PC || PC->IsInBuildMode() || (PC->GetSiegeControl() && PC->GetSiegeControl()->Active()))return true;
    if(const auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();Health && Health->IsDead())return true;
    if(UPlayerKnockdownComponent::IsKnockedDown(P) || P->IsTraversing())return true;
    if(const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>())
    {
        const auto& S=Body->CurrentBodyState();
        // Equip is also synthesized when the same weapon's presentation is refreshed.
        if((S.Action!=EFPSBodyAction::None && S.Action!=EFPSBodyAction::Equip) ||
           S.ConsumeHands || S.RightHand.bReloading || S.LeftHand.bReloading || S.bAiming ||
           S.Motion==EFPSBodyMotion::Vault || S.Motion==EFPSBodyMotion::Mantle)return true;
    }
    if(!P->IsLocallyControlled())return false;
    if(const auto* Bow=P->FindComponentByClass<UBowWeaponComponent>();Bow && (Bow->IsAimHeld() || Bow->IsDrawing()))return true;
    return P->IsAiming() || P->IsReloading() || P->IsOffhandReloadActive() ||
        P->IsCastingWithLeftHand() || P->IsSpellGestureBlocking();
}

bool UVillageOilCarry::CanTake() const
{
    const auto* P=Player();
    return !HandsInUse() && !AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(P->GetController())) &&
        (!P->IsLocallyControlled() || (!P->IsLeftHandBusyForCast() && !P->IsSwitchingWeapon() && !P->IsWeaponFireHeld()));
}

void UVillageOilCarry::RememberEquipment()
{
    OffhandSlotAtTake=INDEX_NONE;
    if(const auto* Model=ColdSteelAuthority::ForPawn(Player()))RefreshEquipment(*Model);
}

void UVillageOilCarry::RefreshEquipment(const UColdSteelStatusModel& Model)
{
    const int32 Slot=Model.ActiveOffhandSlot();
    const auto* Main=Model.Equipped();
    const auto* Off=Model.Equipped(Slot);
    if(OffhandSlotAtTake==INDEX_NONE)
    {
        OffhandSlotAtTake=Slot;
        MainItemAtTake=Main?Main->InstanceId:FString();
        OffhandItemAtTake=Off?Off->InstanceId:FString();
        return;
    }
    if(Slot!=OffhandSlotAtTake || (Main?Main->InstanceId!=MainItemAtTake:!MainItemAtTake.IsEmpty()) ||
       (Off?Off->InstanceId!=OffhandItemAtTake:!OffhandItemAtTake.IsEmpty()))Cancel();
}
void UVillageOilCarry::Take(AVillageOilKettle* Kettle)
{
    if(!Kettle || Occupied() || bTakePending || !CanTake())return;
    bTakePending=true;bLocalCancel=false;RememberEquipment();
    ServerTake(Kettle);
}
void UVillageOilCarry::ServerTake_Implementation(AVillageOilKettle* Kettle)
{
    const bool Ok=!Occupied() && CanTake() && IsValid(Kettle) && Kettle->GetHealth()>0 &&
        ColdSteelWorldInteraction::IsFocused(Player(),Kettle);
    if(Ok){RememberEquipment();SetState(EOilCarryPhase::Held);}
    ClientTakeResult(Ok);
}
void UVillageOilCarry::ClientTakeResult_Implementation(bool Accepted){if(!Accepted)bTakePending=false;}
void UVillageOilCarry::SetState(EOilCarryPhase Phase)
{
    State.Phase=Phase;State.Since=Clock(GetWorld());bReleasedOil=false;bPourQueued=false;
    OnRep_Hands();Player()->ForceNetUpdate();
}
void UVillageOilCarry::OnRep_Hands()
{
    bTakePending=false;
    if(!Occupied()){bLocalCancel=false;OffhandSlotAtTake=INDEX_NONE;}
    else if(Player()->IsLocallyControlled() && !Player()->HasAuthority())
    {
        // A slot change can land between the pickup request and the server acknowledgement.
        if(const auto* Model=ColdSteelAuthority::ForPawn(Player()))RefreshEquipment(*Model);
    }
    SetComponentTickEnabled(Occupied());
    if(GetNetMode()!=NM_DedicatedServer){if(Occupied())PrepareVisual();UpdateVisual();}
}
void UVillageOilCarry::ServerCancel_Implementation(){if(Occupied())SetState(EOilCarryPhase::Empty);}
void UVillageOilCarry::Cancel()
{
    if((!Occupied() && !bTakePending) || bLocalCancel)return;
    if(Player()->HasAuthority()){if(Occupied())SetState(EOilCarryPhase::Empty);return;}
    if(!Player()->IsLocallyControlled())return;
    bLocalCancel=true;bTakePending=false;UpdateVisual();ServerCancel();
}
bool UVillageOilCarry::HandleInput(const FInputKeyEventArgs& E)
{
    const bool Primary=E.Key==EKeys::LeftMouseButton || E.Key==EKeys::Gamepad_RightTrigger;
    if(Primary && E.Event==IE_Released && bLeftPressed){bLeftPressed=false;return true;}
    if((!Occupied() && !bTakePending) || bLocalCancel)return false;
    if(Primary && AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(Player()->GetController())))return false;
    if(Primary)
    {
        if(E.Event==IE_Pressed)
        {
            bLeftPressed=true;
            if((bTakePending || State.Phase==EOilCarryPhase::Held) && !HandsInUse())ServerPour();
        }
        return true;
    }
    // A second interaction with the same supply cannot start another pickup. Other keys go to their action owner.
    if(E.Event==IE_Pressed && E.Key==EKeys::E &&
       Cast<AVillageOilKettle>(ColdSteelWorldInteraction::TraceTarget(Cast<APlayerController>(Player()->GetController()))))return true;
    return false;
}
void UVillageOilCarry::ServerPour_Implementation()
{
    if(State.Phase!=EOilCarryPhase::Held || HandsInUse())return;
    if(Clock(GetWorld())-State.Since<Raise)bPourQueued=true;
    else SetState(EOilCarryPhase::Pour);
}
FTransform UVillageOilCarry::PanPose(bool FirstPerson) const
{
    const double Age=FMath::Max(0.,Clock(GetWorld())-State.Since);
    const double Lift=State.Phase==EOilCarryPhase::Held?Ease(Age,0,Raise):1.;
    const bool Pouring=State.Phase==EOilCarryPhase::Pour;
    const double Load=Pouring?Ease(Age,0,.15)*(1.-Ease(Age,.15,.38)):0.;
    const double Tilt=Pouring?Tip(Age):0.;
    const double Push=Pouring?Ease(Age,.10,.47)*(1.-Ease(Age,.83,1.20)):0.;
    const double Down=Pouring?Ease(Age,.98,Finish):0.;
    const double Z=FirstPerson?-13.7:Player()->BaseEyeHeight-31.;
    const double X=(FirstPerson?36.:30.)+3.*Push-4.*Load-6.*(1.-Lift+Down);
    // The left palm supports the low handle; the right lifts the opposite handle over the left-front rim.
    return FTransform(FRotator(-36.*Tilt+4.*Load,-8.*Tilt,-29.*Tilt),
        FVector(X,-3.*Tilt,Z+3.5*Push-3.3*Load-(FirstPerson?28.:22.)*(1.-Lift)-(FirstPerson?32.:25.)*Down));
}
void UVillageOilCarry::TickComponent(float Delta,ELevelTick Tick,FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Delta,Tick,Fn);
    auto* P=Player();if(!P || !Occupied())return;
    if((P->HasAuthority() || P->IsLocallyControlled()) && HandsInUse())
    {Cancel();return;}
    if(P->HasAuthority() && State.Phase==EOilCarryPhase::Held && bPourQueued && Clock(GetWorld())-State.Since>=Raise)
        SetState(EOilCarryPhase::Pour);
    if(P->HasAuthority() && State.Phase==EOilCarryPhase::Pour)
    {
        const double Age=Clock(GetWorld())-State.Since;
        if(!bReleasedOil && Age>=Release)
        {
            bReleasedOil=true;
            const FVector Eye=P->GetPawnViewLocation();
            const FVector Forward=FRotator(0,P->GetBaseAimRotation().Yaw,0).Vector();
            const FVector Column=Eye+Forward*VillageHotOil::Reach;
            FCollisionQueryParams Q(SCENE_QUERY_STAT(OilPour),false,P);
            FCollisionObjectQueryParams Objects(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
            FHitResult Block,Ground;
            // A parapet opening can deliver oil to the street below. Solid walls intercept the pour.
            FVector End=Column;
            if(GetWorld()->LineTraceSingleByObjectType(Block,Eye,Column,Objects,Q))
                End=Block.ImpactPoint-Forward*9.;
            if(GetWorld()->LineTraceSingleByObjectType(Ground,End,End-FVector(0,0,12000),Objects,Q) && Ground.ImpactNormal.Z>=.65)
            {
                const FTransform At(FRotator::ZeroRotator,Ground.ImpactPoint);
                if(auto* Field=GetWorld()->SpawnActorDeferred<AVillageOilField>(AVillageOilField::StaticClass(),At,P,P,
                    ESpawnActorCollisionHandlingMethod::AlwaysSpawn))
                {
                    const FVector BodyLip=PanPose(false).TransformPosition(VillageOilMotion::Lip);
                    Field->Lip=P->GetActorTransform().TransformPosition(BodyLip);
                    Field->FinishSpawning(At);
                }
            }
        }
        if(Age>=Finish){SetState(EOilCarryPhase::Empty);return;}
    }
    if(GetNetMode()!=NM_DedicatedServer && !bLocalCancel)UpdateVisual();
}
void UVillageOilCarry::PrepareVisual()
{
    auto* P=Player();
    auto Make=[&](USceneComponent* Parent,UStaticMesh* Mesh,bool OwnerOnly)
    {
        auto* C=NewObject<UStaticMeshComponent>(P,NAME_None,RF_Transient);
        P->AddInstanceComponent(C);C->SetupAttachment(Parent);C->SetStaticMesh(Mesh);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCanEverAffectNavigation(false);
        C->SetOnlyOwnerSee(OwnerOnly);C->SetCastShadow(!OwnerOnly);
        C->RegisterComponent();return C;
    };
    if(!WorldPot)
    {
        auto* Pot=Cast<UStaticMesh>(VillageHotOil::Asset(TEXT("SM_OilHandPot")).TryLoad());
        auto* Surface=Cast<UStaticMesh>(VillageHotOil::Asset(TEXT("SM_OilSurface")).TryLoad());
        WorldPot=Make(P->GetRootComponent(),Pot,false);WorldOil=Make(WorldPot,Surface,false);
        WorldOil->SetMaterial(0,VillageHotOil::BodyMaterial());
    }
    if(!ViewPot && P->IsLocallyControlled() && P->FirstPersonCamera)
    {
        ViewPot=Make(P->FirstPersonCamera,WorldPot->GetStaticMesh(),true);
        ViewOil=Make(ViewPot,WorldOil->GetStaticMesh(),true);
        ViewOil->SetMaterial(0,WorldOil->GetMaterial(0));
    }
    if(!P->IsLocallyControlled() || Arms || !P->FirstPersonCamera)return;
    auto* Rig=Cast<USkeletalMesh>(FSoftObjectPath(StaffGripPose::ArmsMeshPath).TryLoad());if(!Rig)return;
    Arms=NewObject<UForgeArmsMeshComponent>(P,NAME_None,RF_Transient);P->AddInstanceComponent(Arms);
    Arms->SetupAttachment(P->FirstPersonCamera);Arms->SetSkinnedAssetAndUpdate(Rig,true);
    Arms->SetOnlyOwnerSee(true);Arms->SetCastShadow(false);Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Arms->SetComponentTickEnabled(false);Arms->ComponentTags.Add(TEXT("PreloadModularOutfit"));Arms->RegisterComponent();
    const auto& Ref=Rig->GetRefSkeleton();
    for(int Side=0;Side<2;++Side)
    {
        TArray<FTransform> Sample;
        BaseContact[Side]=UWoodenTorchArmsComponent::BuildStaffCarry(*Rig,Side,Sample,INDEX_NONE);
        if(!Side)RestPose=Sample;
        int32 Clavicle=Ref.FindBoneIndex(Side?TEXT("clavicle_l"):TEXT("clavicle_r"));
        if(Clavicle==INDEX_NONE)continue;
        for(int32 I=Clavicle;I<Ref.GetNum();++I)if(I==Clavicle || Ref.BoneIsChildOf(I,Clavicle))
        {ArmBones.Add(I);RestPose[I]=Sample[I];}
    }
    if(const auto* Render=Rig->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
        {
            const auto& Sections=Render->LODRenderData[L].RenderSections;
            for(int32 S=0;S<Sections.Num();++S)
            {
                const int32 M=Sections[S].MaterialIndex;
                Arms->ShowMaterialSection(M,S,WeaponPresentationMaterials::IsArmSection(Rig->GetMaterials()[M]),L);
            }
        }
}
void UVillageOilCarry::PrepareWorldGrip(USkeletalMesh* BodyMesh)
{
    if(!BodyMesh || WorldGripMesh.Get()==BodyMesh)return;
    auto* Native=Cast<USkeletalMesh>(FSoftObjectPath(StaffGripPose::ArmsMeshPath).TryLoad());
    if(!Native)return;
    WorldGripMesh=BodyMesh;
    WorldFingerPose=BodyMesh->GetRefSkeleton().GetRefBonePose();
    for(int Side=0;Side<2;++Side)
    {
        const FName Hand=Side?TEXT("hand_l"):TEXT("hand_r");
        FFPSBodyGripRig Rig;
        Rig.Initialize(Native->GetRefSkeleton(),BodyMesh->GetRefSkeleton(),Hand,Hand);
        WorldFingers[Side].Reset();
        if(!Rig.IsValid())continue;
        TArray<FTransform> Sample;
        const FTransform Contact=UWoodenTorchArmsComponent::BuildStaffCarry(*Native,Side,Sample);
        WorldHandleInWrist[Side]=Contact*Rig.Mount;
        Rig.Transfer(Sample,WorldFingerPose);
        WorldFingers[Side]=Rig.Descendants;
    }
}
void UVillageOilCarry::UpdateVisual()
{
    const bool Show=Occupied() && !bLocalCancel;
    auto* P=Player();const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool WantsFirst=P->IsLocallyControlled() && P->FirstPersonCamera && !(Body && Body->IsThirdPersonViewEnabled());
    if(Show && WantsFirst && !ViewPot)PrepareVisual();
    const bool First=WantsFirst && ViewPot;
    if(Show && P->GetMesh())PrepareWorldGrip(P->GetMesh()->GetSkeletalMeshAsset());
    if(WorldPot){WorldPot->SetVisibility(Show);WorldPot->SetOwnerNoSee(First);WorldPot->SetRelativeTransform(PanPose(false));}
    const auto Pose=PanPose(true);
    if(ViewPot){ViewPot->SetVisibility(Show && First);ViewPot->SetRelativeTransform(Pose);}
    const double Age=Clock(GetWorld())-State.Since;
    const double Fill=State.Phase==EOilCarryPhase::Pour?VillageOilMotion::Fill(Age):1.;
    for(auto* Oil:{WorldOil.Get(),ViewOil.Get()})if(Oil)
    {
        Oil->SetVisibility(Show && Fill>0. && (Oil!=ViewOil || First));
        if(Oil==WorldOil)Oil->SetOwnerNoSee(First);
        // Level liquid intersecting a parabolic bowl has a displaced circular footprint in pan XY.
        // The camera rig follows the eyes. Use the authored torso-relative tilt so simply looking
        // over a parapet does not empty or invert the liquid in a held first-person pot.
        const FQuat Vessel=Oil==ViewOil?Pose.GetRotation():Oil->GetAttachParent()->GetComponentQuat();
        FVector Up=Vessel.UnrotateVector(FVector::UpVector);
        Up.Z=FMath::Max(.42,Up.Z);Up.Normalize();
        const FVector2D Slope(-Up.X/Up.Z,-Up.Y/Up.Z);
        const FVector2D Center=(Slope*7.25).GetClampedToMaxSize(10.8);
        const double Radius=(12.88-Center.Size())*.94*FMath::Pow(Fill,.28);
        const double Height=-5.32+(Radius*Radius+Center.SizeSquared())*.069;
        const FVector2D Axis=Slope.IsNearlyZero()?FVector2D(1.,0.):Slope.GetSafeNormal();
        const FQuat Rot=FRotationMatrix::MakeFromZX(Up,FVector(Axis,Slope.Size())).ToQuat();
        Oil->SetRelativeLocationAndRotation(FVector(Center,Height),Rot);
        Oil->SetRelativeScale3D(FVector(Radius/(50.*Up.Z),Radius/50.,1.));
        if(Show)Oil->SetCustomPrimitiveDataFloat(0,GetWorld()->GetTimeSeconds());
    }
    if(!Arms)return;
    Arms->SetVisibility(Show && First);
    if(!Show || !First || RestPose.IsEmpty())return;
    const auto& Ref=Arms->GetSkinnedAsset()->GetRefSkeleton();
    TArray<FTransform> Frame=RestPose;
    for(int Side=0;Side<2;++Side)
    {
        const double Tilt=State.Phase==EOilCarryPhase::Pour?Tip(Age):0.;
        const auto Wrist=BaseContact[Side].Inverse()*Grip(Side,Tilt)*Pose;
        const FVector Elbow(-10,Side?-32.+2.*Tilt:32.+3.*Tilt,Side?-23.:-28.+5.*Tilt);
        DriveArm(Ref,Frame,Side,Wrist.GetLocation(),Elbow,Wrist.GetRotation());
    }
    Arms->CommitStationPose(Frame,ArmBones);
}
bool UVillageOilCarry::PourLip(FVector& WorldPoint) const
{
    if(State.Phase!=EOilCarryPhase::Pour || bLocalCancel || Clock(GetWorld())-State.Since>=VillageOilMotion::Empty)return false;
    const bool First=ViewPot && ViewPot->IsVisible();
    const auto* Parent=First?static_cast<const USceneComponent*>(Player()->FirstPersonCamera.Get()):Player()->GetRootComponent();
    if(!Parent)return false;
    WorldPoint=(PanPose(First)*Parent->GetComponentTransform()).TransformPosition(VillageOilMotion::Lip);
    return true;
}
void UVillageOilCarry::PoseWorldArms(USkeletalMeshComponent& Mesh,TArray<FTransform>& Pose) const
{
    if(!Occupied() || bLocalCancel || !Mesh.GetSkeletalMeshAsset() || Pose.IsEmpty())return;
    const auto Frame=PanPose(false)*Player()->GetActorTransform();
    const auto& Ref=Mesh.GetSkeletalMeshAsset()->GetRefSkeleton();
    for(int Side=0;Side<2;++Side)
    {
        if(WorldGripMesh.Get()!=Mesh.GetSkeletalMeshAsset() || WorldFingers[Side].IsEmpty())continue;
        const double Tilt=State.Phase==EOilCarryPhase::Pour?Tip(Clock(GetWorld())-State.Since):0.;
        const FTransform Wrist=(WorldHandleInWrist[Side].Inverse()*Grip(Side,Tilt)*Frame).GetRelativeTransform(Mesh.GetComponentTransform());
        const FVector Pole=Mesh.GetComponentTransform().InverseTransformPosition(Frame.TransformPosition(FVector(-30,Side?-28.:29.,Side?-18.:-19.+6.*Tilt)));
        DriveArm(Ref,Pose,Side,Wrist.GetLocation(),Pole,Wrist.GetRotation());
        for(const int32 Bone:WorldFingers[Side])
            if(Pose.IsValidIndex(Bone))Pose[Bone]=WorldFingerPose[Bone]*Pose[Ref.GetParentIndex(Bone)];
    }
}
void UVillageOilCarry::HideFirstPersonEquipment(const AActor* ViewTarget,TSet<FPrimitiveComponentId>& Hidden) const
{
    const auto* P=Player();
    if(!Occupied() || bLocalCancel || ViewTarget!=P || !P->FirstPersonCamera)return;
    const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>();
    const auto* Legs=Body?Body->GetFirstPersonLowerBodyMesh():nullptr;
    P->ForEachComponent<UPrimitiveComponent>(false,[&](UPrimitiveComponent* C){
        if((Legs && (C==Legs || C->IsAttachedTo(Legs))) || (Arms && C->IsAttachedTo(Arms)))return;
        if(C!=Arms && C!=ViewPot && C!=ViewOil && C->IsRegistered() &&
            (C->IsAttachedTo(P->FirstPersonCamera) || (C->bOnlyOwnerSee && !C->IsA<UCapsuleComponent>())))
            Hidden.Add(C->GetPrimitiveSceneId());
    });
}
void UVillageOilCarry::EndPlay(const EEndPlayReason::Type Reason)
{
    for(USceneComponent* C:{static_cast<USceneComponent*>(Arms.Get()),static_cast<USceneComponent*>(ViewOil.Get()),
        static_cast<USceneComponent*>(WorldOil.Get()),static_cast<USceneComponent*>(ViewPot.Get()),static_cast<USceneComponent*>(WorldPot.Get())})
        if(IsValid(C))C->DestroyComponent();
    Super::EndPlay(Reason);
}
