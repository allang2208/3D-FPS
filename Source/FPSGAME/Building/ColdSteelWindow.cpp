#include "ColdSteelWindow.h"
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
    // 本工程自己的窗网格（SourceAssets/Window20260918 生成）；换外观只改这两个默认值。
    const TCHAR* DefaultFrameMesh=TEXT("/Game/Props/Window20260918/SM_WindowFrame_100.SM_WindowFrame_100");
    const TCHAR* DefaultLeafMesh=TEXT("/Game/Props/Window20260918/SM_WindowLeaf_100.SM_WindowLeaf_100");
    // 100×100 双开窗的标称尺寸（cm）：AlignGeometry 之后 Y／Z 仍以网格包围盒为准。
    constexpr float NominalOpeningHalfY=44.f;
    constexpr float NominalLeafHalfY=21.75f;
    constexpr float NominalFrameCenterZ=50.f;
}

AColdSteelWindow::AColdSteelWindow()
{
    PrimaryActorTick.bCanEverTick=true;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("WindowRoot")));

    Frame=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WindowFrame"));
    Frame->SetupAttachment(GetRootComponent());
    Frame->SetMobility(EComponentMobility::Movable);
    Frame->SetCollisionProfileName(TEXT("BlockAll"));
    Frame->SetCanEverAffectNavigation(false);

    // 两只铰链固定在洞口两侧（左扇铰左边、右扇铰右边），两扇因此朝同一侧对开。
    HingeLeft=CreateDefaultSubobject<USceneComponent>(TEXT("WindowHingeLeft"));
    HingeLeft->SetupAttachment(GetRootComponent());
    HingeLeft->SetRelativeLocation(FVector(0.f,-NominalOpeningHalfY,NominalFrameCenterZ));

    HingeRight=CreateDefaultSubobject<USceneComponent>(TEXT("WindowHingeRight"));
    HingeRight->SetupAttachment(GetRootComponent());
    HingeRight->SetRelativeLocation(FVector(0.f,NominalOpeningHalfY,NominalFrameCenterZ));

    // 窗扇从铰链往洞口中间伸：左扇 +Y、右扇 −Y（两侧都朝中间对开）。
    LeafLeft=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WindowLeafLeft"));
    LeafLeft->SetupAttachment(HingeLeft);
    LeafLeft->SetRelativeLocation(FVector(0.f,NominalLeafHalfY,0.f));
    LeafLeft->SetMobility(EComponentMobility::Movable);
    LeafLeft->SetCollisionProfileName(TEXT("BlockAll"));
    LeafLeft->SetCanEverAffectNavigation(false);

    LeafRight=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WindowLeafRight"));
    LeafRight->SetupAttachment(HingeRight);
    LeafRight->SetRelativeLocation(FVector(0.f,-NominalLeafHalfY,0.f));
    // 窗扇网格的圆形把手做在网格 +Y 侧：左扇直接用（+Y 朝洞口中间），右扇绕 Z 转 180° 让把手也朝中间。
    // 窗扇本体左右对称，转过来只有把手换边（位置与包围盒都不变）。
    LeafRight->SetRelativeRotation(FRotator(0.f,180.f,0.f));
    LeafRight->SetMobility(EComponentMobility::Movable);
    LeafRight->SetCollisionProfileName(TEXT("BlockAll"));
    LeafRight->SetCanEverAffectNavigation(false);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> FrameAsset(DefaultFrameMesh);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> LeafAsset(DefaultLeafMesh);
    if(FrameAsset.Succeeded())Frame->SetStaticMesh(FrameAsset.Object);
    if(LeafAsset.Succeeded())
    {
        LeafLeft->SetStaticMesh(LeafAsset.Object);
        LeafRight->SetStaticMesh(LeafAsset.Object);
    }
}

void AColdSteelWindow::BeginPlay()
{
    Super::BeginPlay();
    AlignGeometry();
    LogGeometryOnce();
}

