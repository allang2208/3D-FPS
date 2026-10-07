#include "ColdSteelKeyPickup.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/Pawn.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    // 引擎基本体：100 cm 立方 + 自带灰材质，按缩放拼小钥匙；不依赖任何项目资产。
    const TCHAR* CubeMeshPath = TEXT("/Engine/BasicShapes/Cube.Cube");
    // 悬浮高度与旋转速度：让钥匙在环境里一眼可辨。
    constexpr float HoverZ = 60.f;
    constexpr float SpinDegreesPerSecond = 60.f;
}

AColdSteelKeyPickup::AColdSteelKeyPickup()
{
    PrimaryActorTick.bCanEverTick = true;
    bReplicates = true;
    SetReplicateMovement(true);

    KeyRoot = CreateDefaultSubobject<USceneComponent>(TEXT("KeyRoot"));
    SetRootComponent(KeyRoot);

    // 钥匙本体约 26 cm 长、躺在水平面（Y 长轴），悬浮在 HoverZ 由 KeyRoot 缓慢自转。
    // 基本体立方 100 cm，缩放 = 期望半尺寸 × 2 / 100。
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(CubeMeshPath);
    const struct FPart { FName Name; FVector Extent; FVector Location; } Parts[] = {
        {TEXT("KeyHead"),  FVector(3.f, 4.f, 2.f),    FVector(0.f, -10.f, HoverZ)},
        {TEXT("KeyShaft"), FVector(2.f, 16.f, 1.5f),  FVector(0.f,  -2.f, HoverZ)},
        {TEXT("KeyTooth1"),FVector(2.f, 2.f, 4.f),   FVector(0.f,   5.f, HoverZ - 1.5f)},
        {TEXT("KeyTooth2"),FVector(2.f, 2.f, 5.f),   FVector(0.f,   8.f, HoverZ - 1.75f)},
    };
    for(const FPart& Part : Parts)
    {
        if(UStaticMeshComponent* Component = CreateDefaultSubobject<UStaticMeshComponent>(Part.Name))
        {
            Component->SetupAttachment(KeyRoot);
            Component->SetRelativeLocation(Part.Location);
            Component->SetRelativeScale3D(Part.Extent / 50.f);
            Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Component->SetCanEverAffectNavigation(false);
            Component->SetCastShadow(false);
            if(Cube.Succeeded())Component->SetStaticMesh(Cube.Object);
        }
    }

    // 触发范围略大于钥匙本体：走过去就捡到。
    ContactZone = CreateDefaultSubobject<UBoxComponent>(TEXT("ContactZone"));
    ContactZone->SetupAttachment(KeyRoot);
    ContactZone->SetRelativeLocation(FVector(0.f, 0.f, HoverZ));
    ContactZone->SetBoxExtent(FVector(50.f, 50.f, 60.f));
    ContactZone->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    ContactZone->SetCollisionObjectType(ECC_WorldDynamic);
    ContactZone->SetCollisionResponseToAllChannels(ECR_Ignore);
    ContactZone->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
    ContactZone->SetCanEverAffectNavigation(false);
}

void AColdSteelKeyPickup::BeginPlay()
{
    Super::BeginPlay();
    // 钥匙登记只在服务器判定；拾取后整体消失（复制 Destroy 到远端）。
    if(HasAuthority())
        ContactZone->OnComponentBeginOverlap.AddDynamic(this, &AColdSteelKeyPickup::HandleContact);
}

void AColdSteelKeyPickup::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    // 表现层自转：两端各自转，不走复制（旋转量小、视觉对齐要求低）。
    KeyRoot->AddLocalRotation(FQuat(FRotator(0.f, SpinDegreesPerSecond * DeltaSeconds, 0.f)));
}

void AColdSteelKeyPickup::HandleContact(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
    UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
    if(bTaken || !HasAuthority())return;
    auto* Player = Cast<AFPSGAMECharacter>(OtherActor);
    if(!Player || !Player->IsPlayerControlled())return;
    Player->GrantDoorKey(KeyId);
    bTaken = true;
    UE_LOG(LogTemp, Display, TEXT("ColdSteelKeyPickup %s 被玩家拾取，登记钥匙=%s"), *GetName(), *KeyId.ToString());
    Destroy();
}
