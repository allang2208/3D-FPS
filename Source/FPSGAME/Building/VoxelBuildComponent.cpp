#include "VoxelBuildComponent.h"
#include "../WorldGeneration/ForestVillageMap.h"
#include "../FPSGAMEPlayerController.h"
#include "Camera/CameraActor.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/StreamableManager.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "VoxelBuildDebug.h"
#include "Camera/CameraTypes.h"
#include "Camera/PlayerCameraManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "VoxelCollapseFragment.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VillageBuildDefense.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelBuildWidget.h"
#include "VoxelJointStrength.h"
#include "../FPSGAMECharacter.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"

#include "VoxelBuildPlacementPrivate.h"
using namespace VoxelBuildPlacementPrivate;

namespace
{
    // Last frame the drawer widget consumed a key itself; keeps the same press from running twice.
    // 审计 U3（2026-09-23）：原为文件级 static，PIE 双开共享进程级 GFrameCounter，一个窗口的
    // 抽屉按键会吞掉另一个窗口同帧的 B/Esc/数字键。改为组件成员（见 MarkDrawerKeyHandled）。
    // Voxel construction shapes. The index is the stable brush id: the mouse wheel cycles it and the
    // drawer lists the same table in each material's 其他构造 submenu. bSwapsXY shapes turn with R.
    // 2026-10-14 屋顶组件（第一批体素排列）：参照主流建筑游戏的屋顶件分类（Valheim 专用件
    // 26°/45° 双角度 + 角件/屋脊，Minecraft/7DTD 楼梯楔形拼阶梯），先把核心排列做进体素笔刷——
    //   斜坡板（45° 与 26.6° 两档，1/2 格宽）：阶梯近似斜面，双坡对摆自然成脊；
    //   山墙三角（gable end）：等腰阶梯实心，封双坡两端；
    //   金字塔顶（pyramid cap）：小塔/四角亭收顶。
    // 外斜角（hip）/内天沟（valley）是对角阶梯排列，与屋脊压条（用既有 1×5 直线笔刷）留待
    // 第二批网格构件（构件化后才有真实斜面，体素排列只负责形状验证）。
    enum class EVoxelBrushKind:uint8{Box,Slope,Gable,Pyramid,Ridge};
    struct FVoxelBrushShape
    {
        const TCHAR* Name;
        FIntVector Size;      // 包围盒（R 旋转前）；Box 形状即填充尺寸
        bool bSwapsXY;
        EVoxelBrushKind Kind=EVoxelBrushKind::Box;
        int32 Length=1;       // Slope=坡长（爬升轴）；Gable/Pyramid=底边长
        int32 Width=1;        // Slope=横截宽；Gable=墙体厚度
        int32 RisePer=1;      // Slope=每 N 格升 1（1=45°，2≈26.6° 对齐 Valheim 26° 档）
    };
    const FVoxelBrushShape BrushShapes[]=
    {
        {TEXT("单格"),FIntVector(1,1,1),false,EVoxelBrushKind::Box},
        {TEXT("1 平方米地块"),FIntVector(5,5,1),false,EVoxelBrushKind::Box},
        {TEXT("1 平方米墙面"),FIntVector(5,1,5),true,EVoxelBrushKind::Box},
        {TEXT("1×5 水平直线"),FIntVector(5,1,1),true,EVoxelBrushKind::Box},
        {TEXT("1×5 垂直直线"),FIntVector(1,1,5),false,EVoxelBrushKind::Box},
        {TEXT("45°屋面坡 1×5"),FIntVector(5,1,5),true,EVoxelBrushKind::Slope,5,1,1},
        {TEXT("45°屋面坡 2×5"),FIntVector(5,2,5),true,EVoxelBrushKind::Slope,5,2,1},
        {TEXT("26°屋面坡 1×5"),FIntVector(5,1,3),true,EVoxelBrushKind::Slope,5,1,2},
        {TEXT("26°屋面坡 2×5"),FIntVector(5,2,3),true,EVoxelBrushKind::Slope,5,2,2},
        {TEXT("山墙三角 高5"),FIntVector(9,1,5),true,EVoxelBrushKind::Gable,9,1,0},
        {TEXT("金字塔顶 5×5"),FIntVector(5,5,3),false,EVoxelBrushKind::Pyramid,5,5,0},
        // 2026-10-16 屋脊压条：一行帐篷双切格（脊线两端高 10cm 的脊帽），压在双坡交汇的 V 槽上。
        {TEXT("屋脊压条 1×5"),FIntVector(5,1,1),true,EVoxelBrushKind::Ridge,5,1,0},
        // 2026-10-19 连续平面：偶数宽山墙（10 格=2 m）与两节 5 格 45° 坡正好对齐，
        // 脊线落在格边界，不再靠半格帐篷帽过渡；奇数宽仍用上面 9 格件。
        {TEXT("山墙三角 宽10 高5"),FIntVector(10,1,5),true,EVoxelBrushKind::Gable,10,1,0},
    };
    /** 非 Box 形状的格子生成器（2026-10-14 屋顶阶梯族）。生成顺序保证首格=包围盒最小角
     *  （UpdatePreview 与放置计划都拿 Placement[0] 当盒 Min）。bSwap=R 键旋转：生成后交换
     *  X/Y，与 ShapeSize 的包围盒交换一致（Base 的居中偏移用旋转后 Size，两侧对齐）。 */
    void AppendShapeCells(const FVoxelBrushShape& Entry,bool bSwap,FIntVector Min,TArray<FIntVector>& Out)
    {
        auto Add=[&](int32 X,int32 Y,int32 Z)
        {FIntVector C=Min+FIntVector(X,Y,Z);if(bSwap)Swap(C.X,C.Y);Out.Add(C);};
        switch(Entry.Kind)
        {
        case EVoxelBrushKind::Slope:
            // 2026-10-19 一层薄壳（用户指定视觉）：45°坡只放坡面顶格，下方不填阶梯；
            // 相邻顶格共用 20×20 坡棱接缝，续坡时宽度轴与命中坡段对齐（见 UpdateTarget
            // 的 bContinuePlane 分支），坡面以外不塞隐藏承重格。
            // 26°坡仍保留实心阶梯：半格错位的一层壳没有等价的连续棱接缝。
            if(Entry.RisePer==1)
            {
                for(int32 X=0;X<Entry.Length;++X)
                    for(int32 Y=0;Y<Entry.Width;++Y)Add(X,Y,X);
            }
            else
            {
                for(int32 X=0;X<Entry.Length;++X)
                {const int32 Top=X/Entry.RisePer;for(int32 Z=0;Z<=Top;++Z)for(int32 Y=0;Y<Entry.Width;++Y)Add(X,Y,Z);}
            }
            break;
        case EVoxelBrushKind::Gable:   // 等腰阶梯三角实心：第 Z 行宽 Length-2Z、起点内缩 Z
            for(int32 Z=0;Z<(Entry.Length+1)/2;++Z)
                for(int32 X=0;X<Entry.Length-2*Z;++X)
                    for(int32 Y=0;Y<Entry.Width;++Y)Add(Z+X,Y,Z);
            break;
        case EVoxelBrushKind::Pyramid: // 层 Z 内缩 Z：5×5 底 → 3×3 → 1×1
            for(int32 Z=0;Z<(Entry.Length+1)/2;++Z)
                for(int32 Y=Z;Y<Entry.Length-Z;++Y)
                    for(int32 X=Z;X<Entry.Length-Z;++X)Add(X,Y,Z);
            break;
        case EVoxelBrushKind::Ridge:   // 屋脊压条：单行（沿 +X），脊帽切割见 ShapeCuts
            for(int32 X=0;X<Entry.Length;++X)for(int32 Y=0;Y<Entry.Width;++Y)Add(X,Y,0);
            break;
        default:break;
        }
    }
}

