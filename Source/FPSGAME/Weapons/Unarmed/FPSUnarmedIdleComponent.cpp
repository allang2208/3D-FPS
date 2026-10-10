#include "FPSUnarmedIdleComponent.h"
#include "UnarmedAuthoredLocomotion20261001.h"
#include "../../FPSGAMECharacter.h"
#include "../../FPSGAMEPlayerController.h"
#include "../../Skills/FPSQuickCombatComponent.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Movement/FPSFootstepAudioComponent.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "Camera/CameraComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace
{
const FSoftObjectPath UnarmedArmsAssetPath(TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7"));
}

void UFPSUnarmedArmsMeshComponent::SetMotionSample(float Weight,float EnterWeight,float Phase,float Move,float Run)
{BreathWeight=Weight;EntryWeight=EnterWeight;StridePhase=Phase;MoveWeight=Move;RunWeight=Run;}

void UFPSUnarmedArmsMeshComponent::CacheIdlePose()
{
    namespace Motion=UnarmedAuthoredLocomotion20261001;
    auto* Mesh=GetSkeletalMeshAsset();
    if(!Mesh||(CachedMesh.Get()==Mesh&&CachedRevision==Motion::Revision))return;
    CachedMesh=Mesh;const auto& Skeleton=Mesh->GetRefSkeleton();
    Reference=Skeleton.GetRefBonePose();
    for(int32 I=0;I<Reference.Num();++I)
    {const int32 Parent=Skeleton.GetParentIndex(I);if(Parent>=0)Reference[I]=Reference[I]*Reference[Parent];}
    ArmBones.Reset();
    for(const TCHAR* RootName:{TEXT("clavicle_l"),TEXT("clavicle_r")})
    {
        const int32 Root=Skeleton.FindBoneIndex(RootName);
        if(Root>=0)for(int32 I=0;I<Reference.Num();++I)
            if(I==Root||Skeleton.BoneIsChildOf(I,Root))ArmBones.Add(I);
    }
    for(int32 Key=0;Key<Motion::IdleKeyCount;++Key)
    {
        Keys[Key]=Skeleton.GetRefBonePose();
        for(int32 B=0;B<Motion::BoneCount;++B)
        {
            const int32 I=Skeleton.FindBoneIndex(Motion::Names[B]);if(I<0)continue;
            const int32 Parent=Skeleton.GetParentIndex(I);
            const FVector ParentScale=Parent>=0?Reference[Parent].GetScale3D():FVector::OneVector;
            Keys[Key][I].SetLocation(Motion::Idle[Key][B].Position/ParentScale);
            Keys[Key][I].SetRotation(Motion::Idle[Key][B].Rotation.GetNormalized());
        }
    }
    GaitSamples=Motion::Samples;GaitBones.Init(INDEX_NONE,Motion::BoneCount);
    WalkKeys.SetNum(GaitSamples*Motion::BoneCount);RunKeys.SetNum(GaitSamples*Motion::BoneCount);
    for(int32 B=0;B<Motion::BoneCount;++B)
    {
        const int32 I=Skeleton.FindBoneIndex(Motion::Names[B]);GaitBones[B]=I;if(I<0)continue;
        const int32 Parent=Skeleton.GetParentIndex(I);
        const FVector ParentScale=Parent>=0?Reference[Parent].GetScale3D():FVector::OneVector;
        for(int32 Frame=0;Frame<GaitSamples;++Frame)for(int32 Cycle=0;Cycle<2;++Cycle)
        {
            FTransform& Local=Cycle==0?WalkKeys[Frame*Motion::BoneCount+B]:RunKeys[Frame*Motion::BoneCount+B];
            const auto& Key=Motion::Cycles[Cycle][Frame][B];Local=Skeleton.GetRefBonePose()[I];
            Local.SetLocation(Key.Position/ParentScale);Local.SetRotation(Key.Rotation.GetNormalized());
        }
    }
    LowerBones[0]=Skeleton.FindBoneIndex(TEXT("lowerarm_l"));
    LowerBones[1]=Skeleton.FindBoneIndex(TEXT("lowerarm_r"));
    CachedRevision=Motion::Revision;
}

void UFPSUnarmedArmsMeshComponent::FinalizeBoneTransform()
{
    if(IsVisible()&&!bHiddenInGame&&GetSkeletalMeshAsset())
    {
        CacheIdlePose();auto& Pose=GetEditableComponentSpaceTransforms();
        const auto* ViewCamera=Cast<UCameraComponent>(GetAttachParent());
        if(ViewCamera&&Pose.Num()==Reference.Num())
        {
            namespace Motion=UnarmedAuthoredLocomotion20261001;
            const auto& Skeleton=GetSkeletalMeshAsset()->GetRefSkeleton();
            for(int32 I=0;I<Pose.Num();++I)
                Pose[I].Blend(Keys[0][I],Keys[1][I],BreathWeight);
            const float Sample=FMath::Fmod(StridePhase/(2.f*PI)*GaitSamples+GaitSamples,static_cast<float>(GaitSamples));
            const int32 A=FMath::FloorToInt(Sample),B=(A+1)%GaitSamples;
            const float Alpha=Sample-A;
            if(MoveWeight>UE_SMALL_NUMBER)for(int32 Bone=0;Bone<GaitBones.Num();++Bone)
            {
                const int32 I=GaitBones[Bone];if(I<0)continue;
                FTransform Walk,Run,Gait;
                Walk.Blend(WalkKeys[A*Motion::BoneCount+Bone],WalkKeys[B*Motion::BoneCount+Bone],Alpha);
                Run.Blend(RunKeys[A*Motion::BoneCount+Bone],RunKeys[B*Motion::BoneCount+Bone],Alpha);
                Gait.Blend(Walk,Run,RunWeight);Pose[I].BlendWith(Gait,MoveWeight);
            }
            // Interpolate hinge flexion and axial roll separately throughout
            // idle/walk/run, keeping both elbows on their native bend planes.
            for(int32 Side=0;Side<2;++Side)
            {
                const int32 I=LowerBones[Side];if(I<0)continue;
                const auto& Definition=Motion::JointDefinitions[Side];
                const auto Joint=[&](bool Roll)
                {
                    const auto Value=[Roll](const Motion::FJoint& Key){return Roll?Key.Roll:Key.Flex;};
                    const double Idle=FMath::Lerp(Value(Motion::IdleJoints[0][Side]),Value(Motion::IdleJoints[1][Side]),BreathWeight);
                    const double Walk=FMath::Lerp(Value(Motion::CycleJoints[0][A][Side]),Value(Motion::CycleJoints[0][B][Side]),Alpha);
                    const double Run=FMath::Lerp(Value(Motion::CycleJoints[1][A][Side]),Value(Motion::CycleJoints[1][B][Side]),Alpha);
                    return FMath::Lerp(Idle,FMath::Lerp(Walk,Run,RunWeight),MoveWeight);
                };
                CurrentJoints[Side]=FVector2D(Joint(false),Joint(true));
                Pose[I].SetRotation((FQuat(Definition.ElbowHinge,CurrentJoints[Side].X)*Definition.LowerRestRotation*
                    FQuat(Definition.ForearmAxis,CurrentJoints[Side].Y)).GetNormalized());
            }
            ApplyPunchPose(Pose);
            for(int32 I=0;I<Pose.Num();++I)
            {
                const int32 Parent=Skeleton.GetParentIndex(I);
                if(Parent>=0)Pose[I]=Pose[I]*Pose[Parent];
            }
            const FTransform CameraToMesh=ViewCamera->GetComponentTransform().GetRelativeTransform(GetComponentTransform());
            const FVector EnterOffset=FVector(-2.,0.,-6.)*(1.f-EntryWeight);
            for(const int32 I:ArmBones)
            {
                Pose[I].SetLocation(CameraToMesh.TransformPosition(Pose[I].GetLocation()+EnterOffset));
                Pose[I].SetRotation((CameraToMesh.GetRotation()*Pose[I].GetRotation()).GetNormalized());
            }
        }
    }
    // Existing spell and potion layers take the left hand from this base pose;
    // the right fist and outfit leader remain owned by this viewmodel.
    Super::FinalizeBoneTransform();
}

UFPSUnarmedIdleComponent::UFPSUnarmedIdleComponent()
{PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickGroup=TG_PostPhysics;}

void UFPSUnarmedIdleComponent::BeginPlay()
{
    Super::BeginPlay();auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||GetNetMode()==NM_DedicatedServer){SetComponentTickEnabled(false);return;}
    Camera=Pawn->FindComponentByClass<UCameraComponent>();if(!Camera.IsValid())return;
    Combat=Pawn->FindComponentByClass<UFPSQuickCombatComponent>();
    AddTickPrerequisiteActor(Pawn);AddTickPrerequisiteComponent(Pawn->GetCharacterMovement());
    Footsteps=Pawn->FindComponentByClass<UFPSFootstepAudioComponent>();
    if(Footsteps.IsValid())AddTickPrerequisiteComponent(Footsteps.Get());
    Arms=NewObject<UFPSUnarmedArmsMeshComponent>(Pawn,TEXT("UnarmedV7Fists"));
    Pawn->AddInstanceComponent(Arms);Arms->SetupAttachment(Camera.Get());
    Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);Arms->SetCanEverAffectNavigation(false);
    Arms->SetOnlyOwnerSee(true);Arms->SetCastShadow(false);Arms->bReceivesDecals=false;
    Arms->SetVisibility(false);Arms->RegisterComponent();Arms->SetComponentTickEnabled(false);
    Arms->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Arms->SetBoundsScale(2.f);
    if(GetWorld()->GetGameInstance())Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(Model.IsValid())EquipmentChanged=Model->OnChanged.AddUObject(this,&UFPSUnarmedIdleComponent::RefreshEquipment);
    RefreshEquipment();if(Pawn->IsLocallyControlled())LoadArms();
}

