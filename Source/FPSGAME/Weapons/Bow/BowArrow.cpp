#include "BowArrow.h"
#include "../../FPSGAMECharacter.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

ABowArrow::ABowArrow()
{
    PrimaryActorTick.bCanEverTick = true;
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);
    Shaft = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Shaft"));
    Shaft->SetupAttachment(Root);
    Head = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Head"));
    Head->SetupAttachment(Root);
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
                          float InRadiusCM, float InLengthCM, const FString& InAmmoId)
{
    Damage = FMath::Max(1.f, InDamage);
    Speed = FMath::Max(600.f, InSpeed);
    GravityCM = FMath::Max(0.f, InGravityCM);
    MaxDistanceCM = FMath::Max(400.f, InRangeCM);
    Shot = InShot;
    AmmoId = InAmmoId;
    const float Radius = FMath::Clamp(InRadiusCM, .05f, 6.f);
    const float Length = FMath::Clamp(InLengthCM, 20.f, 200.f);
    Velocity = GetActorForwardVector() * Speed;

    // 占位箭：引擎圆柱做箭杆、引擎圆锥做箭头；两者局部 +Z 沿箭身，转 90° 俯仰对到 Actor +X。
    auto* ShaftMesh = InShaftMesh ? InShaftMesh : LoadObject<UStaticMesh>(nullptr,
        TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    auto* HeadMesh = InHeadMesh ? InHeadMesh : LoadObject<UStaticMesh>(nullptr,
        TEXT("/Engine/BasicShapes/Cone.Cone"));
    const float HeadLength = FMath::Min(9.f, Length * .12f);
    Shaft->SetStaticMesh(ShaftMesh);
    Shaft->SetRelativeRotation(FRotator(90.f, 0.f, 0.f));
    Shaft->SetRelativeLocation(FVector((Length - HeadLength) * .5f, 0.f, 0.f));
    Shaft->SetRelativeScale3D(FVector(Radius / 50.f, Radius / 50.f, (Length - HeadLength) / 100.f));
    Head->SetStaticMesh(HeadMesh);
    Head->SetRelativeRotation(FRotator(90.f, 0.f, 0.f));
    Head->SetRelativeLocation(FVector(Length - HeadLength * .5f, 0.f, 0.f));
    Head->SetRelativeScale3D(FVector(Radius * 2.1f / 50.f, Radius * 2.1f / 50.f, HeadLength / 100.f));
}

void ABowArrow::Tick(float Delta)
{
    Super::Tick(Delta);
    Delta = FMath::Clamp(Delta, 0.f, .1f);
    Age += Delta;
    if (bStuck)
    {
        StickRemaining -= Delta;
        if (StickRemaining <= 0.f)
        {
            Destroy();
            return;
        }
        // 插在目标上时随目标移动：把箭 attach 到命中组件由 FinishStuck 处理。
        return;
    }
    if (Delta <= 0.f || Velocity.IsNearlyZero()) return;
    Velocity.Z -= GravityCM * Delta;
    // 箭头始终指着速度方向：重力抛物线要能在屏幕上看出来。
    SetActorRotation(Velocity.GetSafeNormal().Rotation());

    float Remaining = Speed * Delta;
    const FVector Start = GetActorLocation();
    FVector Previous = Start;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BowArrow), false, GetInstigator());
    Query.AddIgnoredActor(this);
    FHitResult Hit;
    while (Remaining > KINDA_SMALL_NUMBER)
    {
        const float Step = FMath::Min(StepCM, Remaining);
        const FVector Next = Previous + (Velocity.GetSafeNormal() * Step);
        const bool Blocked = GetWorld()->SweepSingleByChannel(Hit, Previous, Next, FQuat::Identity,
            ECC_Visibility, FCollisionShape::MakeSphere(12.f), Query);
        TravelledCM += Step;
        if (Blocked)
        {
            ApplyHit(Hit);
            return;
        }
        Previous = Next;
        Remaining -= Step;
        if (TravelledCM >= MaxDistanceCM)
        {
            Destroy();
            return;
        }
    }
    SetActorLocation(Previous);
    if (TravelledCM >= MaxDistanceCM || Age > 8.f) Destroy();
}

void ABowArrow::ApplyHit(const FHitResult& Hit)
{
    SetActorLocation(Hit.Location - Hit.Normal * 2.f);
    if (!bResolved)
    {
        bResolved = true;
        auto* Target = Hit.GetActor();
        auto* Pawn = Cast<APawn>(GetInstigator());
        const FVector Direction = Velocity.GetSafeNormal();
        if (Target)
        {
            FWeaponDamageResult Result;
            const float Applied = ColdSteelSkills::ApplyHit(Pawn, Hit, Damage, Direction, Shot, &Result);
            if (auto* Character = Cast<AFPSGAMECharacter>(Pawn))
                Character->NotifyConfirmedWeaponHit(Target, Applied, &Result, true);
        }
    }
    FinishStuck(Hit);
}

void ABowArrow::FinishStuck(const FHitResult& Hit)
{
    bStuck = true;
    StickRemaining = StickSeconds;
    Velocity = FVector::ZeroVector;
    SetActorEnableCollision(false);
    SetLifeSpan(StickSeconds);
    // 命中生物：跟着骨骼走，避免目标移动后箭悬在空中。
    if (auto* Component = Hit.GetComponent())
    {
        if (Hit.BoneName.IsNone()) AttachToComponent(Component, FAttachmentTransformRules::KeepWorldTransform);
        else AttachToComponent(Component, FAttachmentTransformRules::KeepWorldTransform, Hit.BoneName);
    }
}