int32 UVoxelBuildComponent::ShapeCount(){return UE_ARRAY_COUNT(BrushShapes);}

FIntVector UVoxelBuildComponent::ShapeSize(int32 Shape,int32 Rotation)
{
    const FVoxelBrushShape& Entry=BrushShapes[FMath::Clamp(Shape,0,ShapeCount()-1)];
    return ((Rotation&1)&&Entry.bSwapsXY)?FIntVector(Entry.Size.Y,Entry.Size.X,Entry.Size.Z):Entry.Size;
}

const TCHAR* UVoxelBuildComponent::ShapeName(int32 Shape)
{
    return BrushShapes[FMath::Clamp(Shape,0,ShapeCount()-1)].Name;
}

bool UVoxelBuildComponent::ShapeIsStaircase(int32 Shape)
{
    return BrushShapes[FMath::Clamp(Shape,0,ShapeCount()-1)].Kind!=EVoxelBrushKind::Box;
}

bool UVoxelBuildComponent::ShapeIsSlope(int32 Shape)
{
    return BrushShapes[FMath::Clamp(Shape,0,ShapeCount()-1)].Kind==EVoxelBrushKind::Slope;
}

int32 UVoxelBuildComponent::ShapeSlopeRise(int32 Shape)
{
    const FVoxelBrushShape& Entry=BrushShapes[FMath::Clamp(Shape,0,ShapeCount()-1)];
    return Entry.Kind==EVoxelBrushKind::Slope?Entry.RisePer:0;
}

void UVoxelBuildComponent::ShapeCells(int32 Shape,int32 Rotation,TArray<FIntVector>& OutCells)
{
    OutCells.Reset();
    const FVoxelBrushShape& Entry=BrushShapes[FMath::Clamp(Shape,0,ShapeCount()-1)];
    const bool bSwap=(Rotation&1)&&Entry.bSwapsXY;
    if(Entry.Kind==EVoxelBrushKind::Box)
    {
        FIntVector Size=Entry.Size;
        if(bSwap)Swap(Size.X,Size.Y);
        for(int32 Z=0;Z<Size.Z;++Z)for(int32 Y=0;Y<Size.Y;++Y)for(int32 X=0;X<Size.X;++X)
        {FIntVector C(X,Y,Z);if(bSwap)Swap(C.X,C.Y);OutCells.Add(C);}
        return;
    }
    AppendShapeCells(Entry,bSwap,FIntVector::ZeroValue,OutCells);
    if(Rotation>=2)
    {
        // 180°（绕 Z）：切割坡的镜像朝向；变换后重排，保证首格仍是包围盒最小角
        //（UpdatePreview/Placement[0] 依赖这一点）。奇数步已在生成时交换 X/Y，
        // 180° 只在交换后的坐标系里翻转 X/Y。
        const FIntVector Size=ShapeSize(Shape,Rotation);
        for(FIntVector& C:OutCells)
        {C.X=Size.X-1-C.X;C.Y=Size.Y-1-C.Y;}
        OutCells.Sort([](const FIntVector& A,const FIntVector& B)
        {return A.X!=B.X?A.X<B.X:(A.Y!=B.Y?A.Y<B.Y:A.Z<B.Z);});
    }
}