void UFPSUnarmedIdleComponent::RefreshEquipment()
{
    const bool WasEmpty=bHandsEmpty;
    const bool WasBook=bBookOffhandOnly;
    bHandsEmpty=false;bBookOffhandOnly=false;bEquipmentResolved=false;
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(Model.IsValid()&&Pawn&&Pawn->IsLocallyControlled())
    {
        // Snapshot is read on profile publication, never on the animation tick.
        const auto State=Model->Snapshot();const int32 Offhand=State.ActiveWeaponSlot==6?8:11;
        bHandsEmpty=!Model->Equipped(State.ActiveWeaponSlot)&&!Model->Equipped(Offhand)&&!Model->ActiveProductionTool();
        const auto* Left=Model->Equipped(Offhand);
        bBookOffhandOnly=!Model->Equipped(State.ActiveWeaponSlot)&&Left&&Left->Definition==TEXT("ue_alchemy_spellbook")&&!Model->ActiveProductionTool();
        bEquipmentResolved=true;
    }
    if(!IsEquipped()||WasBook!=bBookOffhandOnly)CancelAttack();
    if(WasEmpty!=bHandsEmpty||WasBook!=bBookOffhandOnly)NextPunchSide=1;
    if(Arms)
    {
        if(bHandsEmpty||bBookOffhandOnly)Arms->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
        else Arms->ComponentTags.Remove(TEXT("PreloadModularOutfit"));
    }
    UpdateVisibility();
}