void AColdSteelWindow::Configure(UMaterialInterface* Surface)
{
    if(!Surface)return;
    // 整扇窗统一材质：窗框与两扇窗扇的**全部**材质槽一起替换，和玩家用同种体素砌出来的墙一致。
    // 若要保留网格自带的玻璃槽，把下面三处循环改回只 SetMaterial(0, Surface) 即可。
    if(Frame)for(int32 Index=0;Index<FMath::Max(1,Frame->GetNumMaterials());++Index)Frame->SetMaterial(Index,Surface);
    if(LeafLeft)for(int32 Index=0;Index<FMath::Max(1,LeafLeft->GetNumMaterials());++Index)LeafLeft->SetMaterial(Index,Surface);
    if(LeafRight)for(int32 Index=0;Index<FMath::Max(1,LeafRight->GetNumMaterials());++Index)LeafRight->SetMaterial(Index,Surface);
}

void AColdSteelWindow::AlignGeometry()
{
    // 与门同一口径：一律以**包围盒**为准，网格 pivot 在底面／角上都不会让窗悬空或偏位。
    //   窗框：包围盒在 X／Y 居中、底面落在 z=0；
    //   窗扇：包围盒中心落在窗框竖直中心，铰链装在洞口两侧的框沿上（Y=洞口半宽）。
    if(const UStaticMesh* FrameMesh=Frame->GetStaticMesh())
    {
        const FBoxSphereBounds Bounds=FrameMesh->GetBounds();
        FrameOriginCm=Bounds.Origin;
        FrameExtentCm=Bounds.BoxExtent;
        Frame->SetRelativeLocation(FVector(-Bounds.Origin.X,-Bounds.Origin.Y,Bounds.BoxExtent.Z-Bounds.Origin.Z));
    }
    if(const UStaticMesh* LeafMesh=LeafLeft->GetStaticMesh())
    {
        const FBoxSphereBounds Bounds=LeafMesh->GetBounds();
        LeafOriginCm=Bounds.Origin;
        LeafExtentCm=Bounds.BoxExtent;
    }
    const float OpeningHalfY=FMath::Max(1.f,FrameExtentCm.Y-FrameMemberCm);
    const float FrameCenterZ=FrameExtentCm.Z;
    const float LeafHalfY=FMath::Max(1.f,LeafExtentCm.Y);
    HingeLeft->SetRelativeLocation(FVector(0.f,-OpeningHalfY,FrameCenterZ));
    HingeRight->SetRelativeLocation(FVector(0.f,OpeningHalfY,FrameCenterZ));
    // 窗扇相对铰链的 Y：左扇往 +Y 伸、右扇往 −Y 伸；X 由 ApplyHingeDepth 按开向定。
    LeafLeft->SetRelativeLocation(FVector(0.f,LeafHalfY-LeafOriginCm.Y,-LeafOriginCm.Z));
    LeafRight->SetRelativeLocation(FVector(0.f,-LeafHalfY-LeafOriginCm.Y,-LeafOriginCm.Z));
    CacheLeafBounds();
    ApplyHingeDepth();
    HingeLeft->SetRelativeRotation(FRotator(0.f,-SwingSign*CurrentAngle,0.f));
    HingeRight->SetRelativeRotation(FRotator(0.f,SwingSign*CurrentAngle,0.f));
}

void AColdSteelWindow::ApplyHingeDepth()
{
    if(LeafExtentCm.IsNearlyZero()||FrameExtentCm.IsNearlyZero())return;
    // 铰链贴在窗扇的外侧面（SwingSign>0，向外开）或内侧面（SwingSign<0，向内开），窗扇整体落在
    // 铰链内侧。铰链若固定放在窗框中间，窗扇转到 88° 时靠铰链的那半个厚度会切进窗框边梃。
    // 窗扇自身的世界位置不动（相对铰链反向偏移），所以换开向不会让关着的窗扇跳一下。
    // 深度用名义板厚，不用包围盒：把手凸出会让包围盒的 X 半宽变大（见 LeafHalfThicknessCm 的说明）。
    const float HingeX=SwingSign*LeafHalfThicknessCm;
    HingeLeft->SetRelativeLocation(FVector(HingeX,-(FrameExtentCm.Y-FrameMemberCm),FrameExtentCm.Z));
    HingeRight->SetRelativeLocation(FVector(HingeX,FrameExtentCm.Y-FrameMemberCm,FrameExtentCm.Z));
    const float LeafX=-HingeX-LeafOriginCm.X;
    LeafLeft->SetRelativeLocation(FVector(LeafX,LeafLeft->GetRelativeLocation().Y,LeafLeft->GetRelativeLocation().Z));
    LeafRight->SetRelativeLocation(FVector(LeafX,LeafRight->GetRelativeLocation().Y,LeafRight->GetRelativeLocation().Z));
}