void UVoxelBuildComponent::ShapeCuts(int32 Shape,int32 Rotation,const TArray<FIntVector>& Cells,TArray<uint8>& OutCuts)
{
    OutCuts.Init(0,Cells.Num());
    const FVoxelBrushShape& Entry=BrushShapes[FMath::Clamp(Shape,0,ShapeCount()-1)];
    if(Entry.Kind==EVoxelBrushKind::Box)return;
    // 统一方向旋转：模板系方向 → 旋转后世界系（Slope 的四态坡向/Gable 两坡/Pyramid 四面共用）。
    // rot1=交换 X/Y；rot2=翻转 X；rot3=先换后翻。
    constexpr uint8 RotateDir[4][5]={
        {0,1,2,3,4},      // rot0
        {0,3,4,1,2},      // rot1: X↔Y
        {0,2,1,4,3},      // rot2: +X↔-X, +Y↔-Y
        {0,4,3,2,1}};     // rot3: 换+翻
    const FIntVector SwappedSize=ShapeSize(Shape,Rotation&1);
    for(int32 I=0;I<Cells.Num();++I)
    {
        // 逆变换回模板本地格（所有角色判定都在模板坐标系里做）。
        FIntVector Local=Cells[I];
        if(Rotation&1)Swap(Local.X,Local.Y);
        if(Rotation>=2){Local.X=SwappedSize.X-1-Local.X;Local.Y=SwappedSize.Y-1-Local.Y;}
        uint8 TemplateDir=0,Pattern=0;
        switch(Entry.Kind)
        {
        case EVoxelBrushKind::Slope:
            // 45°一层薄壳：所有格都是坡面顶格，全部带 45° 切；26°仍是实心+顶格切割。
            if(Local.Z!=Local.X/Entry.RisePer)break;
            TemplateDir=1;   // 模板坡沿 +X 爬高
            if(Entry.RisePer==2)Pattern=(Local.X%Entry.RisePer)==0?1:2;
            break;
        case EVoxelBrushKind::Gable:
        {
            // 左右两坡的列顶格各带一个 45 切。奇数宽：顶行只剩一格，用帐篷帽跨出半格脊线；
            // 偶数宽（2026-10-19 宽10）：顶行两格各切一刀，脊线正好落在两格边界，不需要帽。
            const bool bEven=(Entry.Length&1)==0;
            const int32 Half=(Entry.Length-1)/2;
            if(!bEven&&Local.Z==Half&&Local.X==Half){TemplateDir=1;Pattern=3;} // 脊线帐篷（脊沿 Y）
            else if(Local.X==Local.Z){TemplateDir=1;}                          // 左坡面 z=x
            else if(Local.X==Entry.Length-1-Local.Z){TemplateDir=2;}           // 右坡面 z=L-1-x
            break;
        }
        case EVoxelBrushKind::Pyramid:
            // 四面 45 切（面 z=x / z=L-1-x / z=y / z=L-1-y）；角格属两面，取 X 面（留阶梯=hip 檩线）。
            if(Local.X==Local.Z)TemplateDir=1;
            else if(Local.X==Entry.Length-1-Local.Z)TemplateDir=2;
            else if(Local.Y==Local.Z)TemplateDir=3;
            else if(Local.Y==Entry.Length-1-Local.Z)TemplateDir=4;
            break;
        case EVoxelBrushKind::Ridge:
            TemplateDir=3;Pattern=3;   // 帐篷：模板行沿 X，脊线沿 X（Dir 3/4 族），旋转时换轴
            break;
        default:break;
        }
        if(!TemplateDir)continue;
        OutCuts[I]=VoxelCut::Make(RotateDir[Rotation&3][TemplateDir],Pattern);
    }
}

void UVoxelBuildComponent::DebugShapeCells(int32 Shape,bool bRotate,TArray<FIntVector>& OutCells)
{
    ShapeCells(Shape,bRotate?1:0,OutCells);
}

void UVoxelBuildComponent::DebugShapePlan(int32 Shape,int32 Rotation,TArray<FIntVector>& OutCells,TArray<uint8>& OutCuts)
{
    ShapeCells(Shape,Rotation,OutCells);
    ShapeCuts(Shape,Rotation,OutCells,OutCuts);
}

UVoxelBuildComponent::UVoxelBuildComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
    PaletteAsset=TSoftObjectPtr<UVoxelBuildPalette>(FSoftObjectPath(TEXT("/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette.DA_VoxelBuildPalette")));
}