void UFPSUnarmedIdleComponent::LoadArms()
{
    if(bLoadRequested)return;bLoadRequested=true;
    if(UnarmedArmsAssetPath.ResolveObject()){ApplyLoadedArms();return;}
    Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(UnarmedArmsAssetPath,
        FStreamableDelegate::CreateUObject(this,&UFPSUnarmedIdleComponent::ApplyLoadedArms));
}

void UFPSUnarmedIdleComponent::ApplyLoadedArms()
{
    auto* Mesh=Cast<USkeletalMesh>(UnarmedArmsAssetPath.ResolveObject());if(!Arms||!Mesh)return;
    Arms->SetSkeletalMesh(Mesh);
    // V7's native M4 mesh contains weapon sections; this view exposes only arms.
    if(const auto* Render=Mesh->GetResourceForRendering())for(int32 L=0;L<Render->LODRenderData.Num();++L)
        for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
        {
            const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            const FString N=Mesh->GetMaterials()[M].MaterialSlotName.ToString().ToLower();
            const bool Hand=!N.Contains(TEXT("handguard"))&&(N.Contains(TEXT("skin"))||N.Contains(TEXT("manny"))||
                N.Contains(TEXT("bare"))||N.Contains(TEXT("glove"))||N.Contains(TEXT("sleeve"))||
                N==TEXT("hand")||N==TEXT("hands")||N.EndsWith(TEXT("_hands")));
            Arms->ShowMaterialSection(M,S,Hand,L);
        }
    UpdateVisibility();
}

