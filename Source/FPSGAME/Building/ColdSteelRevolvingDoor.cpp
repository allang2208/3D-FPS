#include "ColdSteelRevolvingDoor.h"
#include "Components/BoxComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Net/UnrealNetwork.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    const TCHAR* RevolvingLeafMesh=TEXT("/Game/Props/SingleDoor20260918/SM_SingleDoorLeaf_D40.SM_SingleDoorLeaf_D40");
    const TCHAR* CubeMeshPath=TEXT("/Engine/BasicShapes/Cube.Cube");
    constexpr float ContactZoneHalf=70.f;   // 门口触发盒半宽：比叶扇外缘略大，走近即转
    const TCHAR* RevolvingSoundPath=TEXT("/Game/Audio/Interactions/DoorAudio20261004/S_Door_Open.S_Door_Open");
}

AColdSteelRevolvingDoor::AColdSteelRevolvingDoor()
{
    PrimaryActorTick.bCanEverTick=true;
    bReplicates=true;SetReplicateMovement(true);
    DoorRoot=CreateDefaultSubobject<USceneComponent>(TEXT("DoorRoot"));
    SetRootComponent(DoorRoot);

    Pivot=CreateDefaultSubobject<USceneComponent>(TEXT("DoorPivot"));
    Pivot->SetupAttachment(DoorRoot);

    CenterPost=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("CenterPost"));
    CenterPost->SetupAttachment(DoorRoot);
    CenterPost->SetMobility(EComponentMobility::Movable);
    CenterPost->SetCollisionProfileName(TEXT("BlockAll"));
    CenterPost->SetCanEverAffectNavigation(false);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> LeafAsset(RevolvingLeafMesh);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(CubeMeshPath);
    for(int32 Index=0;Index<3;++Index)
    {
        UStaticMeshComponent* Leaf=CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("Leaf%d"),Index));
        Leaf->SetupAttachment(Pivot);
        Leaf->SetMobility(EComponentMobility::Movable);
        Leaf->SetCollisionProfileName(TEXT("BlockAll"));
        Leaf->SetCanEverAffectNavigation(false);
        if(LeafAsset.Succeeded())Leaf->SetStaticMesh(LeafAsset.Object);
        Leaves[Index]=Leaf;
    }
    if(Cube.Succeeded())
    {
        CenterPost->SetStaticMesh(Cube.Object);
        CenterPost->SetRelativeScale3D(FVector(0.24f,0.24f,2.4f));
        CenterPost->SetRelativeLocation(FVector(0.f,0.f,120.f));
    }
    static ConstructorHelpers::FObjectFinder<USoundBase> RotateAsset(RevolvingSoundPath);
    if(RotateAsset.Succeeded())RotateSound=RotateAsset.Object;

    ContactZone=CreateDefaultSubobject<UBoxComponent>(TEXT("ContactZone"));
    ContactZone->SetupAttachment(DoorRoot);
    ContactZone->SetRelativeLocation(FVector(0.f,0.f,120.f));
    ContactZone->SetBoxExtent(FVector(ContactZoneHalf,ContactZoneHalf,120.f));
    ContactZone->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    ContactZone->SetCollisionObjectType(ECC_WorldDynamic);
    ContactZone->SetCollisionResponseToAllChannels(ECR_Ignore);
    ContactZone->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
    ContactZone->SetCanEverAffectNavigation(false);
}

void AColdSteelRevolvingDoor::BeginPlay()
{
    Super::BeginPlay();
    if(HasAuthority())NetScale=GetActorScale3D();
    else OnRep_Setup();
    AlignGeometry();
    if(!HasAuthority())OnRep_Swing();
    if(HasAuthority())
        ContactZone->OnComponentBeginOverlap.AddDynamic(this, &AColdSteelRevolvingDoor::HandleContact);
}

void AColdSteelRevolvingDoor::AlignGeometry()
{
    if(const UStaticMesh* LeafMesh=Leaves[0]?Leaves[0]->GetStaticMesh():nullptr)
    {
        // 每扇缩为洞口半宽（Y 0.5），内缘贴中柱、外缘向外：包盒中心落在半径 r=半扇宽 处。
        const FBoxSphereBounds Bounds=LeafMesh->GetBounds();
        LeafHalfCm=Bounds.BoxExtent*FVector(1.f,0.5f,1.f);
        LeafOriginCm=Bounds.Origin*FVector(1.f,0.5f,1.f);
        LeafRadiusCm=LeafHalfCm.Y;
        for(int32 Index=0;Index<3;++Index)
        {
            if(UStaticMeshComponent* Leaf=Leaves[Index])
            {
                Leaf->SetRelativeScale3D(FVector(1.f,0.5f,1.f));
                const float Yaw=Index*120.f;
                const FQuat YawQuat(FRotator(0.f,Yaw,0.f));
                // 相对定位口径：包盒中心落在 Radial（半径方向）、底面贴地。
                const FVector Radial=YawQuat.RotateVector(FVector(0.f,LeafRadiusCm,0.f));
                Leaf->SetRelativeRotation(FRotator(0.f,Yaw,0.f));
                Leaf->SetRelativeLocation(Radial+FVector(0.f,0.f,LeafHalfCm.Z)-YawQuat.RotateVector(LeafOriginCm));
            }
        }
    }
}