UInstancedStaticMeshComponent* UVoxelBuildComponent::FindAimEdge(AActor* PreviewActorArg)
{
    // 组件由预览 Actor 持有；缓存丢了（Live Coding 重载、世界切换）就按名字重新认领。
    if(AimEdgeComponent&&AimEdgeComponent->IsValidLowLevelFast())return AimEdgeComponent;
    AimEdgeComponent=nullptr;
    AActor* Owner=IsValid(PreviewActorArg)?PreviewActorArg:PreviewActor.Get();
    if(!Owner)return nullptr;
    for(UActorComponent* Component:Owner->GetComponents())
        if(auto* Instanced=Cast<UInstancedStaticMeshComponent>(Component))
            if(Instanced->GetFName()==FName(TEXT("VoxelAimEdges"))){AimEdgeComponent=Instanced;break;}
    return AimEdgeComponent;
}

void UVoxelBuildComponent::ClearAimHighlight(AActor* PreviewActorArg)
{
    if(auto* Edges=FindAimEdge(PreviewActorArg)){Edges->ClearInstances();Edges->SetVisibility(false);}
    AimEdgeCell=FIntVector(INT32_MAX);AimEdgeSignature=0;AimEdgeCount=-1;
}

void UVoxelBuildComponent::TryInitializeWorld()
{
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->IsLocalController()||!PC->GetPawn())return;

    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    if(Map!=TEXT("DayNight_Lighting")&&Map!=TEXT("L_Normandy_FPS_Test")&&Map!=TEXT("L_MilitaryTrench_FPS_Test")&&!ForestVillageMap::HasVillage(Map))
    {InitializationMessage=TEXT("当前场景尚未开放体素建造");bInitializeFailed=true;return;}
    // Start in parallel with entry preparation, before Hills::bReady releases input.
    if(!PreparePreviewAssets())return;
    auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||Model->ProfileSlot().IsEmpty())return;
    FString Key=Model->ProfileSlot()+TEXT("|")+Map;
    if(ForestVillageMap::HasVillage(Map))
    {
        ATemperateHillsWorld* Hills=nullptr;for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It){Hills=*It;break;}
        if(!Hills||!Hills->bReady||!Hills->WorldId.IsValid())return;
        VillageWorld=Hills;
        Key+=TEXT("|")+Hills->WorldId.ToString(EGuidFormats::Digits);
    }
    Palette=PaletteAsset.LoadSynchronous();
    if(!Palette){InitializationMessage=TEXT("体素材质资源尚未生成");bInitializeFailed=true;return;}
    if(GetNetMode()==NM_Client)
    {for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It)if(It->IsReady()){BuildWorld=*It;break;}
     if(!BuildWorld){InitializationMessage=TEXT("正在同步队伍建筑");return;}}
    else BuildWorld=GetWorld()->SpawnActor<AVoxelBuildWorld>();
    if(!BuildWorld||(GetNetMode()!=NM_Client&&!BuildWorld->Initialize(Key,Palette)))
    {InitializationMessage=BuildWorld?BuildWorld->ResultMessage():TEXT("无法创建建筑世界");bInitializeFailed=true;return;}
    // AController is hidden by default. A component owned by it cannot be
    // made visible with SetVisibility alone, so the ghost needs its own Actor.
    FActorSpawnParameters PreviewSpawn;PreviewSpawn.Owner=PC;PreviewSpawn.ObjectFlags|=RF_Transient;
    PreviewSpawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    PreviewActor=GetWorld()->SpawnActor<AActor>(AActor::StaticClass(),FVector::ZeroVector,FRotator::ZeroRotator,PreviewSpawn);
    PreviewActor->SetActorHiddenInGame(false);PreviewActor->SetActorEnableCollision(false);
    auto* PreviewRoot=NewObject<USceneComponent>(PreviewActor,TEXT("VoxelPreviewRoot"));
    PreviewActor->AddInstanceComponent(PreviewRoot);PreviewActor->SetRootComponent(PreviewRoot);
    PreviewRoot->SetMobility(EComponentMobility::Movable);PreviewRoot->RegisterComponent();
    Preview=NewObject<UStaticMeshComponent>(PreviewActor,TEXT("VoxelPlacementGhost"));
    PreviewActor->AddInstanceComponent(Preview);Preview->SetupAttachment(PreviewRoot);
    Preview->SetStaticMesh(GhostMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    Preview->SetCollisionEnabled(ECollisionEnabled::NoCollision);Preview->SetCastShadow(false);
    Preview->SetMobility(EComponentMobility::Movable);
    Preview->SetCanEverAffectNavigation(false);Preview->SetVisibility(false);Preview->RegisterComponent();
    FoundationPreview=NewObject<UInstancedStaticMeshComponent>(PreviewActor,TEXT("VoxelFoundationGhost"));
    PreviewActor->AddInstanceComponent(FoundationPreview);FoundationPreview->SetupAttachment(PreviewRoot);
    FoundationPreview->SetStaticMesh(Preview->GetStaticMesh());FoundationPreview->SetMobility(EComponentMobility::Movable);
    FoundationPreview->SetCollisionEnabled(ECollisionEnabled::NoCollision);FoundationPreview->SetCastShadow(false);
    FoundationPreview->SetCanEverAffectNavigation(false);FoundationPreview->SetVisibility(false);FoundationPreview->RegisterComponent();
    // 2026-10-14：阶梯形状（屋顶坡/山墙/金字塔）的逐格 ghost 通道，与整体盒/地基柱互不抢占。
    CellGhost=NewObject<UInstancedStaticMeshComponent>(PreviewActor,TEXT("VoxelCellGhost"));
    PreviewActor->AddInstanceComponent(CellGhost);CellGhost->SetupAttachment(PreviewRoot);
    CellGhost->SetStaticMesh(Preview->GetStaticMesh());CellGhost->SetMobility(EComponentMobility::Movable);
    CellGhost->SetCollisionEnabled(ECollisionEnabled::NoCollision);CellGhost->SetCastShadow(false);
    CellGhost->SetCanEverAffectNavigation(false);CellGhost->SetVisibility(false);CellGhost->RegisterComponent();
    auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Building/Voxels/Rounded/M_Voxel_PlacementPreview.M_Voxel_PlacementPreview"));
    if(!Material)Material=Palette->PreviewMaterial.LoadSynchronous();
    if(Material)
    {PreviewMID=UMaterialInstanceDynamic::Create(Material,this);Preview->SetMaterial(0,PreviewMID);FoundationPreview->SetMaterial(0,PreviewMID);CellGhost->SetMaterial(0,PreviewMID);}
    // 2026-10-15：楔形切割坡的逐格 ghost（45°/26°下/26°上三网格；缺资产时保持 null，
    //  UpdatePreview 回落 CellGhost 立方体）。网格由 CreateExampleMeshCut 同源烘焙，几何与放置后一致。
    auto MakeCutGhost=[&](const TCHAR* Name,UStaticMesh* Mesh)->UInstancedStaticMeshComponent*
    {
        if(!Mesh)return nullptr;
        auto* C=NewObject<UInstancedStaticMeshComponent>(PreviewActor,Name);
        PreviewActor->AddInstanceComponent(C);C->SetupAttachment(PreviewRoot);
        C->SetStaticMesh(Mesh);C->SetMobility(EComponentMobility::Movable);
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCastShadow(false);
        C->SetCanEverAffectNavigation(false);C->SetVisibility(false);C->RegisterComponent();
        if(PreviewMID)C->SetMaterial(0,PreviewMID);
        return C;
    };
    const FString WedgeDir=TEXT("/Game/Building/Voxels/Rounded/");
    CellCutGhost45=MakeCutGhost(TEXT("VoxelCellCut45"),LoadObject<UStaticMesh>(nullptr,*(WedgeDir+TEXT("SM_VoxelWedge45.SM_VoxelWedge45"))));
    CellCutGhost26L=MakeCutGhost(TEXT("VoxelCellCut26L"),LoadObject<UStaticMesh>(nullptr,*(WedgeDir+TEXT("SM_VoxelWedge26L.SM_VoxelWedge26L"))));
    CellCutGhost26U=MakeCutGhost(TEXT("VoxelCellCut26U"),LoadObject<UStaticMesh>(nullptr,*(WedgeDir+TEXT("SM_VoxelWedge26U.SM_VoxelWedge26U"))));
    CellCutGhostTent=MakeCutGhost(TEXT("VoxelCellCutTent"),LoadObject<UStaticMesh>(nullptr,*(WedgeDir+TEXT("SM_VoxelTent.SM_VoxelTent"))));
    // Gold edge highlight for the block being snapped against: twelve thin bars with their own MID.
    AimEdgeComponent=NewObject<UInstancedStaticMeshComponent>(PreviewActor,TEXT("VoxelAimEdges"));
    PreviewActor->AddInstanceComponent(AimEdgeComponent);AimEdgeComponent->SetupAttachment(PreviewRoot);
    AimEdgeComponent->SetStaticMesh(Preview->GetStaticMesh());AimEdgeComponent->SetMobility(EComponentMobility::Movable);
    AimEdgeComponent->SetCollisionEnabled(ECollisionEnabled::NoCollision);AimEdgeComponent->SetCastShadow(false);
    AimEdgeComponent->SetCanEverAffectNavigation(false);AimEdgeComponent->SetVisibility(false);
    UMaterialInterface* EdgeMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Building/Voxels/Rounded/M_VoxelAimEdge.M_VoxelAimEdge"));
    bAimEdgeGold=EdgeMaterial!=nullptr;
    if(!EdgeMaterial)EdgeMaterial=Material;
    if(EdgeMaterial){AimEdgeMaterial=UMaterialInstanceDynamic::Create(EdgeMaterial,this);AimEdgeComponent->SetMaterial(0,AimEdgeMaterial);}
    AimEdgeComponent->RegisterComponent();
    ClearAimHighlight(PreviewActor);
    // Above the gameplay HUD so the flush-right drawer covers the panel navigation entries.
    Widget=CreateWidget<UVoxelBuildWidget>(PC);if(Widget){Widget->AddToPlayerScreen(21);Widget->SetVisibility(ESlateVisibility::Collapsed);}
    PushPanelContent();
}

