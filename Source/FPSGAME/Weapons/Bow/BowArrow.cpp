#include "BowArrow.h"
#include "../../FPSGAMECharacter.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Monsters/MonsterDamageAlert.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../UI/ColdSteelWorldInteraction.h"
#include "Components/CapsuleComponent.h"
#include "Components/SphereComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "../../Monsters/FPSCombatHealthComponent.h"

ABowArrow::ABowArrow()
{
    PrimaryActorTick.bCanEverTick = true;
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);
    Shaft = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Shaft"));
    Shaft->SetupAttachment(Root);
    Head = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Head"));
    Head->SetupAttachment(Root);
    RecoveryShape = CreateDefaultSubobject<UCapsuleComponent>(TEXT("RecoveryShape"));
    RecoveryShape->SetupAttachment(Root);
    RecoveryShape->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RecoveryShape->SetCollisionResponseToAllChannels(ECR_Ignore);
    RecoveryShape->SetCollisionResponseToChannel(ECC_Visibility, ECR_Overlap);
    RecoveryShape->SetGenerateOverlapEvents(false);
    RecoveryShape->SetCanEverAffectNavigation(false);
    AutoRecovery=CreateDefaultSubobject<USphereComponent>(TEXT("AutoRecovery"));
    AutoRecovery->SetupAttachment(Root);
    AutoRecovery->InitSphereRadius(125.f);
    AutoRecovery->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    AutoRecovery->SetCollisionObjectType(ECC_WorldDynamic);
    AutoRecovery->SetCollisionResponseToAllChannels(ECR_Ignore);
    AutoRecovery->SetCollisionResponseToChannel(ECC_Pawn,ECR_Overlap);
    AutoRecovery->SetGenerateOverlapEvents(true);
    AutoRecovery->SetCanEverAffectNavigation(false);
    AutoRecovery->OnComponentBeginOverlap.AddDynamic(this,&ABowArrow::OnRecoveryOverlap);
    AutoRecovery->OnComponentEndOverlap.AddDynamic(this,&ABowArrow::OnRecoveryEndOverlap);
    for (UStaticMeshComponent* Component : { Shaft.Get(), Head.Get() })
    {
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetCanEverAffectNavigation(false);
        Component->SetCastShadow(false);
        Component->SetNotifyRigidBodyCollision(false);
    }
    // 箭体不做世界碰撞：命中由本 Actor 的扫掠负责，否则生成时会戳到自己手上的弓。
    SetActorEnableCollision(false);
}