bool UFPSUnarmedIdleComponent::ShouldShow() const
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if((!bHandsEmpty&&!bBookOffhandOnly)||!Arms||!Arms->GetSkeletalMeshAsset()||!Pawn||!Pawn->IsLocallyControlled()||Pawn->IsTraversing())return false;
    const auto* PC=Cast<APlayerController>(Pawn->GetController());
    if(!PC||PC->GetViewTarget()!=Pawn)return false;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    return true;
}

void UFPSUnarmedIdleComponent::UpdateVisibility()
{
    if(!Arms)return;const bool Show=ShouldShow();
    if(Arms->IsVisible()!=Show)
    {Arms->SetVisibility(Show);VisibleAge=0.f;MoveBlend=0.f;RunBlend=0.f;}
}

void UFPSUnarmedIdleComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn||!Pawn->IsLocallyControlled())return;
    if(!bEquipmentResolved)RefreshEquipment();
    if(!bLoadRequested)LoadArms();UpdateVisibility();
    RefreshPunchSample();
    if(!Arms||!Arms->IsVisible()||Arms->bHiddenInGame)return;
    CycleTime=FMath::Fmod(CycleTime+Delta,UnarmedAuthoredLocomotion20261001::PeriodSeconds);VisibleAge+=Delta;
    const float Breath=.5f-.5f*FMath::Cos(2.f*PI*CycleTime/UnarmedAuthoredLocomotion20261001::PeriodSeconds);
    const float Enter=FMath::SmoothStep(0.f,.18f,VisibleAge);
    const auto* Movement=Pawn->GetCharacterMovement();
    const float Speed=Pawn->GetVelocity().Size2D();
    const bool Grounded=Movement&&Movement->IsMovingOnGround()&&!Pawn->IsSliding()&&!Pawn->IsDodging();
    const bool Moving=Grounded&&Speed>15.f;
    const float MoveTarget=Moving?FMath::Clamp((Speed-15.f)/FMath::Max(1.f,Movement->MaxWalkSpeed-15.f),0.f,1.f):0.f;
    const bool Running=Moving&&Pawn->IsSprinting()&&!Pawn->bIsCrouched;
    const float Follow=1.f-FMath::Exp(-9.f*Delta);
    MoveBlend=FMath::Lerp(MoveBlend,MoveTarget,Follow);
    RunBlend=FMath::Lerp(RunBlend,Running?1.f:0.f,1.f-FMath::Exp(-(Running?5.5f:10.f)*Delta));
    const float Move=MoveBlend*(Pawn->bIsCrouched?.6f:1.f);
    // Distance/footfall phase is shared with the camera and staff. Airborne and
    // stationary frames fade the last sampled stride instead of advancing it.
    if(Moving&&Footsteps.IsValid())GaitPhase=Footsteps->GetStridePhaseRadians();
    Arms->SetMotionSample(Breath,Enter,GaitPhase,Move,RunBlend);
    Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
}

void UFPSUnarmedIdleComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    CancelAttack();
    if(Model.IsValid()&&EquipmentChanged.IsValid())Model->OnChanged.Remove(EquipmentChanged);
    if(Load)Load->CancelHandle();Super::EndPlay(Reason);
}

bool UFPSUnarmedIdleComponent::IsPunching() const
{
    const auto* Quick=Combat.Get();
    return Quick&&Quick->GetStyle()==EQuickCombatStyle::UnarmedPunch&&Quick->IsOccupyingLeftHand();
}

bool UFPSUnarmedIdleComponent::CanPunch() const
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!IsEquipped()||!Pawn||!Pawn->IsLocallyControlled()||!Arms||!Arms->GetSkeletalMeshAsset()
        ||Pawn->IsResolvingActionInterrupt()||Pawn->IsSwitchingWeapon()||Pawn->IsTraversing()
        ||Pawn->IsDodging()||Pawn->IsSliding()||Pawn->IsSpellGestureBlocking())return false;
    if(const auto* Potion=Pawn->FindComponentByClass<UFPSPotionUseComponent>();Potion&&Potion->IsActive())return false;
    if(AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(Pawn->GetController())))return false;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    const auto* PC=Cast<APlayerController>(Pawn->GetController());
    return PC&&PC->GetViewTarget()==Pawn;
}

bool UFPSUnarmedIdleComponent::BeginPunch()
{
    auto* Quick=Combat.Get();
    if(!CanPunch()||!Quick||Quick->IsOccupyingLeftHand())return false;
    Arms->CapturePunchEntry();
    Quick->ConfigureForUnarmedPunch();
    if(!Quick->BeginAction())return false;
    PunchSide=bBookOffhandOnly?1:NextPunchSide;
    NextPunchSide=bBookOffhandOnly?1:1-NextPunchSide;
    Cast<AFPSGAMECharacter>(GetOwner())->ExitSprintForWeapon();
    RefreshPunchSample();
    return true;
}

void UFPSUnarmedIdleComponent::SetTriggerHeld(bool Held)
{
    bTriggerHeld=Held;
    if(Held&&!IsPunching()&&!BeginPunch())bTriggerHeld=false;
}

void UFPSUnarmedIdleComponent::CancelAttack()
{
    bTriggerHeld=false;
    if(auto* Quick=Combat.Get();
        Quick&&Quick->GetStyle()==EQuickCombatStyle::UnarmedPunch)Quick->Cancel();
    if(Arms)Arms->SetPunchSample(-1.f,PunchSide);
}

void UFPSUnarmedIdleComponent::RefreshPunchSample()
{
    const auto* Quick=Combat.Get();
    if(Arms)Arms->SetPunchSample(IsPunching()?Quick->GetActionAge():-1.f,PunchSide);
}

void UFPSUnarmedIdleComponent::AdvanceActionBeforeCamera(float Delta)
{
    if(Delta<=0.f)return;
    auto* Quick=Combat.Get();
    if(!Quick||Quick->GetStyle()!=EQuickCombatStyle::UnarmedPunch)return;
    if(IsPunching()&&!CanPunch()){CancelAttack();return;}
    const bool WasPunching=IsPunching();
    Quick->AdvanceAction(Delta);
    RefreshPunchSample();
    if(WasPunching&&!IsPunching()&&bTriggerHeld)
    {
        // Finish recovery before capturing the next fist's entry. No hitch catch-up hits.
        if(Arms&&Arms->IsVisible()){Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();}
        if(!BeginPunch())bTriggerHeld=false;
    }
}

bool UFPSUnarmedIdleComponent::GetStrikeProbe(FVector& Origin)
{
    if(!IsPunching()||!Arms||!Arms->IsVisible()||Arms->bHiddenInGame)return false;
    const FName Bone=PunchSide==1?TEXT("middle_01_r"):TEXT("middle_01_l");
    if(Arms->GetBoneIndex(Bone)==INDEX_NONE)return false;
    RefreshPunchSample();Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
    Origin=Arms->GetSocketLocation(Bone);
    return true;
}
