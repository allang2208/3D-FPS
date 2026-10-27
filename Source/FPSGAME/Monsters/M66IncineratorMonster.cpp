#include "M66IncineratorMonster.h"
#include "MonsterCorpseMeshComponent.h"
#include "M66MovementComponent.h"
#include "M66AnimInstance.h"
#include "M66FurnaceVisualComponent.h"
#include "M66CorpseSyncComponent.h"
#include "M66AudioComponent.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "UObject/ConstructorHelpers.h"

AM66IncineratorMonster::AM66IncineratorMonster(const FObjectInitializer& Initializer)
    :Super(Initializer.SetDefaultSubobjectClass<UM66MovementComponent>(ACharacter::CharacterMovementComponentName)
        .SetDefaultSubobjectClass<UMonsterCorpseMeshComponent>(ACharacter::MeshComponentName))
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=true;
    bReplicates=true;SetReplicateMovement(true);SetCanBeDamaged(true);
    Combat=CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    Status=CreateDefaultSubobject<UCombatStatusFormula>(TEXT("CombatStatus"));
    BreathVisuals=CreateDefaultSubobject<UM66FurnaceVisualComponent>(TEXT("FurnacePresentation"));
    CorpseRagdoll=CreateDefaultSubobject<UMonsterCorpseRagdollComponent>(TEXT("CorpseRagdoll"));
    CorpseSync=CreateDefaultSubobject<UM66CorpseSyncComponent>(TEXT("CorpseSync"));
    BodyAudio=CreateDefaultSubobject<UM66AudioComponent>(TEXT("BodyAudio"));
    CorpseRagdoll->Rig=EMonsterCorpseRig::M66;CorpseRagdoll->MinimumPhysicsSeconds=5.f;
    GetCapsuleComponent()->InitCapsuleSize(100.f,190.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->bEnablePhysicsOnDedicatedServer=true;
    GetMesh()->SetCollisionObjectType(ECC_Pawn);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
    static ConstructorHelpers::FClassFinder<AMonsterAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    AIControllerClass=AI.Succeeded()?AI.Class.Get():AMonsterAIController::StaticClass();
    AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;
    bUseControllerRotationYaw=false;BaseEyeHeight=95.f;
    auto* Move=GetCharacterMovement();Move->MaxWalkSpeed=WalkSpeed;
    Move->MaxAcceleration=280.f;Move->BrakingDecelerationWalking=440.f;
    Move->bCanWalkOffLedges=false;Move->bOrientRotationToMovement=false;Move->bUseControllerDesiredRotation=false;
    CastChecked<UM66MovementComponent>(Move)->ConfigureWideBodyStairs(225.f,450.f);
    Tags.Add(TEXT("Enemy"));Tags.Add(TEXT("M66"));
}
void AM66IncineratorMonster::ApplyRig()
{
    bCleftFrameReady=false;
    CastChecked<UM66MovementComponent>(GetCharacterMovement())->ConfigureWideBodyStairs(225.f,450.f);
    GetCharacterMovement()->MaxWalkSpeed=WalkSpeed;
    GetCharacterMovement()->RotationRate=FRotator(0,TurnSpeed,0);
    if(!VisualMesh)return;
    auto* RigMesh=GetMesh();RigMesh->SetSkeletalMeshAsset(VisualMesh);
    if(ReactionPhysics)RigMesh->SetPhysicsAsset(ReactionPhysics);
    const auto Bounds=VisualMesh->GetBounds();const float Scale=380.f/FMath::Max(1.f,float(Bounds.BoxExtent.Z)*2.f);
    RigMesh->SetRelativeScale3D(FVector(Scale));RigMesh->SetRelativeRotation(FRotator::ZeroRotator);
    // V01 imported with ForceFrontXAxis. Centre support under the real ankles,
    // not the asymmetric arm/torso bounding box.
    const auto& Ref=VisualMesh->GetRefSkeleton();auto Bind=Ref.GetRefBonePose();
    for(int32 I=0;I<Bind.Num();++I)if(Ref.GetParentIndex(I)!=INDEX_NONE)Bind[I]*=Bind[Ref.GetParentIndex(I)];
    PrepareCleftWeakpoint(Bind);
    FVector Centre=FVector::ZeroVector;int32 Found=0;
    for(FName Name:{FName(TEXT("Bone_010")),FName(TEXT("Bone_015"))})
        if(const int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE){Centre+=Bind[I].GetLocation();++Found;}
    if(Found)Centre/=Found;
    RigMesh->SetRelativeLocation(FVector(-Centre.X*Scale,-Centre.Y*Scale,-190.f-(Bounds.Origin.Z-Bounds.BoxExtent.Z)*Scale));
    // Replicated actors can cache the blueprint component offset before this
    // runtime rig placement. Smoothing must use the same origin as authority.
    CacheInitialMeshOffset(RigMesh->GetRelativeLocation(),RigMesh->GetRelativeRotation());
    RigMesh->SetAnimInstanceClass(UM66AnimInstance::StaticClass());
    PrepareBackSmokeOutlets();
}
void AM66IncineratorMonster::OnConstruction(const FTransform& Transform)
{Super::OnConstruction(Transform);ApplyRig();}
void AM66IncineratorMonster::BeginPlay()
{
    Home=GetActorLocation();if(HasAuthority()){MaxHealth*=float(MonsterCoreStats::HealthMultiplier());Health=MaxHealth;}
    Super::BeginPlay();ApplyRig();OnRep_Reaction();StartBackSmoke();
}
void AM66IncineratorMonster::SetLocomotion(bool Moving,bool Returning)
{
    if(HasAuthority()&&!Busy())GetCharacterMovement()->MaxWalkSpeed=Returning?ReturnSpeed:WalkSpeed;
}