float AColdSteelRevolvingDoor::RotateDirectionFor(const APawn* InstigatorPawn) const
{
    // 玩家在哪一侧就朝哪一侧转（把面前的扇推走）；拿不到玩家位置时固定正向。
    if(!InstigatorPawn)return 1.f;
    const FVector Local=GetActorTransform().InverseTransformPosition(InstigatorPawn->GetActorLocation());
    if(FMath::Abs(Local.X)<1.f)return 1.f;
    return Local.X>0.f?1.f:-1.f;
}

void AColdSteelRevolvingDoor::ToggleDoorFrom(const APawn* InstigatorPawn)
{
    if(!HasAuthority())return;
    // 停稳才接受下一步旋转；转动中重复请求忽略（触发盒与 E 双入口共用）。
    if(!FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.5f))return;
    NetSwing.From=CurrentAngle;
    TargetAngle+=StepDegrees*RotateDirectionFor(InstigatorPawn);
    NetSwing.To=TargetAngle;
    NetSwing.Speed=StepDegrees/FMath::Max(.1f,StepSeconds);
    NetSwing.StartedAt=FColdSteelDoorNetState::Now(GetWorld());
    NetSwing.bOpen=false;
    NetSwing.Direction=TargetAngle>CurrentAngle?1.f:-1.f;
    ForceNetUpdate();
    MulticastRotateSound();
    UE_LOG(LogTemp,Display,TEXT("ColdSteelRevolvingDoor %s 旋转至 %.0f°"),*GetName(),TargetAngle);
}

void AColdSteelRevolvingDoor::MulticastRotateSound_Implementation()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    if(RotateSound)UGameplayStatics::PlaySoundAtLocation(this,RotateSound,GetActorLocation());
}

void AColdSteelRevolvingDoor::HandleContact(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
    UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
    if(!HasAuthority())return;
    auto* Pawn=Cast<APawn>(OtherActor);
    if(!Pawn||!Pawn->IsPlayerControlled())return;
    ToggleDoorFrom(Pawn);
}

void AColdSteelRevolvingDoor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!HasAuthority())CurrentAngle=NetSwing.Angle(GetWorld());
    ApplyAngle(DeltaSeconds);
    UpdateLeafPawnCollision();
}

void AColdSteelRevolvingDoor::ApplyAngle(float DeltaSeconds)
{
    if(HasAuthority())CurrentAngle=FMath::FInterpConstantTo(CurrentAngle,TargetAngle,DeltaSeconds,
        StepDegrees/FMath::Max(.1f,StepSeconds));
    Pivot->SetRelativeRotation(FRotator(0.f,CurrentAngle,0.f));
}

bool AColdSteelRevolvingDoor::LeavesOverlapPawn() const
{
    UWorld* World=GetWorld();
    if(!World||LeafHalfCm.IsNearlyZero())return false;
    FCollisionObjectQueryParams ObjectParams;
    ObjectParams.AddObjectTypesToQuery(ECC_Pawn);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(ColdSteelRevolvingDoorPawn),false,this);
    Params.AddIgnoredActor(this);
    const FVector Extent=FVector(FMath::Max(1.f,LeafHalfCm.X-2.f),FMath::Max(1.f,LeafHalfCm.Y-2.f),
        FMath::Max(1.f,LeafHalfCm.Z-4.f));
    const FCollisionShape Shape=FCollisionShape::MakeBox(Extent);
    for(const UStaticMeshComponent* Leaf:Leaves)
    {
        if(!Leaf)continue;
        const FTransform Transform=Leaf->GetComponentTransform();
        if(World->OverlapAnyTestByObjectType(Transform.TransformPosition(LeafOriginCm),Transform.GetRotation(),
            ObjectParams,Shape,Params))return true;
    }
    return false;
}

void AColdSteelRevolvingDoor::UpdateLeafPawnCollision()
{
    // 与门族同一口径：停稳才挡 Pawn，转动中对玩家放行（可以跟着门走进去）。
    const bool bSettled=FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.5f);
    for(UStaticMeshComponent* Leaf:Leaves)
    {
        if(!Leaf)continue;
        const bool bBlockingNow=Leaf->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block;
        bool bWants=bSettled;
        if(bWants&&!bBlockingNow&&LeavesOverlapPawn())bWants=false;
        if(bWants!=bBlockingNow)Leaf->SetCollisionResponseToChannel(ECC_Pawn,bWants?ECR_Block:ECR_Ignore);
    }
}

void AColdSteelRevolvingDoor::Configure(UMaterialInterface* Surface)
{
    if(!Surface)return;
    if(HasAuthority()){NetSurface=Surface;ForceNetUpdate();}
    for(UStaticMeshComponent* Part:{CenterPost,Leaves[0],Leaves[1],Leaves[2]})
        if(Part)for(int32 Index=0;Index<FMath::Max(1,Part->GetNumMaterials());++Index)Part->SetMaterial(Index,Surface);
}

void AColdSteelRevolvingDoor::OnRep_Swing()
{
    // 客户端按服务器时间重放转动：Tick 每帧读 NetSwing.Angle。
}

void AColdSteelRevolvingDoor::OnRep_Setup()
{
    if(NetSurface)Configure(NetSurface);
    if(!NetScale.IsNearlyZero()&&!GetActorScale3D().Equals(NetScale))SetActorScale3D(NetScale);
}

void AColdSteelRevolvingDoor::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AColdSteelRevolvingDoor,NetSwing);
    DOREPLIFETIME(AColdSteelRevolvingDoor,NetSurface);
    DOREPLIFETIME(AColdSteelRevolvingDoor,NetScale);
}
