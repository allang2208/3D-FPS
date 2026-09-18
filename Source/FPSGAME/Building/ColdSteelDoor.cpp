#include "ColdSteelDoor.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    // 门板仍是包里的 SM_Door（迁移在 Content/DoorSystem 下）；门框用本工程缩放进深后的资产
    // （SourceAssets/SingleDoor20260918/bake_single_door_frame_d40_20260918.py：24.8 → 40 cm，
    //  进深 40 ＝ 2 格体素，与双开门统一；其余两轴与包资产一致）。换外观只需改这两个默认值。
    // 名字按类区分：这三个门的 .cpp 会被 UBT 合并进同一个 unity 文件，
    // 匿名命名空间在合并块里是共享的，同名常量会报 C2374 重定义。
    const TCHAR* SingleDoorLeafMesh=TEXT("/Game/DoorSystem/Demo/StarterContent/Props/SM_Door.SM_Door");
    const TCHAR* SingleDoorFrameMesh=TEXT("/Game/Props/SingleDoor20260918/SM_SingleDoorFrame_D40.SM_SingleDoorFrame_D40");
    // 门框内沿到中线的距离（cm）：门板宽 90 → 铰链在 −45，门板中心在 +45。
    constexpr float LeafHalfWidth=45.f;
    constexpr float LeafCenterZ=100.f;
}

AColdSteelDoor::AColdSteelDoor()
{
    PrimaryActorTick.bCanEverTick=true;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("DoorRoot")));

    Frame=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("DoorFrame"));
    Frame->SetupAttachment(GetRootComponent());
    Frame->SetMobility(EComponentMobility::Movable);
    Frame->SetCollisionProfileName(TEXT("BlockAll"));
    Frame->SetCanEverAffectNavigation(false);

    Hinge=CreateDefaultSubobject<USceneComponent>(TEXT("DoorHinge"));
    Hinge->SetupAttachment(GetRootComponent());
    Hinge->SetRelativeLocation(FVector(0.f,-LeafHalfWidth,LeafCenterZ));

    Leaf=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("DoorLeaf"));
    Leaf->SetupAttachment(Hinge);
    Leaf->SetRelativeLocation(FVector(0.f,LeafHalfWidth,0.f));
    Leaf->SetMobility(EComponentMobility::Movable);
    Leaf->SetCollisionProfileName(TEXT("BlockAll"));
    Leaf->SetCanEverAffectNavigation(false);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> LeafAsset(SingleDoorLeafMesh);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> FrameAsset(SingleDoorFrameMesh);
    if(LeafAsset.Succeeded())Leaf->SetStaticMesh(LeafAsset.Object);
    if(FrameAsset.Succeeded())Frame->SetStaticMesh(FrameAsset.Object);
}

void AColdSteelDoor::BeginPlay()
{
    Super::BeginPlay();
    AlignGeometry();
    LogGeometryOnce();
}

void AColdSteelDoor::Configure(UMaterialInterface* Surface)
{
    if(!Surface)return;
    // 整个门统一材质：门板与门框的**全部**材质槽一起替换（含网格自带的小窗槽），
    // 这样和玩家用同种体素砌出来的墙一致。若要保留原网格的玻璃小窗，
    // 把下面两处循环改回只 SetMaterial(0, Surface) 即可。
    if(Leaf)for(int32 Index=0;Index<FMath::Max(1,Leaf->GetNumMaterials());++Index)Leaf->SetMaterial(Index,Surface);
    if(Frame)for(int32 Index=0;Index<FMath::Max(1,Frame->GetNumMaterials());++Index)Frame->SetMaterial(Index,Surface);
}

void AColdSteelDoor::AlignGeometry()
{
    // 关键：StarterContent 的 SM_Door / SM_DoorFrame pivot 在包围盒边缘（门框在底边、门板在角上）。
    // 按 pivot 摆放会把门框顶到半空、门板相对门框偏半个身位；这里一律以“包围盒”为准：
    //   门框：包围盒在 X/Y 居中、底面落在 z=0；
    //   门板：包围盒底面落在 z=0，宽度方向居中于门框洞口，铰链放在门板左边缘。
    HingeSign=bHingeOnPositiveY?1.f:-1.f;
    if(const UStaticMesh* FrameMesh=Frame->GetStaticMesh())
    {
        const FBoxSphereBounds Bounds=FrameMesh->GetBounds();
        Frame->SetRelativeLocation(FVector(-Bounds.Origin.X,-Bounds.Origin.Y,Bounds.BoxExtent.Z-Bounds.Origin.Z));
    }
    if(const UStaticMesh* LeafMesh=Leaf->GetStaticMesh())
    {
        const FBoxSphereBounds Bounds=LeafMesh->GetBounds();
        const float HalfWidth=Bounds.BoxExtent.Y;
        // 铰链装在 bHingeOnPositiveY 指定的一侧，门板整体仍居中于洞口（自由边在另一侧，也就是把手侧）。
        Hinge->SetRelativeLocation(FVector(0.f,HingeSign*HalfWidth,0.f));
        Leaf->SetRelativeLocation(FVector(-Bounds.Origin.X,
            -HingeSign*HalfWidth-Bounds.Origin.Y,Bounds.BoxExtent.Z-Bounds.Origin.Z));
    }
    CacheLeafBounds();
    Hinge->SetRelativeRotation(FRotator(0.f,CurrentAngle,0.f));
}