void ABowArrow::Configure(float InDamage, float InSpeed, float InGravityCM, float InRangeCM,
                          const FColdSteelSkillShot& InShot, UStaticMesh* InShaftMesh, UStaticMesh* InHeadMesh,
                          float InRadiusCM, float InLengthCM, const FString& InAmmoId,
                          bool bInRecoverable, float InRecoverySeconds)
{
    Damage = FMath::Max(1.f, InDamage);
    Speed = FMath::Max(600.f, InSpeed);
    GravityCM = FMath::Max(0.f, InGravityCM);
    MaxDistanceCM = FMath::Max(400.f, InRangeCM);
    Shot = InShot;
    AmmoId = InAmmoId;
    bRecoverable = bInRecoverable;
    RecoverySeconds = FMath::Clamp(InRecoverySeconds, 8.f, 300.f);
    if (const auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        RecoveryCaption = FString::Printf(TEXT("拾回 %s ×1"), *Profile->AmmoLabel(AmmoId));
    const float Radius = FMath::Clamp(InRadiusCM, .05f, 6.f);
    const float Length = FMath::Clamp(InLengthCM, 20.f, 200.f);
    RecoveryShape->SetRelativeRotation(FRotator(90.f, 0.f, 0.f));
    RecoveryShape->SetRelativeLocation(FVector(-Length * .5f, 0.f, 0.f));
    AutoRecovery->SetRelativeLocation(FVector(-Length * .5f, 0.f, 0.f));
    RecoveryShape->SetCapsuleSize(FMath::Max(2.f, Radius), Length * .5f);
    CollisionRadiusCM = FMath::Clamp(Radius * 1.2f, .25f, 2.f);
    Velocity = GetActorForwardVector() * Speed;

    // 占位箭：引擎圆柱做箭杆、引擎圆锥做箭头；两者局部 +Z 沿箭身，转 90° 俯仰对到 Actor +X。
    auto* ShaftMesh = InShaftMesh ? InShaftMesh : LoadObject<UStaticMesh>(nullptr,
        TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    auto* HeadMesh = InHeadMesh ? InHeadMesh : LoadObject<UStaticMesh>(nullptr,
        TEXT("/Engine/BasicShapes/Cone.Cone"));
    const float HeadLength = FMath::Min(9.f, Length * .12f);
    Shaft->SetStaticMesh(ShaftMesh);
    if (InShaftMesh)
    {
        // Authored arrow includes shaft, nock, fletching and head. Actor origin
        // is always its tip, which is also the collision/launch contact point.
        const auto Bounds = InShaftMesh->GetBounds();
        const bool bAlongX = Bounds.BoxExtent.X > Bounds.BoxExtent.Z;
        const float Authored = 2.f * (bAlongX ? Bounds.BoxExtent.X : Bounds.BoxExtent.Z);
        const float LongScale = Length / FMath::Max(.01f, Authored);
        const FVector Scale = bAlongX ? FVector(LongScale, 1.f, 1.f) : FVector(1.f, 1.f, LongScale);
        const FQuat Rotation = FQuat::FindBetweenNormals(bAlongX ? FVector::XAxisVector : FVector::ZAxisVector, FVector::XAxisVector);
        Shaft->SetRelativeRotation(Rotation);
        Shaft->SetRelativeScale3D(Scale);
        const FVector Axis = bAlongX ? FVector::XAxisVector : FVector::ZAxisVector;
        const FVector Centre = Axis * FVector::DotProduct(Bounds.Origin, Axis);
        Shaft->SetRelativeLocation(FVector(-Length * .5f, 0.f, 0.f) - Rotation.RotateVector(Centre * Scale));
        Head->SetVisibility(false);
        return;
    }
    Shaft->SetRelativeRotation(FRotator(90.f, 0.f, 0.f));
    Shaft->SetRelativeLocation(FVector(-(Length + HeadLength) * .5f, 0.f, 0.f));
    Shaft->SetRelativeScale3D(FVector(Radius / 50.f, Radius / 50.f, (Length - HeadLength) / 100.f));
    Head->SetStaticMesh(HeadMesh);
    Head->SetRelativeRotation(FRotator(90.f, 0.f, 0.f));
    Head->SetRelativeLocation(FVector(-HeadLength * .5f, 0.f, 0.f));
    Head->SetRelativeScale3D(FVector(Radius * 2.1f / 50.f, Radius * 2.1f / 50.f, HeadLength / 100.f));
}

void ABowArrow::Tick(float Delta)
{
    Super::Tick(Delta);
    Delta = FMath::Max(0.f, Delta);
    Age += Delta;
    if (bStuck) return;
    if (Delta <= 0.f || Velocity.IsNearlyZero()) return;
    float Remaining = FMath::Min(Delta, 8.f);
    FVector Previous = GetActorLocation();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BowArrow), true, GetInstigator());
    Query.AddIgnoredActor(this);
    FHitResult Hit;
    while (Remaining > KINDA_SMALL_NUMBER)
    {
        const float Dt = FMath::Min3(Remaining, 1.f / 120.f, StepCM / FMath::Max(1.f, float(Velocity.Size())));
        const FVector Acceleration(0.f, 0.f, -GravityCM);
        FVector Displacement = Velocity * Dt + Acceleration * (.5f * Dt * Dt);
        const float Available = FMath::Max(0.f, MaxDistanceCM - TravelledCM);
        if (Displacement.Size() > Available) Displacement = Displacement.GetSafeNormal() * Available;
        const FVector Next = Previous + Displacement;
        Velocity += Acceleration * Dt;
        SetActorRotation(Velocity.Rotation());
        const bool Blocked = GetWorld()->SweepSingleByChannel(Hit, Previous, Next, FQuat::Identity,
            ECC_Visibility, FCollisionShape::MakeSphere(CollisionRadiusCM), Query);
        TravelledCM += Displacement.Size() * (Blocked ? Hit.Time : 1.f);
        if (Blocked)
        {
            ApplyHit(Hit);
            return;
        }
        Previous = Next;
        Remaining -= Dt;
        if (TravelledCM >= MaxDistanceCM)
        {
            Destroy();
            return;
        }
    }
    SetActorLocation(Previous);
    if (TravelledCM >= MaxDistanceCM || Age > 8.f) Destroy();
}

void ABowArrow::ResolveLaunchObstruction(const FVector& CameraOrigin)
{
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BowLaunch), true, GetInstigator());
    Query.AddIgnoredActor(this);
    if (GetWorld()->SweepSingleByChannel(Hit, CameraOrigin, GetActorLocation(), FQuat::Identity,
        ECC_Visibility, FCollisionShape::MakeSphere(CollisionRadiusCM), Query)) ApplyHit(Hit);
}

void ABowArrow::ApplyHit(const FHitResult& Hit)
{
    SetActorLocation(Hit.ImpactPoint + Velocity.GetSafeNormal() * 2.f);
    if (!bResolved)
    {
        bResolved = true;
        auto* Target = Hit.GetActor();
        auto* Pawn = Cast<APawn>(GetInstigator());
        const FVector Direction = Velocity.GetSafeNormal();
        if (Target)
        {
            FWeaponDamageResult Result;
            float Applied = 0.f;
            {
                // Bow release/impact never reports a hearing stimulus. Keep
                // the local audio, and resolve group alarms only after death.
                const MonsterDamageAlert::FScopedSilentShot SilentShot(Target);
                Applied = ColdSteelSkills::ApplyHit(Pawn, Hit, Damage, Direction, Shot, &Result);
            }
            if (auto* Character = Cast<AFPSGAMECharacter>(Pawn))
                Character->NotifyConfirmedWeaponHit(Target, Applied, &Result, true);
        }
    }
    FinishStuck(Hit);
}

