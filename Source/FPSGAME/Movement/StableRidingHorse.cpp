#include "StableRidingHorse.h"
#include "StableHorseGear.h"
#include "StableHorseMarket.h"
#include "StableHorseAnimInstance.h"
#include "StableHorseGroundMesh.h"
#include "HorseRiderComponent.h"
#include "StableManeComponent.h"
#include "../UI/StatusEffectsComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "../Combat/CombatStatusFormula.h"
#include "../FPSGAMECharacter.h"
#include "../WorldGeneration/VillagePresentationView.h"
#include "HAL/IConsoleManager.h"
#include "Animation/AnimSequence.h"
#include "Materials/MaterialInterface.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "TimerManager.h"
#include "Net/UnrealNetwork.h"
#include "UObject/ConstructorHelpers.h"

namespace StableGround
{
    constexpr float WalkAngle=45.f;
    constexpr float CanterAngle=60.f;
    static float GHorseRTDistCm=2200.f;
    static FAutoConsoleVariableRef CVarHorseRTDistCm(
        TEXT("fps.Hills.HorseRayTracingDistCm"),
        GHorseRTDistCm,
        TEXT("Max camera distance (cm, +300 cm hysteresis) for unridden stable horses to stay visible in Ray Tracing. <= 0 keeps RT always on."),
        ECVF_Default);
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
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Camera,ECR_Block);

    auto ConfigureAuxCapsule=[](UCapsuleComponent* Cap,bool bBlockPawn)
    {
        Cap->SetCollisionObjectType(ECC_WorldDynamic);
        Cap->SetCollisionEnabled(bBlockPawn?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::QueryOnly);
        Cap->SetCollisionResponseToAllChannels(ECR_Ignore);
        if(bBlockPawn)Cap->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);
        Cap->SetCollisionResponseToChannel(ECC_Camera,ECR_Block);
        Cap->SetCanEverAffectNavigation(false);
        Cap->SetGenerateOverlapEvents(false);
        Cap->bApplyImpulseOnDamage=false;
    };
    ForebodyCollision=CreateDefaultSubobject<UCapsuleComponent>(TEXT("ForebodyCollision"));
    ForebodyCollision->SetupAttachment(GetCapsuleComponent());
    ForebodyCollision->InitCapsuleSize(32.f,76.f);
    ForebodyCollision->SetRelativeLocation(FVector(56.f,0.f,-6.f));
    ConfigureAuxCapsule(ForebodyCollision,true);

    HindbodyCollision=CreateDefaultSubobject<UCapsuleComponent>(TEXT("HindbodyCollision"));
    HindbodyCollision->SetupAttachment(GetCapsuleComponent());
    HindbodyCollision->InitCapsuleSize(32.f,74.f);
    HindbodyCollision->SetRelativeLocation(FVector(-54.f,0.f,-10.f));
    ConfigureAuxCapsule(HindbodyCollision,true);

    NeckCameraCollision=CreateDefaultSubobject<UCapsuleComponent>(TEXT("NeckCameraCollision"));
    NeckCameraCollision->SetupAttachment(GetMesh(),TEXT("neck_02"));
    NeckCameraCollision->InitCapsuleSize(21.f,34.f);
    ConfigureAuxCapsule(NeckCameraCollision,false);

    HeadCameraCollision=CreateDefaultSubobject<UCapsuleComponent>(TEXT("HeadCameraCollision"));
    HeadCameraCollision->SetupAttachment(GetMesh(),TEXT("head"));
    HeadCameraCollision->InitCapsuleSize(17.f,35.f);
    ConfigureAuxCapsule(HeadCameraCollision,false);

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
        auto FitBoneCameraCapsule=[&](UCapsuleComponent* Cap,FName HostBone,FName StartBone,FName EndBone,float RadiusCm,float EndPadCm)
        {
            const int32 Host=Ref.FindBoneIndex(HostBone),A=Ref.FindBoneIndex(StartBone),B=Ref.FindBoneIndex(EndBone);
            if(!Cap || Host==INDEX_NONE || A==INDEX_NONE || B==INDEX_NONE)return;
            const FTransform HostBind=Ref.GetBoneAbsoluteTransform(Host);
            const float BoneScale=FMath::Max(KINDA_SMALL_NUMBER,float(HostBind.GetScale3D().GetAbsMax()));
            const float InvScale=1.f/BoneScale;
            const FVector LocalA=HostBind.InverseTransformPosition(Ref.GetBoneAbsoluteTransform(A).GetLocation());
            const FVector LocalB=HostBind.InverseTransformPosition(Ref.GetBoneAbsoluteTransform(B).GetLocation());
            const FVector Span=LocalB-LocalA;
            const float Length=Span.Size();
            const FVector Dir=Length>KINDA_SMALL_NUMBER?Span/Length:FVector::UpVector;
            const float ScaledRadius=RadiusCm*InvScale;
            const float ScaledHalf=FMath::Max(ScaledRadius,Length*.5f+EndPadCm*InvScale);
            Cap->InitCapsuleSize(ScaledRadius,ScaledHalf);
            Cap->SetRelativeLocation((LocalA+LocalB)*.5f);
            Cap->SetRelativeRotation(FQuat::FindBetweenNormals(FVector::UpVector,Dir));
        };
        FitBoneCameraCapsule(NeckCameraCollision,TEXT("neck_02"),TEXT("neck_01"),TEXT("neck_03"),21.f,12.f);
        FitBoneCameraCapsule(HeadCameraCollision,TEXT("head"),TEXT("head"),TEXT("mouth_socket"),17.f,10.f);
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

    static constexpr const TCHAR* TackPaths[TackSlotCount]={
        TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/HorseTackR52/SK_Tack_Horseshoes_Mounted.SK_Tack_Horseshoes_Mounted"),
        TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/HorseTackR52/SK_Tack_Saddle_Mounted.SK_Tack_Saddle_Mounted"),
        TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/HorseTackR52/SK_Tack_Barding_Mounted.SK_Tack_Barding_Mounted"),
        TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/HorseTackR52/SK_Tack_Saddlebags_Mounted.SK_Tack_Saddlebags_Mounted"),
    };
    for(int32 I=0;I<TackSlotCount;++I)
    {
        ConstructorHelpers::FObjectFinder<USkeletalMesh> Found(TackPaths[I]);
        if(Found.Succeeded())TackMeshAssets[I]=Found.Object;
    }
}
void AStableRidingHorse::BeginPlay()
{
    Super::BeginPlay();
    // The streamed village may arrive before the terrain collider. Park idle residents
    // at their authored floor until a grounded player actually reaches the stirrup.
    if((HasAuthority()||bMarketShowcase)&&!Rider&&!bShowcaseCanRoam)GetCharacterMovement()->DisableMovement();
    if(HasAuthority()&&!bMarketShowcase)
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
    RefreshTackVisuals();
    UpdateHorseRayTracingVisibility(true);
    UStatusEffectsComponent::GetOrCreate(this);
    GetMesh()->SetAnimInstanceClass(UStableHorseAnimInstance::StaticClass());
    if(!bMarketShowcase)UpdateGait(0.f);
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
    DOREPLIFETIME(AStableRidingHorse,EquippedTackMask);
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
FVector AStableRidingHorse::GroundOffset() const
{
    const auto* Body=Cast<UStableHorseGroundMesh>(GetMesh());
    return Body?Body->SurfaceOffset():FVector::ZeroVector;
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
void AStableRidingHorse::UpdateAuxiliaryCollision(bool bCameraBlocking,bool bPawnBlocking)
{
    if(auto* RootCap=GetCapsuleComponent())
        RootCap->SetCollisionResponseToChannel(ECC_Camera,bCameraBlocking?ECR_Block:ECR_Ignore);
    auto SetBodyCap=[&](UCapsuleComponent* Cap)
    {
        if(!Cap)return;
        const bool bAny=bCameraBlocking||bPawnBlocking;
        Cap->SetCollisionEnabled(bPawnBlocking?ECollisionEnabled::QueryAndPhysics:(bCameraBlocking?ECollisionEnabled::QueryOnly:ECollisionEnabled::NoCollision));
        if(bAny)
        {
            Cap->SetCollisionResponseToChannel(ECC_Pawn,bPawnBlocking?ECR_Block:ECR_Ignore);
            Cap->SetCollisionResponseToChannel(ECC_Camera,bCameraBlocking?ECR_Block:ECR_Ignore);
        }
    };
    SetBodyCap(ForebodyCollision);
    SetBodyCap(HindbodyCollision);
    const ECollisionEnabled::Type CamMode=bCameraBlocking?ECollisionEnabled::QueryOnly:ECollisionEnabled::NoCollision;
    if(NeckCameraCollision)NeckCameraCollision->SetCollisionEnabled(CamMode);
    if(HeadCameraCollision)HeadCameraCollision->SetCollisionEnabled(CamMode);
}
void AStableRidingHorse::OnRep_Rider(AFPSGAMECharacter* PreviousRider)
{
    auto SetIgnore=[&](AFPSGAMECharacter* Target,bool bIgnore)
    {
        if(!IsValid(Target))return;
        GetCapsuleComponent()->IgnoreActorWhenMoving(Target,bIgnore);
        if(ForebodyCollision)ForebodyCollision->IgnoreActorWhenMoving(Target,bIgnore);
        if(HindbodyCollision)HindbodyCollision->IgnoreActorWhenMoving(Target,bIgnore);
    };
    if(IsValid(Rider) && RecentlyClearedRider.Get()==Rider.Get())
    {
        RecentlyClearedRider.Reset();
        RecentlyClearedUntil=0.;
    }
    if(IsValid(PreviousRider) && PreviousRider!=Rider && IsRetreating())
    {
        if(IsValid(RecentlyClearedRider.Get()) && RecentlyClearedRider.Get()!=PreviousRider)
            SetIgnore(RecentlyClearedRider.Get(),false);
        RecentlyClearedRider=PreviousRider;
        RecentlyClearedUntil=(GetWorld()?GetWorld()->GetTimeSeconds():0.)+0.65;
        SetIgnore(PreviousRider,true);
    }
    else
    {
        SetIgnore(PreviousRider,false);
    }
    SetIgnore(Rider,true);
}
void AStableRidingHorse::UpdateClearedRiderCollision(double Now)
{
    if(!RecentlyClearedRider.IsValid())
    {
        RecentlyClearedUntil=0.;
        return;
    }
    if(Now<RecentlyClearedUntil)return;
    if(AFPSGAMECharacter* Target=RecentlyClearedRider.Get(); IsValid(Target) && Target!=Rider)
    {
        GetCapsuleComponent()->IgnoreActorWhenMoving(Target,false);
        if(ForebodyCollision)ForebodyCollision->IgnoreActorWhenMoving(Target,false);
        if(HindbodyCollision)HindbodyCollision->IgnoreActorWhenMoving(Target,false);
    }
    RecentlyClearedRider.Reset();
    RecentlyClearedUntil=0.;
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
        const float JumpHeight=Traits.JumpRise()*(1.f+TackBonuses().JumpBonus);
        const float Lift=FMath::Sqrt(2.f*Gravity*JumpHeight);
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
void AStableRidingHorse::UpdateHorseRayTracingVisibility(bool bForce)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    UWorld* World=GetWorld();
    if(!World)return;
    const double Now=World->GetTimeSeconds();
    if(!bForce && Now<NextHorseRTCheckAt)return;
    NextHorseRTCheckAt=Now+0.5;

    bool bWantRT=true;
    if(!Rider && !bMarketShowcase && StableGround::GHorseRTDistCm>0.f)
    {
        bool bHasView=false;
        const double Dist=VillagePresentationView::Distance(*World,GetActorLocation(),0.,&bHasView);
        const double Cutoff=bHorseRTVisible?(double(StableGround::GHorseRTDistCm)+300.):double(StableGround::GHorseRTDistCm);
        bWantRT=bHasView && Dist<=Cutoff;
    }
    if(bForce || bWantRT!=bHorseRTVisible)
    {
        bHorseRTVisible=bWantRT;
        if(auto* Skin=GetMesh())Skin->SetVisibleInRayTracing(bWantRT);
        if(Mane)Mane->SetVisibleInRayTracing(bWantRT);
        for(const auto& Tack:TackVisuals)
            if(auto* Comp=Tack.Get())Comp->SetVisibleInRayTracing(bWantRT);
    }
}
void AStableRidingHorse::Tick(float Delta)
{
    Super::Tick(Delta);
    if(bMarketShowcase)
    {
        UpdateHorseRayTracingVisibility(false);
        TickShowcase(Delta);
        if(Mane)Mane->UpdateMotion(Delta);
        return;
    }
    UpdateHorseRayTracingVisibility(false);
    if(RecentlyClearedRider.IsValid() && GetWorld())
        UpdateClearedRiderCollision(GetWorld()->GetTimeSeconds());
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
        if(AffixBonuses.NaturalRegenPerSecondPct>0.f && !IsRetreating() && HasActiveKeeper() && Health>0.f && Health<MaxHealth)
        {
            NaturalRegenAccumulator+=Delta;
            if(NaturalRegenAccumulator>=1.f)
            {
                const float Steps=FMath::FloorToFloat(NaturalRegenAccumulator);
                NaturalRegenAccumulator-=Steps;
                Health=FMath::Min(MaxHealth,Health+MaxHealth*AffixBonuses.NaturalRegenPerSecondPct*Steps);
                if(Health>=MaxHealth)GetWorldTimerManager().ClearTimer(RestRecoveryTimer);
                CacheKeeperCondition(false);
                ForceNetUpdate();
            }
        }
        else NaturalRegenAccumulator=0.f;
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
        const auto Tack=TackBonuses();
        const float BaseSpeed=Throttle<0.f?125.f:(bRiddenCanter?1160.f:220.f);
        const float AffixSpeed=AffixBonuses.BaseMoveMultiplier*(bRiddenCanter?AffixBonuses.CanterSpeedMultiplier:1.f);
        Move->MaxWalkSpeed=BaseSpeed*Traits.SpeedScale()*AffixSpeed*(1.f+Tack.SpeedBonus)*MovementScale;
        if(!FMath::IsNearlyZero(Steering))
        {
            FRotator Target=GetActorRotation();
            Target.Yaw+=Steering*(bRiddenCanter?68.f:88.f)*Traits.TurnScale()*AffixBonuses.TurnMultiplier*(1.f+Tack.TurnBonus)*Delta*MovementScale;
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
double AStableRidingHorse::PointToHorseSegmentDistSq2D(const FVector& Point, const AStableRidingHorse& Horse)
{
    const FVector Loc = Horse.GetActorLocation();
    const FVector Fwd = Horse.GetActorForwardVector().GetSafeNormal2D();
    // Equine body horizontal spine segment: rump (-85 cm) to chest/muzzle (+105 cm).
    const FVector2D A(Loc.X - Fwd.X * 85., Loc.Y - Fwd.Y * 85.);
    const FVector2D B(Loc.X + Fwd.X * 105., Loc.Y + Fwd.Y * 105.);
    const FVector2D P(Point.X, Point.Y);
    const FVector2D AB = B - A;
    const double LenSq = AB.SizeSquared();
    const double T = LenSq > 1e-4 ? FMath::Clamp(FVector2D::DotProduct(P - A, AB) / LenSq, 0., 1.) : 0.;
    const FVector2D Closest = A + AB * T;
    return FVector2D::DistSquared(P, Closest);
}

bool AStableRidingHorse::SegmentClearsHorse2D(const FVector& From, const FVector& To, const AStableRidingHorse& Horse, double MinClearanceCm)
{
    const FVector Loc = Horse.GetActorLocation();
    const FVector Fwd = Horse.GetActorForwardVector().GetSafeNormal2D();
    const FVector2D P0(From.X, From.Y), P1(To.X, To.Y);
    const FVector2D D = P1 - P0;
    const double LenSq = D.SizeSquared();
    const double MinSq = FMath::Square(MinClearanceCm);
    // Test blocker's rump, center, and forehand against travel segment (zero physics cost).
    for (const double Along : { -80., 10., 100. })
    {
        const FVector2D Q(Loc.X + Fwd.X * Along, Loc.Y + Fwd.Y * Along);
        const double T = LenSq > 1e-4 ? FMath::Clamp(FVector2D::DotProduct(Q - P0, D) / LenSq, 0., 1.) : 0.;
        if (FVector2D::DistSquared(Q, P0 + D * T) < MinSq) return false;
    }
    return true;
}

bool AStableRidingHorse::IsBlockedByAnotherHorse(const FVector& MoveDir, bool bIncludeShowcase, const AStableRidingHorse** OutBlocker) const
{
    if (OutBlocker) *OutBlocker = nullptr;
    const UWorld* World = GetWorld();
    if (!World) return false;
    const FVector Dir = MoveDir.GetSafeNormal2D();
    if (Dir.IsNearlyZero()) return false;

    const FVector Loc = GetActorLocation();
    const FVector Right(-Dir.Y, Dir.X, 0.);
    // Probe forward nose-to-stride corridor (+70 cm .. +215 cm ahead of center) against every nearby horse's spine segment.
    const FVector ProbeNear = Loc + Dir * 80.;
    const FVector ProbeFar  = Loc + Dir * 205.;
    constexpr double CorridorHalfWidthSq = 112. * 112.;

    for (TActorIterator<AStableRidingHorse> It(World); It; ++It)
    {
        const AStableRidingHorse* Other = *It;
        if (Other == this || !IsValid(Other) || Other->IsActorBeingDestroyed()) continue;
        if (!bIncludeShowcase && Other->IsMarketShowcase()) continue;
        if (Other->IsShowcaseFadingOut() || Other->Visit() != EStableHorseVisit::Present) continue;

        const FVector Diff = Other->GetActorLocation() - Loc;
        // Fast coarse cull: skip horses > 3.6 m away horizontally or > 2.2 m vertically.
        if (FMath::Abs(Diff.Z) > 220. || Diff.SizeSquared2D() > FMath::Square(360.)) continue;

        // Check both near-nose and forward-step probes against the other horse's full rump-to-chest body segment.
        if (PointToHorseSegmentDistSq2D(ProbeNear, *Other) < CorridorHalfWidthSq ||
            PointToHorseSegmentDistSq2D(ProbeFar, *Other) < CorridorHalfWidthSq)
        {
            if (OutBlocker) *OutBlocker = Other;
            return true;
        }
        // Also catch an oblique blocker right across our forward bumper.
        const double Ahead = FVector::DotProduct(Diff, Dir);
        const double Side = FMath::Abs(FVector::DotProduct(Diff, Right));
        if (Ahead > 10. && Ahead < 225. && Side < 115.)
        {
            if (OutBlocker) *OutBlocker = Other;
            return true;
        }
    }
    return false;
}

void AStableRidingHorse::UpdateGait(float Delta)
{
    const float RawSpeed=GetVelocity().Size2D();
    const FVector Here=GetActorLocation();
    const float InstActualSpeed=(bHasLastGaitLocation && Delta>SMALL_NUMBER)
        ? float(FVector::Dist2D(Here,LastGaitLocation)/Delta) : RawSpeed;
    LastGaitLocation=Here;
    bHasLastGaitLocation=true;
    SmoothedActualSpeed=FMath::Lerp(SmoothedActualSpeed,InstActualSpeed,1.f-FMath::Exp(-14.f*Delta));
    // For AI-driven movement (unridden follow/recall, including replicated clients via Leader),
    // require real world translation so capsule pushing against another horse never triggers walking-in-place.
    const float Speed=(!Rider && (Leader || bFollowing || bFollowYieldPaused))
        ? (bFollowYieldPaused ? 0.f : FMath::Min(RawSpeed,SmoothedActualSpeed))
        : RawSpeed;
    const bool bParkedIdle=!Rider && !Leader && !InJump() && !IsRetreating() &&
        VisitState==EStableHorseVisit::Present && Speed<5.f;
    if(auto* Skin=GetMesh())
    {
        Skin->VisibilityBasedAnimTickOption=Rider
            ? EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones
            : (bParkedIdle ? EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered : EVisibilityBasedAnimTickOption::AlwaysTickPose);
        Skin->bEnableUpdateRateOptimizations=bParkedIdle;
    }
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

void AStableRidingHorse::ConfigureMarketShowcase(
    const FStableHorseOffer& Offer,bool bInStall,bool bCanFeed,
    const TArray<UAnimSequence*>& AmbientClips,float InitialPhase,bool bFadeIn,
    const FTransform& InVillageToWorld,const FVector2D& InLocalRoamMin,const FVector2D& InLocalRoamMax)
{
    bMarketShowcase=true;
    bShowcaseCanRoam=!bInStall;
    bShowcaseCanFeed=bCanFeed;
    ShowcasePrice=Offer.Price;
    ShowcaseVillageToWorld=InVillageToWorld;
    ShowcaseLocalRoamMin=InLocalRoamMin;
    ShowcaseLocalRoamMax=InLocalRoamMax;

    IndividualId=Offer.Horse.HorseId;
    BirthVersion=Offer.Horse.BirthVersion;
    HorseLevel=Offer.Horse.Level;
    Traits=FStableHorseTraits::FromId(IndividualId,BirthVersion,HorseLevel);
    AffixBonuses=StableHorseAffixes::Bonuses(IndividualId);
    MaxHealth=Traits.HealthLimit()*AffixBonuses.HealthMultiplier;
    MaxStamina=Traits.StaminaLimit()*AffixBonuses.StaminaMultiplier;
    Health=MaxHealth;
    Stamina=MaxStamina;
    AppliedAppearance.Invalidate();
    ApplyIndividualAppearance();

    // AmbientClips order: [0]=Feed, [1]=QIdle, [2]=QIdleLook, [3]=QHeadLow
    ShowcaseClipFeed=AmbientClips.IsValidIndex(0)?AmbientClips[0]:nullptr;
    ShowcaseClipQIdle=AmbientClips.IsValidIndex(1)?AmbientClips[1]:nullptr;
    ShowcaseClipQIdleLook=AmbientClips.IsValidIndex(2)?AmbientClips[2]:nullptr;
    ShowcaseClipQHeadLow=AmbientClips.IsValidIndex(3)?AmbientClips[3]:nullptr;

    if(auto* Move=GetCharacterMovement())
    {
        Move->bRunPhysicsWithNoController=true;
        Move->bCanWalkOffLedges=false;
        Move->SetWalkableFloorAngle(StableGround::WalkAngle);
        Move->MaxStepHeight=40.f;
        Move->MaxAcceleration=380.f;
        Move->BrakingDecelerationWalking=420.f;
        if(bShowcaseCanRoam)
        {
            Move->SetMovementMode(MOVE_Walking);
            Move->MaxWalkSpeed=160.f;
            Move->bForceNextFloorCheck=true;
        }
        else
        {
            Move->DisableMovement();
        }
    }
    if(auto* Skin=GetMesh())
    {
        Skin->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
        Skin->bEnableUpdateRateOptimizations=true;
    }
    if(auto* Cap=GetCapsuleComponent())
    {
        // Local non-replicated showcase horses must never create phantom Pawn walls across peers.
        Cap->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
    }

    LastShowcaseTickLoc=GetActorLocation();
    SmoothedShowcaseSpeed=0.f;
    ShowcaseMoveCooldownUntil=0.;
    ShowcaseRetryWaitUntil=0.;
    ShowcaseBlockRetries=0;
    ShowcaseLastBlocker.Reset();

    if(bInStall)
    {
        if(bCanFeed && ShowcaseClipFeed)EnterShowcaseState(EStableShowcaseState::StallFeed);
        else EnterShowcaseState(FMath::FRand()<0.45f?EStableShowcaseState::StallLook:EStableShowcaseState::StallIdle);
    }
    else
    {
        const float R=FMath::FRand();
        if(R<0.40f && PickShowcaseRoamTarget(ShowcaseWalkGoal))EnterShowcaseState(EStableShowcaseState::RoamTurn);
        else if(R<0.70f)EnterShowcaseState(EStableShowcaseState::RoamGraze);
        else EnterShowcaseState(R<0.85f?EStableShowcaseState::RoamLook:EStableShowcaseState::RoamIdle);
    }
    if(CurrentClip && InitialPhase>0.f && GetMesh())
    {
        const float Len=FMath::Max(CurrentClip->GetPlayLength(),.01f);
        GetMesh()->SetPosition(FMath::Fmod(InitialPhase,Len),false);
    }

    if(bFadeIn)
    {
        ShowcaseFadeDir=-1;
        ShowcaseFadeProgress=1.f;
        ApplyHorseFade(1.f);
    }
    else
    {
        ShowcaseFadeDir=0;
        ShowcaseFadeProgress=0.f;
        ApplyHorseFade(0.f);
    }
    UpdateAuxiliaryCollision(true,false);
}

void AStableRidingHorse::PlayShowcaseClip(UAnimSequence* Clip,float Rate,float Phase)
{
    auto* Skin=GetMesh();
    if(!Skin || !Clip)return;
    if(CurrentClip!=Clip)
    {
        Skin->SetAnimation(Clip);
        Skin->Play(true);
        CurrentClip=Clip;
        StallAnimation=Clip;
        if(Phase>=0.f)
            Skin->SetPosition(FMath::Fmod(Phase,FMath::Max(Clip->GetPlayLength(),.01f)),false);
    }
    if(!FMath::IsNearlyEqual(Skin->GetPlayRate(),Rate))Skin->SetPlayRate(Rate);
}

bool AStableRidingHorse::PickShowcaseRoamTarget(FVector& OutWorldGoal, const AStableRidingHorse* AvoidBlocker) const
{
    UWorld* World=GetWorld();
    if(!World || !bShowcaseCanRoam)return false;
    const FVector CurrentWorld=GetActorLocation();
    const FVector2D MinP=ShowcaseLocalRoamMin+FVector2D(35.,35.);
    const FVector2D MaxP=ShowcaseLocalRoamMax-FVector2D(35.,35.);
    if(MinP.X>=MaxP.X || MinP.Y>=MaxP.Y)return false;

    const FVector BlockerDir=(IsValid(AvoidBlocker))
        ? (AvoidBlocker->GetActorLocation()-CurrentWorld).GetSafeNormal2D()
        : FVector::ZeroVector;

    FCollisionQueryParams Query(SCENE_QUERY_STAT(ShowcaseRoamGround),false,this);
    for(int32 Attempt=0;Attempt<16;++Attempt)
    {
        const double LX=FMath::FRandRange(MinP.X,MaxP.X);
        const double LY=FMath::FRandRange(MinP.Y,MaxP.Y);
        FVector Candidate=ShowcaseVillageToWorld.TransformPosition(FVector(LX,LY,0.));
        if(FVector::DistSquared2D(Candidate,CurrentWorld)<FMath::Square(210.))continue;

        // When re-routing away from a blocking horse, prefer destinations clearly angled away from it.
        if(!BlockerDir.IsNearlyZero())
        {
            const FVector CandDir=(Candidate-CurrentWorld).GetSafeNormal2D();
            if(FVector::DotProduct(CandDir,BlockerDir)>0.35)continue;
        }

        bool bCrowded=false;
        for(TActorIterator<AStableRidingHorse> It(World);It;++It)
        {
            const AStableRidingHorse* Other=*It;
            if(Other==this || !IsValid(Other) || Other->IsActorBeingDestroyed())continue;
            // Keep both the destination AND the straight walking corridor clear of every other horse's body.
            if(PointToHorseSegmentDistSq2D(Candidate,*Other)<FMath::Square(220.) ||
               !SegmentClearsHorse2D(CurrentWorld,Candidate,*Other,150.))
            {bCrowded=true;break;}
            if(Other->bMarketShowcase && Other->bShowcaseCanRoam &&
               (Other->ShowcaseState==EStableShowcaseState::RoamWalk || Other->ShowcaseState==EStableShowcaseState::RoamTurn) &&
               FVector::DistSquared2D(Candidate,Other->ShowcaseWalkGoal)<FMath::Square(240.))
            {bCrowded=true;break;}
        }
        if(bCrowded)continue;

        for(FConstPlayerControllerIterator It=World->GetPlayerControllerIterator();It;++It)
        {
            const APawn* PlayerPawn=It->IsValid()?It->Get()->GetPawn():nullptr;
            if(IsValid(PlayerPawn) && FVector::DistSquared2D(Candidate,PlayerPawn->GetActorLocation())<FMath::Square(190.))
            {bCrowded=true;break;}
        }
        if(bCrowded)continue;

        TArray<FHitResult> Hits;
        const FVector Start(Candidate.X,Candidate.Y,Candidate.Z+65.);
        const FVector End(Candidate.X,Candidate.Y,Candidate.Z-160.);
        if(!World->LineTraceMultiByChannel(Hits,Start,End,ECC_Pawn,Query))continue;
        bool bGrounded=false;
        for(const FHitResult& H:Hits)
        {
            if(!H.bBlockingHit || H.bStartPenetrating || H.ImpactNormal.Z<0.78f || Cast<APawn>(H.GetActor()))continue;
            if(H.ImpactPoint.Z>Candidate.Z+38. || H.ImpactPoint.Z<Candidate.Z-60.)continue;
            Candidate.Z=H.ImpactPoint.Z;
            bGrounded=true;
            break;
        }
        if(!bGrounded)continue;

        OutWorldGoal=Candidate;
        return true;
    }
    return false;
}

void AStableRidingHorse::EnterShowcaseState(EStableShowcaseState NextState)
{
    ShowcaseState=NextState;
    const double Now=GetWorld()?GetWorld()->GetTimeSeconds():0.;
    auto* Move=GetCharacterMovement();

    switch(NextState)
    {
    case EStableShowcaseState::StallFeed:
        ShowcaseStateEndsAt=Now+FMath::FRandRange(10.f,18.f);
        PlayShowcaseClip(ShowcaseClipFeed?ShowcaseClipFeed.Get():IdleAnimation.Get(),1.f);
        break;
    case EStableShowcaseState::StallIdle:
        ShowcaseStateEndsAt=Now+FMath::FRandRange(5.5f,10.5f);
        PlayShowcaseClip((ShowcaseClipQIdle && FMath::FRand()<0.5f)?ShowcaseClipQIdle.Get():IdleAnimation.Get(),1.f);
        break;
    case EStableShowcaseState::StallLook:
        ShowcaseStateEndsAt=Now+FMath::FRandRange(4.0f,7.5f);
        PlayShowcaseClip(ShowcaseClipQIdleLook?ShowcaseClipQIdleLook.Get():IdleAnimation.Get(),1.f);
        break;
    case EStableShowcaseState::RoamIdle:
        if(Move)Move->StopMovementImmediately();
        ShowcaseStateEndsAt=Now+FMath::FRandRange(4.0f,8.5f);
        PlayShowcaseClip((ShowcaseClipQIdle && FMath::FRand()<0.5f)?ShowcaseClipQIdle.Get():IdleAnimation.Get(),1.f);
        break;
    case EStableShowcaseState::RoamLook:
        if(Move)Move->StopMovementImmediately();
        ShowcaseStateEndsAt=Now+FMath::FRandRange(3.5f,6.5f);
        PlayShowcaseClip(ShowcaseClipQIdleLook?ShowcaseClipQIdleLook.Get():IdleAnimation.Get(),1.f);
        break;
    case EStableShowcaseState::RoamGraze:
        if(Move)Move->StopMovementImmediately();
        ShowcaseStateEndsAt=Now+FMath::FRandRange(5.5f,10.0f);
        PlayShowcaseClip(ShowcaseClipQHeadLow?ShowcaseClipQHeadLow.Get():IdleAnimation.Get(),1.f);
        break;
    case EStableShowcaseState::RoamTurn:
        if(Move)Move->StopMovementImmediately();
        ShowcaseStateEndsAt=Now+3.5;
        ShowcaseTurnStallSeconds=0.f;
        LastShowcaseTurnYaw=GetActorRotation().Yaw;
        NextShowcaseYieldScan=Now+FMath::FRandRange(0.02f,0.10f);
        bCachedShowcaseYield=false;
        ShowcaseRetryWaitUntil=0.;
        break;
    case EStableShowcaseState::RoamWalk:
        ShowcaseWalkSpeed=FMath::FRandRange(148.f,178.f);
        if(Move)
        {
            if(Move->MovementMode!=MOVE_Walking)Move->SetMovementMode(MOVE_Walking);
            Move->MaxWalkSpeed=ShowcaseWalkSpeed;
        }
        ShowcaseStateEndsAt=Now+14.0;
        ShowcaseWalkStuckSince=Now;
        ShowcaseWalkProgressLoc=GetActorLocation();
        // Stagger initial check jitter across horses so multiple horses never scan on the same frame.
        NextShowcaseYieldScan=Now+FMath::FRandRange(0.03f,0.12f);
        NextShowcaseClearCheck=0.;
        bCachedShowcaseYield=false;
        bCachedShowcaseForwardClear=true;
        ShowcaseRetryWaitUntil=0.;
        break;
    }
}

void AStableRidingHorse::BeginShowcaseFadeOut()
{
    if(!bMarketShowcase || ShowcaseFadeDir>0)return;
    SetActorTickEnabled(true);
    ShowcaseFadeDir=1;
    if(auto* Move=GetCharacterMovement(); Move && bShowcaseCanRoam)Move->StopMovementImmediately();
    // Continue cleanly from current fade value if interrupted mid fade-in.
    ApplyHorseFade(FMath::SmoothStep(0.f,1.f,ShowcaseFadeProgress));
}

void AStableRidingHorse::TickShowcase(float Delta)
{
    if(ShowcaseFadeDir<0)
    {
        constexpr float FadeInSeconds=1.15f;
        ShowcaseFadeProgress=FMath::Max(0.f,ShowcaseFadeProgress-Delta/FadeInSeconds);
        ApplyHorseFade(FMath::SmoothStep(0.f,1.f,ShowcaseFadeProgress));
        if(ShowcaseFadeProgress<=0.f)
        {
            ShowcaseFadeDir=0;
            ApplyHorseFade(0.f);
        }
    }
    else if(ShowcaseFadeDir>0)
    {
        constexpr float FadeOutSeconds=0.85f;
        ShowcaseFadeProgress=FMath::Min(1.f,ShowcaseFadeProgress+Delta/FadeOutSeconds);
        ApplyHorseFade(FMath::SmoothStep(0.f,1.f,ShowcaseFadeProgress));
        if(ShowcaseFadeProgress>=.5f)UpdateAuxiliaryCollision(false,false);
        if(ShowcaseFadeProgress>=1.f)
        {
            Destroy();
            return;
        }
        // Decelerate to calm idle while fading out.
        PivotWeight=FMath::Lerp(PivotWeight,0.f,1.f-FMath::Exp(-12.f*Delta));
        if(GetVelocity().Size2D()<10.f)PlayShowcaseClip(IdleAnimation.Get(),1.f);
        return;
    }

    UWorld* World=GetWorld();
    if(!World)return;
    const double Now=World->GetTimeSeconds();

    // --- Barn stall state machine (stationary, grounded in stall) ---
    if(!bShowcaseCanRoam)
    {
        PivotWeight=0.f;
        if(Now>=ShowcaseStateEndsAt)
        {
            if(bShowcaseCanFeed && ShowcaseClipFeed)
            {
                const float R=FMath::FRand();
                if(ShowcaseState==EStableShowcaseState::StallFeed)
                    EnterShowcaseState(R<0.55f?EStableShowcaseState::StallLook:EStableShowcaseState::StallIdle);
                else
                    EnterShowcaseState(R<0.68f?EStableShowcaseState::StallFeed:(ShowcaseState==EStableShowcaseState::StallLook?EStableShowcaseState::StallIdle:EStableShowcaseState::StallLook));
            }
            else
            {
                EnterShowcaseState(ShowcaseState==EStableShowcaseState::StallLook?EStableShowcaseState::StallIdle:EStableShowcaseState::StallLook);
            }
        }
        return;
    }

    // --- Entrance forecourt roaming state machine (MOVE_Walking + Walk/Turn/Idle/Look/Graze) ---
    auto* Move=GetCharacterMovement();
    if(Move && Move->MovementMode==MOVE_None)Move->SetMovementMode(MOVE_Walking);

    const auto PickNextStationary=[&](EStableShowcaseState Exclude)
    {
        const float R=FMath::FRand();
        if(Exclude==EStableShowcaseState::RoamGraze)
            EnterShowcaseState(R<0.55f?EStableShowcaseState::RoamIdle:EStableShowcaseState::RoamLook);
        else if(Exclude==EStableShowcaseState::RoamLook)
            EnterShowcaseState(R<0.55f?EStableShowcaseState::RoamGraze:EStableShowcaseState::RoamIdle);
        else if(Exclude==EStableShowcaseState::RoamIdle)
            EnterShowcaseState(R<0.60f?EStableShowcaseState::RoamGraze:EStableShowcaseState::RoamLook);
        else
            EnterShowcaseState(R<0.40f?EStableShowcaseState::RoamGraze:(R<0.75f?EStableShowcaseState::RoamIdle:EStableShowcaseState::RoamLook));
    };

    const FVector Loc=GetActorLocation();
    const float InstDispSpeed=Delta>SMALL_NUMBER ? float(FVector::Dist2D(Loc,LastShowcaseTickLoc)/Delta) : 0.f;
    LastShowcaseTickLoc=Loc;
    SmoothedShowcaseSpeed=FMath::Lerp(SmoothedShowcaseSpeed,InstDispSpeed,1.f-FMath::Exp(-14.f*Delta));
    float DesiredPivot=0.f;
    bool bTurnAdvanced=false;

    const auto AbortMoveIntoCooldown=[&](EStableShowcaseState FromState,double MinCooldown,double MaxCooldown)
    {
        if(Move)Move->StopMovementImmediately();
        ShowcaseBlockRetries=0;
        ShowcaseRetryWaitUntil=0.;
        ShowcaseMoveCooldownUntil=Now+FMath::FRandRange(float(MinCooldown),float(MaxCooldown));
        PickNextStationary(FromState);
    };

    if(ShowcaseState==EStableShowcaseState::RoamTurn)
    {
        const FVector ToGoal=(ShowcaseWalkGoal-Loc).GetSafeNormal2D();
        if(ToGoal.IsNearlyZero() || Now>=ShowcaseStateEndsAt)
        {
            AbortMoveIntoCooldown(EStableShowcaseState::RoamTurn,4.5,7.5);
        }
        else
        {
            // Performance-friendly 0.25s check: if another horse already occupies our desired exit path, stop turning.
            if(Now>=NextShowcaseYieldScan)
            {
                NextShowcaseYieldScan=Now+0.25;
                const AStableRidingHorse* Blocker=nullptr;
                bCachedShowcaseYield=IsBlockedByAnotherHorse(ToGoal,true,&Blocker);
                if(bCachedShowcaseYield)ShowcaseLastBlocker=Blocker;
            }
            if(bCachedShowcaseYield)
            {
                AbortMoveIntoCooldown(EStableShowcaseState::RoamTurn,5.5,8.5);
            }
            else
            {
                const float CurYaw=GetActorRotation().Yaw;
                const float TargetYaw=ToGoal.Rotation().Yaw;
                const float AngleDiff=FMath::FindDeltaAngleDegrees(CurYaw,TargetYaw);
                if(FMath::Abs(AngleDiff)<=16.f)
                {
                    EnterShowcaseState(EStableShowcaseState::RoamWalk);
                }
                else
                {
                    constexpr float TurnRateDeg=56.f;
                    const float StepYaw=FMath::Clamp(AngleDiff,-TurnRateDeg*Delta,TurnRateDeg*Delta);
                    const FRotator NextRot(0.f,CurYaw+StepYaw,0.f);
                    if(ClearBody(FVector::ZeroVector,NextRot))
                    {
                        SetActorRotation(NextRot);
                        DesiredPivot=FMath::Sign(AngleDiff)*0.78f;
                        bTurnAdvanced=true;
                        if(FMath::Abs(FMath::FindDeltaAngleDegrees(CurYaw,LastShowcaseTurnYaw))>4.f)
                        {
                            LastShowcaseTurnYaw=CurYaw;
                            ShowcaseTurnStallSeconds=0.f;
                        }
                        else ShowcaseTurnStallSeconds+=Delta;
                    }
                    else
                    {
                        ShowcaseTurnStallSeconds+=Delta;
                    }
                    // Brief turn retry limit (0.55s): immediately give up instead of stepping in place.
                    if(ShowcaseTurnStallSeconds>=0.55f)
                        AbortMoveIntoCooldown(EStableShowcaseState::RoamTurn,5.5,8.5);
                }
            }
        }
    }
    else if(ShowcaseState==EStableShowcaseState::RoamWalk)
    {
        const FVector ToGoal=ShowcaseWalkGoal-Loc;
        const double Dist2D=ToGoal.Size2D();
        const FVector LocalPos=ShowcaseVillageToWorld.InverseTransformPosition(Loc);
        const bool bOutOfBounds=LocalPos.X<ShowcaseLocalRoamMin.X-30. || LocalPos.X>ShowcaseLocalRoamMax.X+30.
            || LocalPos.Y<ShowcaseLocalRoamMin.Y-30. || LocalPos.Y>ShowcaseLocalRoamMax.Y+30.;

        // If we are in a brief yield pause waiting for a blocking horse to clear, stand calmly (zero movement/stepping).
        if(ShowcaseRetryWaitUntil>0.)
        {
            if(Move)Move->StopMovementImmediately();
            if(Now>=ShowcaseRetryWaitUntil)
            {
                ShowcaseRetryWaitUntil=0.;
                const FVector Forward=GetActorForwardVector().GetSafeNormal2D();
                const AStableRidingHorse* Blocker=nullptr;
                const bool bStillHorseBlocked=IsBlockedByAnotherHorse(Forward,true,&Blocker);
                const bool bStillForwardBlocked=!ClearBody(Forward*45.f,GetActorRotation());
                if(!bStillHorseBlocked && !bStillForwardBlocked)
                {
                    // Corridor cleared during the brief pause -> resume smoothly.
                    ShowcaseWalkStuckSince=Now;
                    ShowcaseWalkProgressLoc=Loc;
                    bCachedShowcaseYield=false;
                    bCachedShowcaseForwardClear=true;
                }
                else
                {
                    // Still blocked after brief retry -> stop trying to move and enter calm idle with cooldown!
                    AbortMoveIntoCooldown(EStableShowcaseState::RoamWalk,6.0,9.5);
                }
            }
        }
        else
        {
            // Performance-friendly 0.25s (4 Hz) blocker + real-displacement check.
            bool bTriggerBlockResolution=false;
            if(Now>=NextShowcaseYieldScan)
            {
                NextShowcaseYieldScan=Now+0.25;
                bCachedShowcaseYield=false;
                const FVector Forward=GetActorForwardVector().GetSafeNormal2D();
                const AStableRidingHorse* Blocker=nullptr;
                if(IsBlockedByAnotherHorse(Forward,true,&Blocker))
                {
                    bCachedShowcaseYield=true;
                    ShowcaseLastBlocker=Blocker;
                }
                else
                {
                    for(FConstPlayerControllerIterator It=World->GetPlayerControllerIterator();It;++It)
                    {
                        const APawn* PlayerPawn=It->IsValid()?It->Get()->GetPawn():nullptr;
                        if(!IsValid(PlayerPawn))continue;
                        const FVector Diff=PlayerPawn->GetActorLocation()-Loc;
                        if(Diff.SizeSquared2D()<FMath::Square(185.) && FVector::DotProduct(Forward,Diff.GetSafeNormal2D())>0.15f)
                        {bCachedShowcaseYield=true;ShowcaseLastBlocker.Reset();break;}
                    }
                }
                if(FVector::DistSquared2D(Loc,ShowcaseWalkProgressLoc)>=FMath::Square(16.))
                {
                    ShowcaseWalkProgressLoc=Loc;
                    ShowcaseWalkStuckSince=Now;
                }
                const bool bStalled=(Now-ShowcaseWalkStuckSince)>=0.75;
                bTriggerBlockResolution=bCachedShowcaseYield || bStalled;
            }

            // Throttled 0.20s (5 Hz) forward obstacle sweep instead of per-frame ClearBody spam.
            if(!bTriggerBlockResolution && Now>=NextShowcaseClearCheck)
            {
                NextShowcaseClearCheck=Now+0.20;
                const FVector Forward=GetActorForwardVector().GetSafeNormal2D();
                bCachedShowcaseForwardClear=ClearBody(Forward*50.f,GetActorRotation());
                if(!bCachedShowcaseForwardClear)bTriggerBlockResolution=true;
            }

            const bool bArrived=Dist2D<=55.;
            const bool bTimedOut=Now>=ShowcaseStateEndsAt;

            if(bArrived || bTimedOut || bOutOfBounds)
            {
                if(Move)Move->StopMovementImmediately();
                ShowcaseBlockRetries=0;
                PickNextStationary(EStableShowcaseState::RoamWalk);
            }
            else if(bTriggerBlockResolution)
            {
                if(Move)Move->StopMovementImmediately();
                // Allow at most 1 brief retry: if blocked by a horse, either pick one clear alternate spot
                // away from the blocker, or pause briefly (0.65s) in case the other horse moves past;
                // if already retried once, immediately stop trying to move!
                if(ShowcaseBlockRetries==0)
                {
                    ++ShowcaseBlockRetries;
                    const AStableRidingHorse* Blocker=ShowcaseLastBlocker.Get();
                    const bool bBlockerMoving=Blocker && Blocker->GetVelocity().SizeSquared2D()>FMath::Square(25.f);
                    FVector AltGoal;
                    if(!bBlockerMoving && PickShowcaseRoamTarget(AltGoal,Blocker))
                    {
                        ShowcaseWalkGoal=AltGoal;
                        EnterShowcaseState(EStableShowcaseState::RoamTurn);
                    }
                    else
                    {
                        ShowcaseRetryWaitUntil=Now+0.65;
                    }
                }
                else
                {
                    AbortMoveIntoCooldown(EStableShowcaseState::RoamWalk,6.0,9.5);
                }
            }
            else
            {
                const float CurYaw=GetActorRotation().Yaw;
                const float TargetYaw=ToGoal.GetSafeNormal2D().Rotation().Yaw;
                const float AngleDiff=FMath::FindDeltaAngleDegrees(CurYaw,TargetYaw);
                constexpr float SteerRateDeg=72.f;
                const float StepYaw=FMath::Clamp(AngleDiff,-SteerRateDeg*Delta,SteerRateDeg*Delta);
                if(FMath::Abs(StepYaw)>0.05f)
                {
                    const FRotator NextRot(0.f,CurYaw+StepYaw,0.f);
                    SetActorRotation(NextRot);
                }

                const FVector MoveDir=GetActorForwardVector().GetSafeNormal2D();
                // Gently slow down as we approach the final 130 cm for a natural stop.
                const float ApproachScale=FMath::Clamp(float(Dist2D)/130.f,0.48f,1.f);
                if(Move)Move->MaxWalkSpeed=ShowcaseWalkSpeed*ApproachScale;
                AddMovementInput(MoveDir,1.f,true);
            }
        }
    }
    else if(Now>=ShowcaseStateEndsAt)
    {
        // Stationary forecourt states (RoamIdle / RoamLook / RoamGraze) -> respect move cooldown after a block.
        const float WalkProb=(ShowcaseState==EStableShowcaseState::RoamLook)?0.65f:0.55f;
        if(Now>=ShowcaseMoveCooldownUntil && FMath::FRand()<WalkProb && PickShowcaseRoamTarget(ShowcaseWalkGoal))
        {
            ShowcaseBlockRetries=0;
            ShowcaseLastBlocker.Reset();
            EnterShowcaseState(EStableShowcaseState::RoamTurn);
        }
        else
        {
            PickNextStationary(ShowcaseState);
        }
    }

    // Drive walking / turning / stationary clips strictly from true ground displacement (prevents walking in place!).
    const float VelSpeed=GetVelocity().Size2D();
    const float EffectiveWalkSpeed=(ShowcaseState==EStableShowcaseState::RoamWalk && ShowcaseRetryWaitUntil<=0.)
        ? FMath::Min(VelSpeed,SmoothedShowcaseSpeed) : 0.f;
    PivotWeight=FMath::Lerp(PivotWeight,DesiredPivot,1.f-FMath::Exp(-14.f*Delta));
    const bool bShouldStepTurn=(ShowcaseState==EStableShowcaseState::RoamTurn && bTurnAdvanced && FMath::Abs(PivotWeight)>0.15f);
    if(EffectiveWalkSpeed>12.f || bShouldStepTurn)
    {
        if(WalkAnimation)
        {
            float Rate=FMath::Clamp(EffectiveWalkSpeed/220.f,0.48f,1.15f);
            if(EffectiveWalkSpeed<=12.f)Rate=0.72f;
            PlayShowcaseClip(WalkAnimation.Get(),Rate);
        }
    }
    else if(ShowcaseState==EStableShowcaseState::RoamWalk || ShowcaseState==EStableShowcaseState::RoamTurn)
    {
        PlayShowcaseClip(IdleAnimation.Get(),1.f);
    }
}