void UVoxelBuildComponent::SetBuildMode(bool Enabled)
{
    auto* PC=Cast<APlayerController>(GetOwner());
    if(Enabled&&PC&&UDungeonRoomSubsystem::IsDungeonPawn(PC->GetPawn()))return;
    if(Enabled&&(!PC||PC->bShowMouseCursor||PC->IsMoveInputIgnored()||PC->IsLookInputIgnored()))
    {
        UE_LOG(LogTemp,Display,TEXT("VOXEL_PANEL SetBuildMode(true) 被输入锁拒绝 cursor=%d move=%d look=%d"),
            PC&&PC->bShowMouseCursor?1:0,PC&&PC->IsMoveInputIgnored()?1:0,PC&&PC->IsLookInputIgnored()?1:0);
        return;
    }
    if(Enabled&&(!BuildWorld||!BuildWorld->IsReady()))
    {
        // Pressing V may retry after assets have been authored in the same session.
        if(!BuildWorld){bInitializeFailed=false;TryInitializeWorld();}
        if(!BuildWorld||!BuildWorld->IsReady())
        {
            if(auto* Model=UGameInstance::GetSubsystem<UColdSteelStatusModel>(GetWorld()->GetGameInstance()))
                Model->PostNotice(TEXT("建造"),InitializationMessage);
            return;
        }
    }
    if(bActive==Enabled)return;
    if(auto* Character=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr)Character->SuspendWeaponForMenu();
    bActive=Enabled;FeedbackTime=0;bUndoModifier=false;
    if(Enabled)bSnapEnabled=true;
    if(Enabled&&BuildWorld->UnsupportedBlockCount()>0)
    {
        Feedback=FString::Printf(TEXT("已有 %d 格需要补充支撑，原建筑已保留"),BuildWorld->UnsupportedBlockCount());
        FeedbackTime=4;bFeedbackValid=false;
    }
    if(Preview)Preview->SetVisibility(false,true);
    if(FoundationPreview)FoundationPreview->SetVisibility(false);
    for(UInstancedStaticMeshComponent* G:{CellGhost,CellCutGhost45,CellCutGhost26L,CellCutGhost26U,CellCutGhostTent})if(G)G->SetVisibility(false);
    if(!Enabled)HideSiegeRangePreview();
    // The gold snapped-neighbour outline is not refreshed once build mode stops, so clear it here.
    ClearAimHighlight(PreviewActor);
    // Entering build mode opens the drawer with the cursor; picking an entry returns to aiming.
    SetPanelOpen(Enabled);
    if(Enabled){PlacementCheckAt=0;TargetUpdateAt=0;UpdateWidget();}
}

