#include "StableRidingHorse.h"
#include "StableHorseAnimInstance.h"
#include "StableHorseGroundMesh.h"
#include "HorseRiderComponent.h"
#include "StableManeComponent.h"
#include "../UI/StatusEffectsComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "../Combat/CombatStatusFormula.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Materials/MaterialInterface.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"
#include "UObject/ConstructorHelpers.h"

namespace StableGround
{
    constexpr float WalkAngle=45.f;
    constexpr float CanterAngle=60.f;
}

namespace StableJump
{
    // The highest stable hinge pier tops out at 172 cm. Height is the rise
    // of the capsule bottom above its own takeoff floor.
    constexpr float GatherSeconds=.20f, LandSeconds=.30f;
    constexpr float PushFrame=9.f, ApexFrame=18.f, ContactFrame=30.f, LastFrame=45.f;
}

AStableRidingHorse::AStableRidingHorse(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer.SetDefaultSubobjectClass<UStableHorseGroundMesh>(ACharacter::MeshComponentName))
{
    bReplicates=true;
    SetReplicateMovement(true);
    AutoPossessAI=EAutoPossessAI::Disabled;
    bUseControllerRotationYaw=false;
    GetCapsuleComponent()->InitCapsuleSize(42.f,94.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    // Summoned horses also need the stable's mesh and gait assets on every peer.
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Body(TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/SK_StableWarhorse"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Idle(TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/Animations/A_Warhorse_Idle"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Walk(TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/Animations/A_Warhorse_Walk"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Canter(TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/Animations/A_Warhorse_Canter"));
    IdleAnimation=StallAnimation=Idle.Object;WalkAnimation=Walk.Object;CanterAnimation=Canter.Object;
    if(Body.Succeeded())
    {
        GetMesh()->SetSkeletalMeshAsset(Body.Object);
        const auto& Ref=Body.Object->GetRefSkeleton();
        const int32 Mouth=Ref.FindBoneIndex(TEXT("mouth_socket")),Hip=Ref.FindBoneIndex(TEXT("pelvis"));
        if(Mouth!=INDEX_NONE && Hip!=INDEX_NONE)
        {
            const FVector Heading=Ref.GetBoneAbsoluteTransform(Mouth).GetLocation()-Ref.GetBoneAbsoluteTransform(Hip).GetLocation();
            GetMesh()->SetRelativeLocationAndRotation(FVector(0,0,-94),FRotator(0,-Heading.Rotation().Yaw,0));
        }
    }
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    Mane=CreateDefaultSubobject<UStableManeComponent>(TEXT("NeckMane"));
    Mane->SetupAttachment(GetMesh());
    auto* Move=GetCharacterMovement();
    Move->bRunPhysicsWithNoController=true;
    Move->bOrientRotationToMovement=false;
    Move->MaxAcceleration=850.f;
    Move->BrakingDecelerationWalking=1150.f;
    Move->MaxStepHeight=40.f;
    Move->SetWalkableFloorAngle(StableGround::WalkAngle);
    Move->GetNavAgentPropertiesRef().AgentStepHeight=Move->MaxStepHeight;
    Move->GravityScale=1.55f;
    Move->bEnablePhysicsInteraction=false;
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Hurdle(
        TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/Animations/A_Warhorse_HurdleJump.A_Warhorse_HurdleJump"));
    JumpAnimation=Hurdle.Object;
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Rear(TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/Animations/A_Warhorse_Rear.A_Warhorse_Rear"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Coat(TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/AppearanceR30/M_Warhorse_Coat"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Fade(TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/AppearanceR30/M_Warhorse_CoatFade"));
    RearAnimation=Rear.Object;
    CoatMaterial=Coat.Object;FadedCoatMaterial=Fade.Object;
}
void AStableRidingHorse::BeginPlay()
{
    Super::BeginPlay();
    // The streamed village may arrive before the terrain collider. Park idle residents
    // at their authored floor until a grounded player actually reaches the stirrup.
    if(HasAuthority()&&!Rider)GetCharacterMovement()->DisableMovement();
    if(HasAuthority())
    {
        // R7 placed horses predate the authored stall field. Freeze their R22
        // display number at load so later changes of animation cannot rename them.
        if(!RegisteredStall && ActorHasTag(TEXT("VillageStable.Horses")))
            RegisteredStall=StallAnimation && StallAnimation->GetFName()==TEXT("A_Warhorse_Q_Feed")?2:4;
        ResolveInitialIdentity();
        if(IsActorBeingDestroyed())return;
        Health=MaxHealth;
        Stamina=MaxStamina;
        if(const auto* GI=GetGameInstance())
            if(const auto* Model=GI->GetSubsystem<UColdSteelStatusModel>())StaminaRates=Model->StaminaSettings();
    }
    ApplyIndividualAppearance();
    UStatusEffectsComponent::GetOrCreate(this);
    GetMesh()->SetAnimInstanceClass(UStableHorseAnimInstance::StaticClass());
    UpdateGait(0.f);
}
void AStableRidingHorse::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AStableRidingHorse,Rider);
    DOREPLIFETIME(AStableRidingHorse,bRiddenCanter);
    DOREPLIFETIME(AStableRidingHorse,KeeperProfile);
    DOREPLIFETIME(AStableRidingHorse,RegisteredStall);
    DOREPLIFETIME(AStableRidingHorse,IndividualId);
    DOREPLIFETIME(AStableRidingHorse,BirthVersion);
    DOREPLIFETIME(AStableRidingHorse,HorseLevel);
    DOREPLIFETIME(AStableRidingHorse,bNeedsRecall);
    DOREPLIFETIME(AStableRidingHorse,VisitStartedAt);
    DOREPLIFETIME(AStableRidingHorse,VisitState);
    DOREPLIFETIME(AStableRidingHorse,Leader);
    DOREPLIFETIME(AStableRidingHorse,bLeftStall);
    DOREPLIFETIME(AStableRidingHorse,JumpState);
    DOREPLIFETIME(AStableRidingHorse,Health);
    DOREPLIFETIME(AStableRidingHorse,RetreatStartedAt);
    DOREPLIFETIME_CONDITION(AStableRidingHorse,Stamina,COND_OwnerOnly);
    DOREPLIFETIME(AStableRidingHorse,PivotDegreesPerSecond);
}
FQuat AStableRidingHorse::GroundTilt() const
{
    const auto* Body=Cast<UStableHorseGroundMesh>(GetMesh());
    return Body?Body->SurfaceTilt():FQuat::Identity;
}
FVector AStableRidingHorse::Saddle() const { return GetMesh()->GetSocketLocation(TEXT("saddle_socket")); }
FVector AStableRidingHorse::Stirrup(bool bLeft) const
{
    const auto* Skin=GetMesh();
    const FName Joint=bLeft?TEXT("stirrup_L"):TEXT("stirrup_R");
    const int32 Index=Skin->GetBoneIndex(Joint);
    if(Index==INDEX_NONE)return Skin->GetSocketLocation(Joint);
    // Offset from the leather pivot to the centre of the source mesh's iron tread,
    // measured in the horse's forward/right/up frame at bind pose (centimetres).
    const FVector RestOffset=bLeft?FVector(1.07,-3.75,-35.16):FVector(.51,5.16,-35.14);
    const FTransform Bind=Skin->GetSkeletalMeshAsset()->GetRefSkeleton().GetBoneAbsoluteTransform(Index);
    // Preserve the bind frame when client smoothing rotates the displayed mesh.
    const FTransform MountingFrame(GetBaseRotationOffset(),FVector::ZeroVector,Skin->GetRelativeScale3D());
    const FVector InBone=Bind.InverseTransformVector(MountingFrame.InverseTransformVector(RestOffset));
    return Skin->GetSocketTransform(Joint).TransformPosition(InBone);
}
void AStableRidingHorse::OnRep_Rider(AFPSGAMECharacter* PreviousRider)
{
    if(IsValid(PreviousRider))GetCapsuleComponent()->IgnoreActorWhenMoving(PreviousRider,false);
    if(IsValid(Rider))GetCapsuleComponent()->IgnoreActorWhenMoving(Rider,true);
}
void AStableRidingHorse::SetRider(AFPSGAMECharacter* NewRider)
{
    if(!HasAuthority()||(NewRider&&IsRetreating()))return;
    if(NewRider&&bFollowing)SetLeader(nullptr);
    auto* Previous=Rider.Get();
    Rider=NewRider;
    OnRep_Rider(Previous);
    // A rider may mount an unclaimed stable horse; the stamina HUD still belongs to that connection.
    APawn* KeeperPawn=KeeperModel.IsValid()?KeeperModel->RuntimePawn():nullptr;
    SetOwner(NewRider?NewRider->GetController():(KeeperPawn?KeeperPawn->GetController():nullptr));
    auto* Move=GetCharacterMovement();
    const bool bFinishInAir=InJump()&&Move->IsFalling();
    if(!bFinishInAir)Move->SetMovementMode(Rider?MOVE_Walking:MOVE_None);
    if(bFinishInAir)
    {
        Drive(0,0,false);
        ConsumeMovementInputVector();
    }
    else
    {
        if(!Rider&&InJump())SetJumpPhase(EStableJumpPhase::Grounded);
        Halt();
    }
    ForceNetUpdate();
}
void AStableRidingHorse::Drive(float Forward,float Turn,bool bCanter)
{
    Throttle=FMath::Clamp(Forward,-1.f,1.f);
    Steering=FMath::Clamp(Turn,-1.f,1.f);
    bWantsForwardCanter=bCanter && Throttle>0.f;
    RefreshRiddenCanter();
}
void AStableRidingHorse::RefreshRiddenCanter()
{
    if(!HasAuthority())return;
    const bool Canter=Rider && bWantsForwardCanter && !bExhausted && !IsRetreating();
    if(Canter==bRiddenCanter)return;
    bRiddenCanter=Canter;
    OnRep_RiddenCanter();
    ForceNetUpdate();
}
void AStableRidingHorse::OnRep_RiddenCanter()
{
    auto* Move=GetCharacterMovement();
    Move->SetWalkableFloorAngle(bRiddenCanter?StableGround::CanterAngle:StableGround::WalkAngle);
    Move->bForceNextFloorCheck=true;
}
void AStableRidingHorse::Halt()
{
    Drive(0,0,false);
    ConsumeMovementInputVector();
    GetCharacterMovement()->StopMovementImmediately();
}
double AStableRidingHorse::JumpClock() const
{
    const auto* GS=GetWorld()->GetGameState();
    return GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
}
void AStableRidingHorse::SetJumpPhase(EStableJumpPhase Next)
{
    JumpState.Phase=Next;
    JumpState.Since=JumpClock();
    ForceNetUpdate();
}
void AStableRidingHorse::BeginRiddenJump()
{
    if(!HasAuthority()||!Rider||bExhausted||IsRetreating()||InJump()||!JumpAnimation||
        !GetCharacterMovement()->IsMovingOnGround())return;
    if(const auto* Status=FindComponentByClass<UCombatStatusFormula>();Status&&Status->BlocksMovement())return;
    if(ClearBody(FVector::UpVector*28.f,GetActorRotation()))
        SetJumpPhase(EStableJumpPhase::Gathering);
}
void AStableRidingHorse::AdvanceJump(float Delta)
{
    auto* Move=GetCharacterMovement();
    const double Age=JumpClock()-JumpState.Since;
    if(JumpState.Phase==EStableJumpPhase::Gathering)
    {
        if(Age<StableJump::GatherSeconds)return;
        const float Gravity=-Move->GetGravityZ();
        if(!Rider||bExhausted||IsRetreating()||!Move->IsMovingOnGround()||Gravity<=0.f||
            !ClearBody(FVector::UpVector*28.f,GetActorRotation()))
        {
            SetJumpPhase(EStableJumpPhase::Grounded);
            return;
        }
        const float Lift=FMath::Sqrt(2.f*Gravity*Traits.JumpRise());
        JumpState.TimeToApex=Lift/Gravity;
        FVector Launch=FVector::VectorPlaneProject(Move->Velocity,FVector::UpVector);
        if(Throttle>0.f)
        {
            // A walking approach needs a forward push to carry the entire horse
            // across a rail. A cantering horse carries its existing momentum.
            const FVector Forward=GetActorForwardVector().GetSafeNormal2D();
            Launch+=Forward*FMath::Max(0.,500.-FVector::DotProduct(Launch,Forward));
        }
        Move->SetMovementMode(MOVE_Falling);
        Move->Velocity=Launch+FVector::UpVector*Lift;
        SetJumpPhase(EStableJumpPhase::Airborne);
    }
    if(JumpState.Phase==EStableJumpPhase::Airborne)
    {
        // CMC sweeps the central capsule. The additional sweeps protect the
        // head and the projecting quarters without erasing gravity at a wall.
        const FRotator Facing=GetActorRotation();
        FVector Rise=FVector::UpVector*FMath::Max(0.,Move->Velocity.Z*Delta);
        if(!Rise.IsNearlyZero()&&!ClearBody(Rise,Facing))
        {
            Move->Velocity.Z=0.;
            Rise=FVector::ZeroVector;
        }
        const FVector Across(Move->Velocity.X*Delta,Move->Velocity.Y*Delta,0.);
        if(!Across.IsNearlyZero()&&!ClearBody(Across+Rise,Facing))
            Move->Velocity.X=Move->Velocity.Y=0.;
    }
    else if(JumpState.Phase==EStableJumpPhase::Landing&&Age>=StableJump::LandSeconds)
    {
        SetJumpPhase(EStableJumpPhase::Grounded);
        if(!Rider&&!Leader)Move->DisableMovement();
    }
}
void AStableRidingHorse::Landed(const FHitResult& Hit)
{
    Super::Landed(Hit);
    if(HasAuthority()&&JumpState.Phase==EStableJumpPhase::Airborne)
        SetJumpPhase(EStableJumpPhase::Landing);
}
void AStableRidingHorse::PoseJump()
{
    auto* Skin=GetMesh();
    if(CurrentClip!=JumpAnimation)
    {
        Skin->SetAnimation(JumpAnimation);
        Skin->Play(false);
        Skin->SetPlayRate(0.f);
        CurrentClip=JumpAnimation;
    }
    const float Age=FMath::Max(0.,JumpClock()-JumpState.Since);
    float Frame=0.f;
    switch(JumpState.Phase)
    {
    case EStableJumpPhase::Gathering:
        Frame=StableJump::PushFrame*FMath::Min(Age/StableJump::GatherSeconds,1.f);
        break;
    case EStableJumpPhase::Airborne:
    {
        const float Half=Age/FMath::Max(JumpState.TimeToApex,.01f);
        Frame=Half<1.f?FMath::Lerp(StableJump::PushFrame,StableJump::ApexFrame,Half):
            FMath::Lerp(StableJump::ApexFrame,StableJump::ContactFrame-1.f,FMath::Min(Half-1.f,1.f));
        break;
    }
    case EStableJumpPhase::Landing:
        Frame=FMath::Lerp(StableJump::ContactFrame,StableJump::LastFrame,FMath::Min(Age/StableJump::LandSeconds,1.f));
        break;
    default: break;
    }
    Skin->SetPosition(JumpAnimation->GetPlayLength()*Frame/StableJump::LastFrame,false);
}
void AStableRidingHorse::Tick(float Delta)
{
    Super::Tick(Delta);
    if(IsRetreating())
    {
        TickRetreat(Delta);
        return;
    }
    if(VisitState!=EStableHorseVisit::Present){TickVisit(Delta);return;}
    const float PriorYaw=GetActorRotation().Yaw;
    if(HasAuthority())
    {
        const double Now=GetWorld()->GetTimeSeconds();
        if(!Rider && KeeperModel.IsValid() && Now>=NextFollowFeedback)
        {
            NextFollowFeedback=Now+.5;
            if(auto* OwnerPawn=KeeperModel->RuntimePawn())
                UpdateFollowFeedback(Now,FVector::Dist(GetActorLocation(),OwnerPawn->GetActorLocation()));
        }
        const bool Running=(Rider?bRiddenCanter:bFollowing && !bExhausted) &&
            GetVelocity().SizeSquared2D()>FMath::Square(325.f);
        UpdateStamina(Delta,Running);
        if(Rider)RefreshRiddenCanter();
        if(InJump())AdvanceJump(Delta);
    }
    const auto* Status=HasAuthority()&&(Rider||Leader)?FindComponentByClass<UCombatStatusFormula>():nullptr;
    const float MovementScale=Status?Status->MovementMultiplier():1.f;
    if(HasAuthority()&&MovementScale<=0.f&&!InJump())GetCharacterMovement()->StopMovementImmediately();
    if(HasAuthority()&&bFollowing&&MovementScale>0.f)Follow(Delta,MovementScale);
    if(HasAuthority()&&Rider&&MovementScale>0.f&&JumpState.Phase!=EStableJumpPhase::Airborne)
    {
        auto* Move=GetCharacterMovement();
        Move->MaxWalkSpeed=(Throttle<0.f?125.f:(bRiddenCanter?1160.f:220.f))*Traits.SpeedScale()*MovementScale;
        if(!FMath::IsNearlyZero(Steering))
        {
            FRotator Target=GetActorRotation();
            Target.Yaw+=Steering*(bRiddenCanter?68.f:88.f)*Traits.TurnScale()*Delta*MovementScale;
            if(ClearBody(FVector::ZeroVector,Target))SetActorRotation(Target);
        }
        if(!FMath::IsNearlyZero(Throttle))
        {
            const FVector Step=GetActorForwardVector()*Throttle*Move->MaxWalkSpeed*Delta;
            if(ClearBody(Step,GetActorRotation()))
                AddMovementInput(GetActorForwardVector(),Throttle,true);
            else Move->StopMovementImmediately();
        }
    }
    if(HasAuthority()&&!bLeftStall&&(Rider||Leader)&&GetVelocity().SizeSquared2D()>100.)
    {bLeftStall=true;ForceNetUpdate();}
    if(HasAuthority())
    {
        const float YawRate=Delta>SMALL_NUMBER ? FMath::FindDeltaAngleDegrees(PriorYaw,GetActorRotation().Yaw)/Delta : 0.f;
        const int8 Turn=(!InJump() && (Rider||Leader) && GetVelocity().SizeSquared2D()<FMath::Square(135.f))
            ? int8(4*FMath::RoundToInt(FMath::Clamp(YawRate,-108.f,108.f)/4.f)) : 0;
        if(Turn!=PivotDegreesPerSecond){PivotDegreesPerSecond=Turn;ForceNetUpdate();}
    }
    UpdateGait(Delta);
    Mane->UpdateMotion(Delta);
}
void AStableRidingHorse::UpdateGait(float Delta)
{
    GetMesh()->VisibilityBasedAnimTickOption=Rider?EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones:
        EVisibilityBasedAnimTickOption::AlwaysTickPose;
    const float Speed=GetVelocity().Size2D();
    const float Turn=InJump()?0.f:FMath::Sign(float(PivotDegreesPerSecond))*FMath::SmoothStep(2.f,28.f,float(FMath::Abs(int(PivotDegreesPerSecond))))*(1.f-FMath::SmoothStep(12.f,115.f,Speed));
    PivotWeight=FMath::Lerp(PivotWeight,Turn,1.f-FMath::Exp(-18.f*Delta));
    if(InJump()&&JumpAnimation){PoseJump();return;}
    // The authored rider holds these same irons and saddle through the horse's idle.
    if(Rider && IdleAnimation)
    {
        const auto* Transfer=Rider->FindComponentByClass<UHorseRiderComponent>();
        if(Transfer && Transfer->Transferring())
        {
            if(CurrentClip!=IdleAnimation)
            {
                GetMesh()->SetAnimation(IdleAnimation);
                GetMesh()->Play(true);
                CurrentClip=IdleAnimation;
            }
            GetMesh()->SetPlayRate(0.f);
            GetMesh()->SetPosition(FMath::Fmod(Transfer->TransferSeconds(),FMath::Max(IdleAnimation->GetPlayLength(),.001f)),false);
            return;
        }
    }
    const bool bBacking=FVector::DotProduct(GetVelocity(),GetActorForwardVector())<-8.f;
    UAnimSequence* Clip=Speed>325.f&&!bBacking?CanterAnimation.Get():Speed>8.f||IsSteppingInPlace()?WalkAnimation.Get():
        (!Rider&&!Leader&&!bLeftStall?StallAnimation.Get():IdleAnimation.Get());
    if(!Clip)return;
    if(CurrentClip!=Clip){GetMesh()->SetAnimation(Clip);GetMesh()->Play(true);CurrentClip=Clip;}
    float Rate=1.f;
    if(Clip==WalkAnimation||Clip==CanterAnimation)
    {
        Rate=FMath::Clamp(Speed/(Clip==WalkAnimation?220.f:660.f),.45f,Clip==CanterAnimation?2.f:1.35f);
        if(Clip==WalkAnimation)
        {
            const float StepRate=WalkAnimation->GetPlayLength()*FMath::Abs(int(PivotDegreesPerSecond))/60.f;
            Rate=FMath::Lerp(Rate,FMath::Clamp(StepRate,.45f,2.25f),FMath::Abs(PivotWeight));
            // Turning in the saddle must not switch a translating backstep to forward hoof contacts.
            if(bBacking)Rate=-Rate;
        }
    }
    if(!FMath::IsNearlyEqual(GetMesh()->GetPlayRate(),Rate))GetMesh()->SetPlayRate(Rate);
}