void AColdSteelWindow::CacheLeafBounds()
{
    if(const UStaticMesh* Mesh=LeafLeft?LeafLeft->GetStaticMesh():nullptr)
    {
        const FBoxSphereBounds Bounds=Mesh->GetBounds();
        LeafExtentCm=Bounds.BoxExtent;
        LeafOriginCm=Bounds.Origin;
    }
}

bool AColdSteelWindow::IsSwingBlocked(float DirectionSign) const
{
    UWorld* World=GetWorld();
    if(!World||!LeafLeft||LeafExtentCm.IsNearlyZero()||FrameExtentCm.IsNearlyZero())return false;
    // 略缩小检测盒：窗扇贴着窗框与临格体素，贴合面不该算“被挡住”。
    const FCollisionShape Shape=FCollisionShape::MakeBox(LeafTestExtent());
    // 只查世界实体：玩家／怪物的碰撞体积不参与“窗口被挡”的判定（与门同一口径）。
    FCollisionObjectQueryParams ObjectParams;
    ObjectParams.AddObjectTypesToQuery(ECC_WorldStatic);
    ObjectParams.AddObjectTypesToQuery(ECC_WorldDynamic);
    ObjectParams.AddObjectTypesToQuery(ECC_Destructible);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(ColdSteelWindowSwing),false,this);
    Params.AddIgnoredActor(this);
    if(const AActor* Parent=GetAttachParentActor())Params.AddIgnoredActor(Parent);
    // 检测位置按**候选开向**摆：铰链贴面与窗扇偏移都由 DirectionSign 推出来，不用当前铰链位置——
    // 否则“换向再判定”会比真实开到位的位置偏半个铰链贴面差（4 cm），贴边的墙就可能误判。
    const float OpeningHalfY=FMath::Max(1.f,FrameExtentCm.Y-FrameMemberCm);
    const float LeafHalfY=FMath::Max(1.f,LeafExtentCm.Y);
    const float HingeX=DirectionSign*LeafHalfThicknessCm;
    const FVector Hinge[2]={FVector(HingeX,-OpeningHalfY,FrameExtentCm.Z),FVector(HingeX,OpeningHalfY,FrameExtentCm.Z)};
    const FVector Centre[2]={Hinge[0]+FVector(-HingeX,LeafHalfY,0.f),Hinge[1]+FVector(-HingeX,-LeafHalfY,0.f)};
    const FTransform ActorTransform=GetActorTransform();
    const float Full=FMath::Abs(OpenAngleDegrees)*DirectionSign;
    const float Samples[]={0.25f,0.5f,0.75f,1.f};
    for(const float Fraction:Samples)
    {
        // 两扇同向对开：左扇转 −Angle、右扇转 +Angle 时两扇朝同一侧（本地 +X 或 −X）摆。
        const float Angle=Full*Fraction;
        for(int32 Index=0;Index<2;++Index)
        {
            const FQuat Rotation(FRotator(0.f,Index?Angle:-Angle,0.f));
            const FVector Pivot=ActorTransform.TransformPosition(Hinge[Index]+Rotation.RotateVector(Centre[Index]-Hinge[Index]));
            const FQuat WorldRotation=ActorTransform.GetRotation()*Rotation;
            const FVector WorldCentre=Pivot+WorldRotation.RotateVector(LeafOriginCm);
            if(World->OverlapAnyTestByObjectType(WorldCentre,WorldRotation,ObjectParams,Shape,Params))
                return true;
        }
    }
    return false;
}

FVector AColdSteelWindow::LeafTestExtent() const
{
    // X 用名义板厚：把手那点凸出不参与扫掠判定（否则检测盒比扇板厚一倍，贴边的墙会误判成挡住）。
    return FVector(FMath::Max(1.f,LeafHalfThicknessCm*2.f-1.f),FMath::Max(1.f,LeafExtentCm.Y-2.f),
        FMath::Max(1.f,LeafExtentCm.Z-3.f));
}