void ABowArrow::FinishStuck(const FHitResult& Hit)
{
    bStuck = true;
    Velocity = FVector::ZeroVector;
    SetActorTickEnabled(false);
    SetActorEnableCollision(bRecoverable);
    RecoveryShape->SetCollisionEnabled(bRecoverable ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision);
    SetLifeSpan(bRecoverable ? RecoverySeconds : StickSeconds);
    // 命中生物：跟着骨骼走，避免目标移动后箭悬在空中。
    if (auto* Component = Hit.GetComponent())
    {
        if (Hit.BoneName.IsNone()) AttachToComponent(Component, FAttachmentTransformRules::KeepWorldTransform);
        else AttachToComponent(Component, FAttachmentTransformRules::KeepWorldTransform, Hit.BoneName);
    }
    // Only a landed, actually spent arrow becomes a pickup. The overlap timer
    // runs solely while a player is close, including a point-blank impact.
    if(bRecoverable)AutoRecovery->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
}

void ABowArrow::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(RecoveryTimer);
    Super::EndPlay(Reason);
}

void ABowArrow::OnRecoveryOverlap(UPrimitiveComponent* OverlappedComponent,AActor* OtherActor,
    UPrimitiveComponent* OtherComponent,int32 OtherBodyIndex,bool bFromSweep,const FHitResult& SweepResult)
{
    const auto* Pawn=Cast<APawn>(OtherActor);
    if(CanRecover()&&HasAuthority()&&GetNetMode()==NM_Standalone&&Pawn&&Pawn->IsPlayerControlled()&&
        !GetWorldTimerManager().IsTimerActive(RecoveryTimer))
        GetWorldTimerManager().SetTimer(RecoveryTimer,this,&ABowArrow::RecoverNearby,.2f,true,.15f);
}

void ABowArrow::OnRecoveryEndOverlap(UPrimitiveComponent* OverlappedComponent,AActor* OtherActor,
    UPrimitiveComponent* OtherComponent,int32 OtherBodyIndex)
{
    RecoverNearby();
}

void ABowArrow::RecoverNearby()
{
    if(!CanRecover()){GetWorldTimerManager().ClearTimer(RecoveryTimer);return;}
    TArray<AActor*> Nearby;AutoRecovery->GetOverlappingActors(Nearby,APawn::StaticClass());
    bool bPlayerNearby=false;
    for(auto* Actor:Nearby)
    {
        auto* Pawn=Cast<APawn>(Actor);
        if(!Pawn||!Pawn->IsPlayerControlled())continue;
        bPlayerNearby=true;
        if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())continue;
        // A nearby arrow behind a wall cannot be collected through that wall.
        FCollisionQueryParams Query(SCENE_QUERY_STAT(BowArrowRecovery),false,Pawn);Query.AddIgnoredActor(this);
        FHitResult Obstruction;const FVector End=AutoRecovery->GetComponentLocation();
        if(GetWorld()->LineTraceSingleByChannel(Obstruction,Pawn->GetActorLocation(),End,ECC_Visibility,Query)&&
            FVector::DistSquared(Obstruction.ImpactPoint,End)>FMath::Square(8.f))continue;
        RecoverIntoPouch(Pawn);
        // On a save failure keep the arrow and retry on the next entry, without
        // retrying disk writes or notices five times per second.
        GetWorldTimerManager().ClearTimer(RecoveryTimer);
        return;
    }
    if(!bPlayerNearby)GetWorldTimerManager().ClearTimer(RecoveryTimer);
}

FString ABowArrow::RecoveryPrompt() const
{
    return CanRecover() ? RecoveryCaption : FString();
}

bool ABowArrow::TryRecover(APawn* Pawn)
{
    return ColdSteelWorldInteraction::IsFocused(Pawn,this)&&RecoverIntoPouch(Pawn);
}

bool ABowArrow::RecoverIntoPouch(APawn* Pawn)
{
    if(!Pawn||!Pawn->IsPlayerControlled()||!CanRecover()||!HasAuthority()||GetNetMode()!=NM_Standalone)return false;
    auto* Profile = Pawn->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Profile) return false;
    // Persist the exact fired type before removing the world arrow. Failed
    // saves/capacity leave it available; virtual training arrows never enter here.
    bRecoverable = false;
    if (!Profile->GrantAmmo(AmmoId, 1))
    {
        bRecoverable = true;
        Profile->PostNotice(TEXT("箭支未拾回"), Profile->ResultMessage());
        return false;
    }
    SetActorEnableCollision(false);
    Destroy();
    return true;
}