// ===== 2026-09-20 吸附排查：自驱瞄准扫描（同步单次调用，入口 RunAimDiagnostics） =====
namespace
{
    struct FAimDiagSweep
    {
        TArray<FString> Report;
        TArray<TPair<FString,FVector>> Targets;
        FRotator SavedRotation=FRotator::ZeroRotator;
        FVector SavedLocation=FVector::ZeroVector;
        bool bWasActive=false,bWasPanel=false,bWasSnap=false;
    } AimDiag;
}
void UVoxelBuildComponent::RunAimDiagnostics()
{
    auto* PC=Cast<APlayerController>(GetOwner());
    const FString OutPath=FPaths::ProjectSavedDir()/TEXT("aimdiag_report.txt");
    if(!PC||!PC->GetPawn()||!PC->PlayerCameraManager||!BuildWorld||!BuildWorld->IsReady())
    {FFileHelper::SaveStringToFile(TEXT("prerequisites missing (pc/pawn/camera/world)"),*OutPath);return;}
    if(SelectedMaterial.IsNone())
    {FFileHelper::SaveStringToFile(TEXT("no material selected"),*OutPath);return;}

    AimDiag.Report.Reset();AimDiag.Targets.Reset();
    AimDiag.bWasActive=bActive;AimDiag.bWasPanel=bPanelOpen;AimDiag.bWasSnap=bSnapEnabled;
    AimDiag.SavedRotation=PC->GetControlRotation();
    AimDiag.SavedLocation=PC->GetPawn()->GetActorLocation();

    // 站位：距第一件构件 3 m、眼睛高度；瞄准点：每件构件中心与顶带，加脚下地面与天空对照。
    AVoxelBuildPrefabActor* First=nullptr;
    for(TActorIterator<AVoxelBuildPrefabActor> It(GetWorld());It;++It)
    {
        AVoxelBuildPrefabActor* Piece=*It;
        const FVector C=Piece->GetActorLocation();
        AimDiag.Targets.Add({Piece->GetName()+TEXT("@center"),C});
        AimDiag.Targets.Add({Piece->GetName()+TEXT("@top"),C+FVector(0,0,110)});
        if(!First)First=Piece;
    }
    const FVector Stand=First?First->GetActorLocation()+FVector(300,300,130):AimDiag.SavedLocation;
    // 体素块本身也是目标：世界 Actor 上的网格组件（分块）取前几个的包围盒中心。
    {
        TInlineComponentArray<UPrimitiveComponent*> Chunks(BuildWorld);
        for(int32 CI=0;CI<Chunks.Num()&&CI<4;++CI)
            AimDiag.Targets.Add({FString::Printf(TEXT("chunk%d@%.0f,%.0f"),CI,Chunks[CI]->Bounds.Origin.X,Chunks[CI]->Bounds.Origin.Y),Chunks[CI]->Bounds.Origin});
    }
    AimDiag.Targets.Add({TEXT("ground@stand"),Stand-FVector(0,0,100)});
    AimDiag.Targets.Add({TEXT("sky"),Stand+FVector(-300,-300,2600)});
    bActive=true;bPanelOpen=false;bSnapEnabled=true;
    // 绕过输入锁直进瞄准态：外部驱动通道在重负载（资产导入/缩略图）下极不稳定，
    // 全扫描在本调用内同步完成——每姿态 SetControlRotation 后直接 SetCameraCachePOV 把相机 POV
    // 顶到位（UpdateViewTarget 是 protected，写缓存是公开等效路径），再直调 UpdateTarget。
    AimDiag.Report.Add(FString::Printf(TEXT("targets=%d material=%s snap=1"),
        AimDiag.Targets.Num(),*SelectedMaterial.ToString()));
    for(int32 Index=0;Index<AimDiag.Targets.Num();++Index)
    {
        // 每个目标各自的就近站位（射线只有 6 m，从公共站位够不到远处的构件——第一轮就栽在这）。
        const FVector LocalStand=AimDiag.Targets[Index].Value+FVector(300,300,130);
        PC->GetPawn()->SetActorLocation(LocalStand,false,nullptr,ETeleportType::TeleportPhysics);
        // 同一目标四个姿态：直视 / 偏航±3° / 抬 8°——小视角偏移不应让方案瞬间消失。
        const int32 Pose=Index%4;
        FVector Eye;FRotator EyeRot;
        PC->GetPawn()->GetActorEyesViewPoint(Eye,EyeRot);
        FRotator Aim=(AimDiag.Targets[Index].Value-Eye).Rotation();
        if(Pose==1)Aim.Yaw+=3;
        else if(Pose==2)Aim.Yaw-=3;
        else if(Pose==3)Aim.Pitch=FMath::Min(Aim.Pitch+8.f,89.f);
        PC->SetControlRotation(Aim);
        FMinimalViewInfo POV;POV.Location=Eye;POV.Rotation=Aim;POV.FOV=90.f;
        PC->PlayerCameraManager->SetCameraCachePOV(POV);
        UpdateTarget();
        const FVector AimDir=PC->PlayerCameraManager->GetCameraRotation().Vector();
        AimDiag.Report.Add(FString::Printf(
            TEXT("%s pose#%d plan=%d valid=%d assisted=%d grow=%d hits=%d cell=%d,%d,%d aimDir=%.2f,%.2f,%.2f hitActor=%s msg=%s"),
            *AimDiag.Targets[Index].Key,Pose,Placement.Num(),bCanPlace?1:0,LastAimWasAssisted?1:0,GrowUpPlan?1:0,
            AimScratch.Num(),HitCell.Cell.X,HitCell.Cell.Y,HitCell.Cell.Z,AimDir.X,AimDir.Y,AimDir.Z,
            *GetNameSafe(Hit.GetActor()),*TargetMessage));
    }
    PC->SetControlRotation(AimDiag.SavedRotation);
    PC->GetPawn()->SetActorLocation(AimDiag.SavedLocation,false,nullptr,ETeleportType::TeleportPhysics);
    bActive=AimDiag.bWasActive;bPanelOpen=AimDiag.bWasPanel;bSnapEnabled=AimDiag.bWasSnap;
    AimDiag.Report.Add(TEXT("== done =="));
    FFileHelper::SaveStringToFile(FString::Join(AimDiag.Report,LINE_TERMINATOR),*OutPath);
    UE_LOG(LogTemp,Warning,TEXT("AIMDIAG %d lines recorded"),AimDiag.Report.Num());
}