bool AColdSteelWindow::LeavesOverlapPawn() const
{
    UWorld* World=GetWorld();
    if(!World||!LeafLeft||LeafExtentCm.IsNearlyZero())return false;
    FCollisionObjectQueryParams ObjectParams;
    ObjectParams.AddObjectTypesToQuery(ECC_Pawn);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(ColdSteelWindowPawn),false,this);
    Params.AddIgnoredActor(this);
    if(const AActor* Parent=GetAttachParentActor())Params.AddIgnoredActor(Parent);
    const FCollisionShape Shape=FCollisionShape::MakeBox(LeafTestExtent());
    const UStaticMeshComponent* Leaves[2]={LeafLeft,LeafRight};
    for(const UStaticMeshComponent* Leaf:Leaves)
    {
        if(!Leaf)continue;
        const FTransform LeafNow=Leaf->GetComponentTransform();
        if(World->OverlapAnyTestByObjectType(LeafNow.TransformPosition(LeafOriginCm),LeafNow.GetRotation(),
            ObjectParams,Shape,Params))
            return true;
    }
    return false;
}

void AColdSteelWindow::UpdateLeafPawnCollision()
{
    if(!LeafLeft)return;
    // 关着且已经静止才挡玩家；开窗/关窗过程中与开着时对 Pawn 放行，窗扇可以从玩家身上扫过去。
    const bool bSettled=FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.5f);
    bool bBlock=!bOpen&&bSettled;
    const bool bBlockingNow=LeafLeft->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block;
    // 玩家还站在窗扇里时先别恢复阻挡，等他离开，免得把人挤住或卡住。
    if(bBlock&&!bBlockingNow&&LeavesOverlapPawn())bBlock=false;
    if(bBlock!=bBlockingNow)SetLeavesPawnBlocking(bBlock);
}

void AColdSteelWindow::SetLeavesPawnBlocking(bool bBlock)
{
    const ECollisionResponse Response=bBlock?ECR_Block:ECR_Ignore;
    if(LeafLeft)LeafLeft->SetCollisionResponseToChannel(ECC_Pawn,Response);
    if(LeafRight)LeafRight->SetCollisionResponseToChannel(ECC_Pawn,Response);
}

void AColdSteelWindow::LogGeometryOnce()
{
    // 刚设置过相对位置，先刷新组件变换再读包围盒，避免读到上一帧的旧值。
    if(Frame)Frame->UpdateComponentToWorld();
    if(LeafLeft)LeafLeft->UpdateComponentToWorld();
    if(LeafRight)LeafRight->UpdateComponentToWorld();
    const FBox FrameBox=Frame?Frame->Bounds.GetBox():FBox(ForceInit);
    const FBox LeftBox=LeafLeft?LeafLeft->Bounds.GetBox():FBox(ForceInit);
    const FBox RightBox=LeafRight?LeafRight->Bounds.GetBox():FBox(ForceInit);
    if(!FrameBox.IsValid||!LeftBox.IsValid||!RightBox.IsValid)return;
    const bool bSameZ=FMath::Abs(LeftBox.Min.Z-RightBox.Min.Z)<1.f&&FMath::Abs(RightBox.Min.Z-FrameBox.Min.Z)<1.f;
    const bool bInside=LeftBox.Min.Y>=FrameBox.Min.Y-2.f&&RightBox.Max.Y<=FrameBox.Max.Y+2.f
        &&LeftBox.Max.Y<=RightBox.Min.Y+1.f;
    UE_LOG(LogTemp,Display,
        TEXT("ColdSteelWindow %s 窗框 z=[%.1f,%.1f] y=[%.1f,%.1f] 左扇 y=[%.1f,%.1f] 右扇 y=[%.1f,%.1f] 对齐=%s"),
        *GetName(),FrameBox.Min.Z,FrameBox.Max.Z,FrameBox.Min.Y,FrameBox.Max.Y,
        LeftBox.Min.Y,LeftBox.Max.Y,RightBox.Min.Y,RightBox.Max.Y,
        (bSameZ&&bInside)?TEXT("OK"):TEXT("CHECK"));
}

