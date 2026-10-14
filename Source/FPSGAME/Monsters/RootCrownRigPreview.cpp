#include "RootCrownRigPreview.h"
#include "MonsterCharacterMovementComponent.h"
#include "RootCrownMovementComponent.h"
#include "RootCrownAnimInstance.h"
#include "RootCrownHitComponent.h"
#include "MonsterIdleBreathingMeshComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "UObject/ConstructorHelpers.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/SkeletalMesh.h"

ARootCrownRigPreview::ARootCrownRigPreview(const FObjectInitializer& Initializer)
    : Super(Initializer.SetDefaultSubobjectClass<URootCrownMovementComponent>(CharacterMovementComponentName)
        .SetDefaultSubobjectClass<UMonsterIdleBreathingMeshComponent>(MeshComponentName))
{
    PrimaryActorTick.bCanEverTick=true;
    bReplicates=true;
    SetReplicateMovement(true);
    SetNetUpdateFrequency(30.f);SetMinNetUpdateFrequency(15.f);
    Combat=CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    HitDetection=CreateDefaultSubobject<URootCrownHitComponent>(TEXT("HitDetection"));
    CorpseRagdoll=CreateDefaultSubobject<UMonsterCorpseRagdollComponent>(TEXT("CorpseRagdoll"));
    SlashVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("SlashGesture"));
    ContactVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("SlashContact"));
    ReactionVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("ReactionVoice"));
    for (UAudioComponent* Voice:{SlashVoice.Get(),ContactVoice.Get(),ReactionVoice.Get()})
    {
        Voice->SetupAttachment(GetMesh(),TEXT("Crown_Base"));Voice->bAutoActivate=false;Voice->bAutoDestroy=false;
        Voice->bOverrideAttenuation=true;Voice->AttenuationOverrides.bAttenuate=true;
        Voice->AttenuationOverrides.bSpatialize=true;Voice->AttenuationOverrides.FalloffDistance=1600.f;
    }
    GetCapsuleComponent()->InitCapsuleSize(175.f,175.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
    GetMesh()->SetCollisionProfileName(TEXT("PhysicsActor"));
    GetMesh()->SetCollisionObjectType(ECC_Pawn);
    GetMesh()->SetCanEverAffectNavigation(false);
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
    static ConstructorHelpers::FClassFinder<AMonsterAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    AIControllerClass=AI.Succeeded()?AI.Class.Get():AMonsterAIController::StaticClass();
    AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;
    bUseControllerRotationYaw=false;BaseEyeHeight=80.f;
    auto* Move=GetCharacterMovement();Move->MaxWalkSpeed=WalkSpeed;
    Move->MaxAcceleration=360.f;Move->BrakingDecelerationWalking=600.f;
    Move->RotationRate=FRotator(0,TurnSpeed,0);
    Move->bOrientRotationToMovement=true;Move->bUseControllerDesiredRotation=false;
    Move->bCanWalkOffLedges=false;
    Tags.Add(TEXT("Enemy"));Tags.Add(TEXT("RootCrown"));
    CastChecked<UMonsterCharacterMovementComponent>(GetCharacterMovement())->ConfigureWideBodyStairs(225.f,450.f);
}

void ARootCrownRigPreview::ApplyRig()
{
    CastChecked<UMonsterCharacterMovementComponent>(GetCharacterMovement())->ConfigureWideBodyStairs(225.f,450.f);
    if(!VisualMesh)return;
    auto* Component=GetMesh();Component->SetSkeletalMeshAsset(VisualMesh);
    const FBoxSphereBounds Bounds=VisualMesh->GetBounds();
    const double Scale=350./FMath::Max(1.,double(Bounds.BoxExtent.Z)*2.);
    Component->SetRelativeScale3D(FVector(Scale));
    // Authored Blender -Y faces front; FBX maps it to mesh +Y, as the existing M rigs do.
    Component->SetRelativeRotation(FRotator(0,-90,0));
    Component->SetRelativeLocation(FVector(0,0,-175.-(Bounds.Origin.Z-Bounds.BoxExtent.Z)*Scale));
    Component->SetAnimInstanceClass(URootCrownAnimInstance::StaticClass());
    if(HitSurfacePhysics)Component->SetPhysicsAsset(HitSurfacePhysics);
    Component->SetCollisionObjectType(ECC_Pawn);
    Component->SetCollisionResponseToAllChannels(ECR_Ignore);
    Component->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    Component->SetCollisionEnabled(Dead()?ECollisionEnabled::NoCollision:ECollisionEnabled::QueryOnly);
    if (SlashMaterial) Component->SetMaterial(0,SlashMaterial);
    const auto& Ref=VisualMesh->GetRefSkeleton();
    const int32 RootIndex=Ref.FindBoneIndex(TEXT("Root"));
    if (RootIndex!=INDEX_NONE)
    {
        ReferenceRoot=Ref.GetRefBonePose()[RootIndex];
        for(int32 Parent=Ref.GetParentIndex(RootIndex);Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))
            ReferenceRoot*=Ref.GetRefBonePose()[Parent];
    }
    InitializeNeedleOutlets();
}

void ARootCrownRigPreview::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);ApplyRig();
}

void ARootCrownRigPreview::BeginPlay()
{
    Home=GetActorLocation();
    if(HasAuthority()){MaxHealth*=float(MonsterCoreStats::HealthMultiplier());Health=MaxHealth;}
    Super::BeginPlay();ApplyRig();
    HitDetection->InitializeSurface();
    GetCharacterMovement()->MaxWalkSpeed=WalkSpeed;
    GetCharacterMovement()->RotationRate=FRotator(0,TurnSpeed,0);
    if (GetNetMode()!=NM_DedicatedServer && SlashMaterial)
        TensionMaterial=GetMesh()->CreateDynamicMaterialInstance(0,SlashMaterial);
    OnRep_Slash();
    if(Dead())OnRep_Reaction();
}

void ARootCrownRigPreview::RefreshPoseTick()
{
    // The server must update anatomical queries even when no local camera sees this boss.
    const bool Always=(!Dead()&&HasAuthority())||IsAttacking()||Reaction.Phase!=ERootCrownReaction::None;
    GetMesh()->VisibilityBasedAnimTickOption=Always?EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones:
        EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
    GetMesh()->bEnableUpdateRateOptimizations=false;
}