FIntVector UVoxelBuildComponent::BrushSize() const
{
    return ShapeSize(Brush,BrushRotation);
}

void UVoxelBuildComponent::FillBrush(FIntVector Base,TArray<FIntVector>& Result,TArray<uint8>* OutCuts) const
{
    const FIntVector Size=BrushSize();Result.Reset();if(OutCuts)OutCuts->Reset();
    // Center horizontal dimensions around the aimed cell; walls grow upward.
    // 2026-10-16：斜坡刷的行进轴不居中——低边从瞄准格起坡（吸附墙沿/屋檐时坡从锚点向外爬，
    // 居中会把三角甩出墙端）。宽度轴与山墙/金字塔等对称形状维持居中。
    const bool bSlopeAnchors=ShapeIsSlope(Brush);
    const int32 RunAxis=BrushRotation&1;
    if(!(bSlopeAnchors&&RunAxis==0))Base.X-=Size.X/2;
    if(!(bSlopeAnchors&&RunAxis==1))Base.Y-=Size.Y/2;
    // 2026-10-19 连续平面：四态坡刷统一"瞄准格=低边（檐口）"。
    // 模板的低边在 +X/+Y 为最小端、在 -X/-Y 为最大端；负向旋转把包围盒沿行进轴
    // 回让 (Size-1) 格，低边才落在瞄准格上，双坡对摆时脊线/檐口不再错一格。
    // 放置/拆除/幽灵共用这一口径：瞄准格永远是檐口，拆除预览与实际坡段对齐。
    if(bSlopeAnchors&&(BrushRotation&2))Base[RunAxis]-=(RunAxis==0?Size.X:Size.Y)-1;
    // 2026-10-14：格子排列走 ShapeCells 统一真源（Box/屋顶阶梯同一路径，面板图标与
    // DebugShapeCells 出口共享），居中口径与旋转后包围盒一致。
    TArray<FIntVector> Cells;
    ShapeCells(Brush,BrushRotation,Cells);
    // 2026-10-15：楔形切割与格按下标平行（模板序）——坡刷出切口，其余形状全 0。
    if(OutCuts)ShapeCuts(Brush,BrushRotation,Cells,*OutCuts);
    for(const FIntVector& C:Cells)Result.Add(Base+C);
}

void UVoxelBuildComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(!BuildWorld&&!bInitializeFailed){InitializeCountdown-=Delta;if(InitializeCountdown<=0){InitializeCountdown=.5f;TryInitializeWorld();}}
    if(!bActive)
    {
        // Safety net: no exit path (drawer, other menu, Live Coding reload, level change) may leave
        // the gold outline behind. Costs one visibility query per frame while not building.
        if(AimEdgeComponent&&(AimEdgeComponent->IsVisible()||AimEdgeComponent->GetInstanceCount()>0))
            ClearAimHighlight(PreviewActor);
        HideSiegeRangePreview();
        return;
    }
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->GetPawn()){SetBuildMode(false);return;}
    if(VillageCamera)
    {
        const auto* Player=Cast<AFPSGAMEPlayerController>(PC);
        const bool ExternalMenu=Player&&(Player->IsGameMenuOpen()||Player->IsActionPreservingPanelOpen()
            ||Player->IsAlchemyOpen()||Player->IsWoodworkingOpen());
        if(ExternalMenu || PC->GetPawn()!=VillageCameraPawn.Get() || PC->GetViewTarget()!=VillageCamera ||
            (VillageBuilderHealth.IsValid() && VillageBuilderHealth->IsDead()))
        {
            LeaveVillageCamera(!ExternalMenu);
            SetBuildMode(false);
            return;
        }
        if(!bPanelOpen)UpdateVillageCamera(Delta);
    }
    // In survey mode the builder owns both the cursor and the movement locks.
    if(!VillageCamera&&!bPanelOpen&&(PC->bShowMouseCursor||PC->IsMoveInputIgnored()||PC->IsLookInputIgnored()))
    {SetBuildMode(false);return;}
    FeedbackTime=FMath::Max(0.f,FeedbackTime-Delta);
    if(bPanelOpen||VillageBuildDefense::IsVillageRecipe(SelectedComponent))RefreshVillageConstructionAccess();
    if(bPanelOpen)
    {
        if(Preview)Preview->SetVisibility(false,true);
        if(FoundationPreview)FoundationPreview->SetVisibility(false);
        for(UInstancedStaticMeshComponent* G:{CellGhost,CellCutGhost45,CellCutGhost26L,CellCutGhost26U,CellCutGhostTent})if(G)G->SetVisibility(false);
        HideSiegeRangePreview();
        UpdateWidget();
        return;
    }
    // Bound terrain probes and draft connectivity work independently of FPS.
    // Keep the displayed plan fixed between updates, including its validity.
    // The aim follows the camera every frame; only the expensive branches inside UpdateTarget are
    // throttled, so the ghost no longer lags behind the crosshair.
    UpdateTarget();
    // Gold blink on the snapped neighbour: one vector parameter per frame, nothing else.
    if(AimEdgeMaterial&&AimEdgeComponent&&AimEdgeComponent->IsVisible())
    {
        const float Pulse=.5f+.5f*FMath::Sin(float(GetWorld()->GetTimeSeconds())*5.f);
        // Emissive is around 1.0 in daylight terms, which reads as dull grey against a bright sky;
        // push it into HDR range so the gold stays gold and glows.
        AimEdgeMaterial->SetVectorParameterValue(TEXT("Tint"),FLinearColor(1.f,.74f,.2f)*(1.2f+2.4f*Pulse));
    }
    UpdateWidget();
}

void UVoxelBuildComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(PreviewAssetHandle)PreviewAssetHandle->CancelHandle();
    PreviewAssetHandle.Reset();
    if(SurfaceAssetHandle)SurfaceAssetHandle->CancelHandle();
    SurfaceAssetHandle.Reset();
    SetBuildMode(false);
    // 销毁路径不跑收回动画：HUD 让位必须在控件消失前直接解除，否则三块 HUD 元素会一直缺位。
    if(Widget)Widget->SetHudYielded(false);
    if(PreviewActor)PreviewActor->Destroy();if(Widget)Widget->RemoveFromParent();
    // The preview Actor owns the outline component, so both caches must not outlive it.
    AimEdgeComponent=nullptr;AimEdgeMaterial=nullptr;
    SiegeRangeDecal=nullptr;SiegeRangeMID=nullptr;
    Super::EndPlay(Reason);
}