void AColdSteelWindow::ToggleWindow()
{
    if(bOpen)CloseWindow();else OpenWindow();
}

bool AColdSteelWindow::TryGetPlayerSideSign(float& OutSign) const
{
    const UWorld* World=GetWorld();
    const APlayerController* Controller=World?World->GetFirstPlayerController():nullptr;
    const APawn* Pawn=Controller?Controller->GetPawn():nullptr;
    if(!Pawn)return false;
    // 窗的本地 X 就是墙面法线：玩家在 +X 侧还是 −X 侧，决定两扇窗该往哪边开。
    const FVector Local=GetActorTransform().InverseTransformPosition(Pawn->GetActorLocation());
    if(FMath::Abs(Local.X)<1.f)return false;   // 玩家几乎贴在窗平面上，方向说不清
    OutSign=Local.X>0.f?1.f:-1.f;
    return true;
}

void AColdSteelWindow::OpenWindow()
{
    bOpen=true;
    // 默认方向由玩家决定：窗朝玩家的**反侧**开（等于玩家把窗推开），而不是固定方向。
    // 只有在拿不到玩家位置时才退回本地 +X 侧。
    float Preferred=1.f;
    float PlayerSide=0.f;
    const bool bHasPlayer=TryGetPlayerSideSign(PlayerSide);
    if(bHasPlayer)Preferred=-PlayerSide;
    // 首选那一侧被实体挡住就改从另一侧开（与门同一口径）。
    SwingSign=Preferred;
    bOpenFlipped=false;
    if(IsSwingBlocked(Preferred))
    {
        const float Other=-Preferred;
        // 两侧都被挡住时保持默认方向：宁可夹着开，也不要出现“窗完全打不开”。
        if(!IsSwingBlocked(Other)){SwingSign=Other;bOpenFlipped=true;}
    }
    // 先定开向再摆铰链贴面，否则窗扇会切进窗框边梃。
    ApplyHingeDepth();
    TargetAngle=FMath::Abs(OpenAngleDegrees);
    AutoCloseRemaining=AutoCloseSeconds;
    UE_LOG(LogTemp,Display,TEXT("ColdSteelWindow %s 玩家侧=%s 开向=%s %s"),*GetName(),
        bHasPlayer?(PlayerSide>0.f?TEXT("+X"):TEXT("-X")):TEXT("未知"),
        SwingSign>=0.f?TEXT("+X"):TEXT("-X"),
        bOpenFlipped?TEXT("（推开侧被挡，已反向开）"):TEXT("（朝玩家反侧开）"));
}

void AColdSteelWindow::CloseWindow()
{
    bOpen=false;
    TargetAngle=0.f;
    AutoCloseRemaining=0.f;
}

void AColdSteelWindow::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    ApplyAngle(DeltaSeconds);
    UpdateLeafPawnCollision();
    if(bOpen&&AutoCloseSeconds>0.f&&FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.5f))
    {
        AutoCloseRemaining-=DeltaSeconds;
        if(AutoCloseRemaining<=0.f)CloseWindow();
    }
}

void AColdSteelWindow::ApplyAngle(float DeltaSeconds)
{
    if(FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.05f))
    {
        CurrentAngle=TargetAngle;
        HingeLeft->SetRelativeRotation(FRotator(0.f,-SwingSign*CurrentAngle,0.f));
        HingeRight->SetRelativeRotation(FRotator(0.f,SwingSign*CurrentAngle,0.f));
        return;
    }
    const float Step=FMath::Max(1.f,OpenSeconds>KINDA_SMALL_NUMBER?OpenAngleDegrees/OpenSeconds:180.f);
    CurrentAngle=FMath::FInterpConstantTo(CurrentAngle,TargetAngle,DeltaSeconds,Step);
    HingeLeft->SetRelativeRotation(FRotator(0.f,-SwingSign*CurrentAngle,0.f));
    HingeRight->SetRelativeRotation(FRotator(0.f,SwingSign*CurrentAngle,0.f));
}
