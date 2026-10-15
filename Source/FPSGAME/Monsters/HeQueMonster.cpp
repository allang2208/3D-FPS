#include "HeQueMonster.h"
#include "HeQueAnimInstance.h"
#include "HeQueMovementComponent.h"
#include "MonsterIdleBreathingMeshComponent.h"
#include "MonsterCombatComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "MonsterAIController.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Multiplayer/FPSStatusReplicationComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"
#include "UObject/ConstructorHelpers.h"

AHeQueMonster::AHeQueMonster(const FObjectInitializer& Initializer)
    :Super(Initializer.SetDefaultSubobjectClass<UHeQueMovementComponent>(CharacterMovementComponentName)
        .SetDefaultSubobjectClass<UMonsterIdleBreathingMeshComponent>(MeshComponentName))
{
    PrimaryActorTick.bCanEverTick=true;bReplicates=true;SetReplicateMovement(true);
    SetNetUpdateFrequency(30.f);SetMinNetUpdateFrequency(15.f);
    Combat=CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    CorpseRagdoll=CreateDefaultSubobject<UMonsterCorpseRagdollComponent>(TEXT("CorpseRagdoll"));
    PressureMembrane=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RiftMembrane"));
    PressureMembrane->SetupAttachment(GetMesh());
    PressureIntake=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RiftIntake"));PressureIntake->SetupAttachment(GetMesh());
    for(int32 I=0;I<2;++I)
    {
        auto* Wave=CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("RiftWave%d"),I));
        Wave->SetupAttachment(GetMesh());PressureWaves.Add(Wave);
        auto AddPart=[this,I](const TCHAR* Name,TArray<TObjectPtr<UStaticMeshComponent>>& Parts)
        {
            auto* Part=CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("%s%d"),Name,I));
            Part->SetupAttachment(GetMesh());Parts.Add(Part);
        };
        AddPart(TEXT("RiftMuzzle"),PressureMuzzles);AddPart(TEXT("RiftTrail"),PressureTrails);
        AddPart(TEXT("RiftImpact"),PressureImpacts);AddPart(TEXT("RiftDust"),PressureDust);
        auto* Voice=CreateDefaultSubobject<UAudioComponent>(*FString::Printf(TEXT("RiftImpactVoice%d"),I));
        Voice->SetupAttachment(GetRootComponent());Voice->bAutoActivate=false;RiftImpactVoices.Add(Voice);
    }
    TArray<UStaticMeshComponent*> PressureParts={PressureMembrane,PressureIntake};
    for(const auto& Part:PressureWaves)PressureParts.Add(Part.Get());
    for(const auto* Parts:{&PressureMuzzles,&PressureTrails,&PressureImpacts,&PressureDust})
        for(const auto& Part:*Parts)PressureParts.Add(Part.Get());
    for(auto* Part:PressureParts)
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);
        Part->SetCanEverAffectNavigation(false);Part->bReceivesDecals=false;Part->SetVisibility(false);
    }
    RiftVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("RiftVoice"));RiftVoice->SetupAttachment(GetMesh(),TEXT("Bone_000"));
    RiftVoice->bAutoActivate=false;
    ClampVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("ClampVoice"));ClampVoice->SetupAttachment(GetMesh(),TEXT("Bone_000"));
    ClampVoice->bAutoActivate=false;
    SweepVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("KickVoice"));SweepVoice->SetupAttachment(GetMesh(),TEXT("Bone_013"));
    SweepVoice->bAutoActivate=false;
    PsychicVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("PsychicVoice"));PsychicVoice->SetupAttachment(GetMesh(),TEXT("Bone_000"));
    PsychicVoice->bAutoActivate=false;
    JumpVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("JumpSlamVoice"));JumpVoice->SetupAttachment(GetMesh());JumpVoice->bAutoActivate=false;
    JumpImpactVoice=CreateDefaultSubobject<UAudioComponent>(TEXT("JumpImpactVoice"));JumpImpactVoice->SetupAttachment(GetRootComponent());JumpImpactVoice->bAutoActivate=false;
    JumpWave=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("JumpGroundWave"));JumpWave->SetupAttachment(GetRootComponent());
    JumpImpact=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("JumpGroundImpact"));JumpImpact->SetupAttachment(GetRootComponent());
    for(auto* Part:{JumpWave.Get(),JumpImpact.Get()})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetGenerateOverlapEvents(false);
        Part->SetCastShadow(false);Part->SetCanEverAffectNavigation(false);Part->bReceivesDecals=false;
        Part->SetBoundsScale(2.f);Part->SetVisibility(false);
    }
    for(int32 I=0;I<3;++I)
    {
        auto* Wave=CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("PsychicWave%d"),I));
        Wave->SetupAttachment(GetRootComponent());Wave->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Wave->SetCastShadow(false);Wave->SetCanEverAffectNavigation(false);Wave->SetVisibility(false);
        Wave->bReceivesDecals=false;PsychicWaves.Add(Wave);
    }
    CreateDefaultSubobject<UCombatStatusFormula>(TEXT("CombatStatus"));
    CreateDefaultSubobject<UFPSStatusReplicationComponent>(TEXT("NetworkCombatStatus"));
    GetCapsuleComponent()->InitCapsuleSize(225.f,225.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
    GetMesh()->SetCanEverAffectNavigation(false);
    GetMesh()->SetCollisionObjectType(ECC_Pawn);GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
    static ConstructorHelpers::FClassFinder<AMonsterAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    AIControllerClass=AI.Succeeded()?AI.Class.Get():AMonsterAIController::StaticClass();
    AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;bUseControllerRotationYaw=false;BaseEyeHeight=50.f;
    auto* Move=GetCharacterMovement();Move->MaxWalkSpeed=WalkSpeed;Move->MaxAcceleration=140.f;
    Move->BrakingDecelerationWalking=180.f;Move->RotationRate=FRotator(0,TurnSpeed,0);
    Move->bOrientRotationToMovement=true;Move->bCanWalkOffLedges=false;
    Tags.Add(TEXT("Enemy"));Tags.Add(TEXT("HeQue"));
    CastChecked<UMonsterCharacterMovementComponent>(Move)->ConfigureWideBodyStairs(225.f,450.f);
}
void AHeQueMonster::ApplyRig()
{
    CastChecked<UMonsterCharacterMovementComponent>(GetCharacterMovement())->ConfigureWideBodyStairs(225.f,450.f);
    if(!VisualMesh)return;
    auto* BodyMesh=GetMesh();BodyMesh->SetSkeletalMeshAsset(VisualMesh);
    const auto B=VisualMesh->GetBounds();const double Scale=450./FMath::Max(1.,double(B.BoxExtent.Z)*2.);
    BodyMesh->SetRelativeScale3D(FVector(Scale));BodyMesh->SetRelativeRotation(FRotator(0,-90,0));
    BodyMesh->SetRelativeLocation(FVector(0,0,-225.-(B.Origin.Z-B.BoxExtent.Z)*Scale));
    BodyMesh->SetAnimInstanceClass(UHeQueAnimInstance::StaticClass());
    if(HitSurfacePhysics)BodyMesh->SetPhysicsAsset(HitSurfacePhysics);
    BodyMesh->SetCollisionObjectType(ECC_Pawn);BodyMesh->SetCollisionResponseToAllChannels(ECR_Ignore);
    BodyMesh->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    BodyMesh->SetCollisionEnabled(Dead()?ECollisionEnabled::NoCollision:ECollisionEnabled::QueryOnly);
}
void AHeQueMonster::OnConstruction(const FTransform& Transform){Super::OnConstruction(Transform);ApplyRig();}
void AHeQueMonster::BeginPlay()
{
    Home=GetActorLocation();if(HasAuthority()){MaxHealth*=float(MonsterCoreStats::HealthMultiplier());Health=MaxHealth;}
    Super::BeginPlay();ApplyRig();GetCharacterMovement()->MaxWalkSpeed=WalkSpeed;RefreshPoseTick();
    GetCharacterMovement()->MaxAcceleration=140.f;GetCharacterMovement()->BrakingDecelerationWalking=180.f;
    if(Dead())OnRep_Reaction();
}
void AHeQueMonster::SetLocomotion(bool Moving,bool Returning)
{
    if(!Busy())GetCharacterMovement()->MaxWalkSpeed=Returning?ReturnSpeed:WalkSpeed;
}
double AHeQueMonster::ActionClock() const
{
    if(const auto* GS=GetWorld()->GetGameState())return GS->GetServerWorldTimeSeconds();
    return GetWorld()->GetTimeSeconds();
}
void AHeQueMonster::RefreshPoseTick()
{
    const bool Always=(!Dead()&&HasAuthority())||Reaction.Phase!=EHeQueReaction::None||Sweep.Active||Rift.Active||Clamp.Active||Psychic.Active||IsJumpSlamming();
    GetMesh()->VisibilityBasedAnimTickOption=Always?EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones:EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
}
void AHeQueMonster::Tick(float Dt){Super::Tick(Dt);TickReaction(Dt);TickSweep();TickClamp();TickRift();TickPsychic();TickJumpSlam();}
void AHeQueMonster::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AHeQueMonster,Health);DOREPLIFETIME(AHeQueMonster,MaxHealth);DOREPLIFETIME(AHeQueMonster,Reaction);
    DOREPLIFETIME(AHeQueMonster,Sweep);
    DOREPLIFETIME(AHeQueMonster,Rift);
    DOREPLIFETIME(AHeQueMonster,Clamp);
    DOREPLIFETIME(AHeQueMonster,Psychic);
    DOREPLIFETIME(AHeQueMonster,JumpSlam);
}