void AColdSteelDoor::CacheLeafBounds()
{
    if(const UStaticMesh* Mesh=Leaf?Leaf->GetStaticMesh():nullptr)
    {
        const FBoxSphereBounds Bounds=Mesh->GetBounds();
        LeafExtentCm=Bounds.BoxExtent;
        LeafOriginCm=Bounds.Origin;
    }
}

bool AColdSteelDoor::IsSwingBlocked(float DirectionSign) const
{
    UWorld* World=GetWorld();
    if(!World||!Leaf||LeafExtentCm.IsNearlyZero())return false;
    // 略缩小检测盒：门板底面本来就贴着地面、门框，贴合面不该算“被挡住”。
    const FCollisionShape Shape=FCollisionShape::MakeBox(LeafTestExtent());
    // 只查世界实体：玩家／怪物的碰撞体积不参与“门口被挡”的判定（2026-09-17 用户要求）。
    FCollisionObjectQueryParams ObjectParams;
    ObjectParams.AddObjectTypesToQuery(ECC_WorldStatic);
    ObjectParams.AddObjectTypesToQuery(ECC_WorldDynamic);
    ObjectParams.AddObjectTypesToQuery(ECC_Destructible);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(ColdSteelDoorSwing),false,this);
    Params.AddIgnoredActor(this);
    if(const AActor* Parent=GetAttachParentActor())Params.AddIgnoredActor(Parent);
    const FTransform ActorTransform=GetActorTransform();
    const FTransform LeafLocal=Leaf->GetRelativeTransform();
    const FTransform HingeLocal=Hinge->GetRelativeTransform();
    const float Full=FMath::Abs(OpenAngleDegrees)*(DirectionSign>=0.f?1.f:-1.f);
    const float Samples[]={0.25f,0.5f,0.75f,1.f};
    for(const float Fraction:Samples)
    {
        const FTransform HingeOpen(FQuat(FRotator(0.f,Full*Fraction,0.f)),HingeLocal.GetLocation());
        const FTransform LeafOpen=LeafLocal*HingeOpen*ActorTransform;
        const FVector Centre=LeafOpen.TransformPosition(LeafOriginCm);
        if(World->OverlapAnyTestByObjectType(Centre,LeafOpen.GetRotation(),ObjectParams,Shape,Params))
            return true;
    }
    return false;
}

FVector AColdSteelDoor::LeafTestExtent() const
{
    return FVector(FMath::Max(1.f,LeafExtentCm.X-2.f),FMath::Max(1.f,LeafExtentCm.Y-2.f),
        FMath::Max(1.f,LeafExtentCm.Z-4.f));
}

bool AColdSteelDoor::LeafOverlapsPawn() const
{
    UWorld* World=GetWorld();
    if(!World||!Leaf||LeafExtentCm.IsNearlyZero())return false;
    FCollisionObjectQueryParams ObjectParams;
    ObjectParams.AddObjectTypesToQuery(ECC_Pawn);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(ColdSteelDoorPawn),false,this);
    Params.AddIgnoredActor(this);
    if(const AActor* Parent=GetAttachParentActor())Params.AddIgnoredActor(Parent);
    const FTransform LeafNow=Leaf->GetComponentTransform();
    return World->OverlapAnyTestByObjectType(LeafNow.TransformPosition(LeafOriginCm),LeafNow.GetRotation(),
        ObjectParams,FCollisionShape::MakeBox(LeafTestExtent()),Params);
}

void AColdSteelDoor::UpdateLeafPawnCollision()
{
    if(!Leaf)return;
    // 关着且已经静止才挡玩家；开门/关门过程中与开着时对 Pawn 放行，门可以从玩家身上扫过去。
    const bool bSettled=FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.5f);
    bool bBlock=!bOpen&&bSettled;
    const bool bBlockingNow=Leaf->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block;
    // 玩家还站在门板里时先别恢复阻挡，等他离开，免得把人挤住或卡住。
    if(bBlock&&!bBlockingNow&&LeafOverlapsPawn())bBlock=false;
    if(bBlock!=bBlockingNow)
        Leaf->SetCollisionResponseToChannel(ECC_Pawn,bBlock?ECR_Block:ECR_Ignore);
}

void AColdSteelDoor::LogGeometryOnce()
{
    // 刚设置过相对位置，先刷新组件变换再读包围盒，避免读到上一帧的旧值。
    if(Frame)Frame->UpdateComponentToWorld();
    if(Leaf)Leaf->UpdateComponentToWorld();
    const FBox FrameBox=Frame?Frame->Bounds.GetBox():FBox(ForceInit);
    const FBox LeafBox=Leaf?Leaf->Bounds.GetBox():FBox(ForceInit);
    if(!FrameBox.IsValid||!LeafBox.IsValid)return;
    UE_LOG(LogTemp,Display,
        TEXT("ColdSteelDoor %s 门框z=[%.1f,%.1f] 门板z=[%.1f,%.1f] 门框y=[%.1f,%.1f] 门板y=[%.1f,%.1f] 对齐=%s"),
        *GetName(),FrameBox.Min.Z,FrameBox.Max.Z,LeafBox.Min.Z,LeafBox.Max.Z,
        FrameBox.Min.Y,FrameBox.Max.Y,LeafBox.Min.Y,LeafBox.Max.Y,
        (FMath::Abs(LeafBox.Min.Z-FrameBox.Min.Z)<2.f&&LeafBox.Min.Y>=FrameBox.Min.Y-2.f&&LeafBox.Max.Y<=FrameBox.Max.Y+2.f)
            ?TEXT("OK"):TEXT("CHECK"));
}

void AColdSteelDoor::ToggleDoor()
{
    if(bOpen)CloseDoor();else OpenDoor();
}

bool AColdSteelDoor::TryGetPlayerSideSign(float& OutSign) const
{
    const UWorld* World=GetWorld();
    const APlayerController* Controller=World?World->GetFirstPlayerController():nullptr;
    const APawn* Pawn=Controller?Controller->GetPawn():nullptr;
    if(!Pawn)return false;
    // 门的本地 X 就是门板法线：玩家在 +X 侧还是 −X 侧，决定门该往哪边开。
    const FVector Local=GetActorTransform().InverseTransformPosition(Pawn->GetActorLocation());
    if(FMath::Abs(Local.X)<1.f)return false;   // 玩家几乎贴在门平面上，方向说不清
    OutSign=Local.X>0.f?1.f:-1.f;
    return true;
}

float AColdSteelDoor::AngleSignForWorldSide(float WorldSideSign) const
{
    return WorldSideSign*HingeSign;
}

void AColdSteelDoor::OpenDoor()
{
    bOpen=true;
    // 默认方向由玩家决定：门朝玩家的**反侧**开（等于玩家把门推开），而不是固定方向。
    // 只有在拿不到玩家位置时才退回配置方向 OpenAngleDegrees 的符号。
    float Preferred=(OpenAngleDegrees>=0.f)?1.f:-1.f;
    float PlayerSide=0.f;
    const bool bHasPlayer=TryGetPlayerSideSign(PlayerSide);
    if(bHasPlayer)Preferred=AngleSignForWorldSide(-PlayerSide);
    // 首选那一侧被实体挡住就改从另一侧开（2026-09-17 第二轮要求）。
    OpenDirection=Preferred;
    bOpenFlipped=false;
    if(IsSwingBlocked(Preferred))
    {
        const float Other=-Preferred;
        // 两侧都被挡住时保持默认方向：宁可夹着开，也不要出现“门完全打不开”。
        if(!IsSwingBlocked(Other)){OpenDirection=Other;bOpenFlipped=true;}
    }
    TargetAngle=FMath::Abs(OpenAngleDegrees)*OpenDirection;
    AutoCloseRemaining=AutoCloseSeconds;
    UE_LOG(LogTemp,Display,TEXT("ColdSteelDoor %s 铰链侧=Y%s 玩家侧=%s 开门方向=%s %s"),*GetName(),
        HingeSign>0.f?TEXT("+"):TEXT("-"),
        bHasPlayer?(PlayerSide>0.f?TEXT("+X"):TEXT("-X")):TEXT("未知"),
        OpenDirection>=0.f?TEXT("+"):TEXT("-"),
        bOpenFlipped?TEXT("（推开侧被挡，已反向开）"):TEXT("（朝玩家反侧开）"));
}

void AColdSteelDoor::CloseDoor()
{
    bOpen=false;
    TargetAngle=0.f;
    AutoCloseRemaining=0.f;
}

void AColdSteelDoor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    ApplyAngle(DeltaSeconds);
    UpdateLeafPawnCollision();
    if(bOpen&&AutoCloseSeconds>0.f&&FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.5f))
    {
        AutoCloseRemaining-=DeltaSeconds;
        if(AutoCloseRemaining<=0.f)CloseDoor();
    }
}

void AColdSteelDoor::ApplyAngle(float DeltaSeconds)
{
    if(FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.05f))
    {
        CurrentAngle=TargetAngle;
        return;
    }
    const float Step=FMath::Max(1.f,OpenSeconds>KINDA_SMALL_NUMBER?OpenAngleDegrees/OpenSeconds:180.f);
    CurrentAngle=FMath::FInterpConstantTo(CurrentAngle,TargetAngle,DeltaSeconds,Step);
    Hinge->SetRelativeRotation(FRotator(0.f,CurrentAngle,0.f));
}
