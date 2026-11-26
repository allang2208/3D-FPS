#include "VoxelBuildComponent.h"
#include "Camera/CameraActor.h"
#include "Widgets/Text/STextBlock.h"
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
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"

#include "VoxelBuildPlacementPrivate.h"
using namespace VoxelBuildPlacementPrivate;

namespace VoxelBuildPlacementPrivate
{
    // Number row while building: the Nth entry of the palette (materials first, then components).
    int32 NumberKeyIndex(const FKey& Key)
    {
        static const FKey Keys[]={EKeys::One,EKeys::Two,EKeys::Three,EKeys::Four,EKeys::Five,EKeys::Six,EKeys::Seven,EKeys::Eight,EKeys::Nine};
        for(int32 Index=0;Index<UE_ARRAY_COUNT(Keys);++Index)if(Key==Keys[Index])return Index;
        return INDEX_NONE;
    }
}
namespace
{
    FString StrengthText(double Pascal)
    {
        return Pascal>=1000000.?FString::Printf(TEXT("%.1f MPa"),Pascal/1000000.):FString::Printf(TEXT("%.0f kPa"),Pascal/1000.);
    }
    FString MassText(double Kilograms)
    {
        return Kilograms>=1000.?FString::Printf(TEXT("%.1f t"),Kilograms/1000.):FString::Printf(TEXT("%.1f kg"),Kilograms);
    }
    FString SpanText(double Meters,double CapMeters)
    {
        if(Meters<=0.)return TEXT("单格就断");
        return Meters>=CapMeters?FString::Printf(TEXT("≥ %.1f m"),Meters):FString::Printf(TEXT("%.1f m"),Meters);
    }
}

void UVoxelBuildComponent::SetPanelOpen(bool Open)
{
    if(bPanelOpen==Open){SyncVillageCamera();return;}
    bPanelOpen=Open;
    if(Open)RefreshVillageConstructionAccess();
    UE_LOG(LogTemp,Display,TEXT("VOXEL_PANEL SetPanelOpen(%d) active=%d"),Open?1:0,bActive?1:0);
    // Visibility first: Slate cannot focus a collapsed widget.
    if(Widget)Widget->SetDrawerOpen(Open);
    if(auto* PC=Cast<APlayerController>(GetOwner()))
    {
        if(Open)
        {
            if(auto* C=Cast<AFPSGAMECharacter>(PC->GetPawn()))C->SuspendWeaponForMenu();
            // The drawer owns cursor and keyboard; the world keeps running without gameplay input.
            PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);PC->bShowMouseCursor=true;
            FInputModeUIOnly Mode;Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
            if(Widget)Mode.SetWidgetToFocus(Widget->TakeWidget());
            PC->SetInputMode(Mode);
            if(Widget)Widget->SetKeyboardFocus();
        }
        else
        {
            PC->SetIgnoreMoveInput(false);PC->SetIgnoreLookInput(false);
            if(!bActive || !VillageBuildDefense::IsVillageRecipe(SelectedComponent))
            {
                PC->bShowMouseCursor=false;
                PC->SetInputMode(FInputModeGameOnly());
            }
        }
    }
    const bool ResumeSurvey=!Open && VillageCamera!=nullptr;
    SyncVillageCamera();
    if(ResumeSurvey && VillageCamera)SetVillageCursorMode();
    if(Preview)Preview->SetVisibility(false,true);
    if(FoundationPreview)FoundationPreview->SetVisibility(false);
    for(UInstancedStaticMeshComponent* G:{CellGhost,CellCutGhost45,CellCutGhost26L,CellCutGhost26U,CellCutGhostTent})if(G)G->SetVisibility(false);
    ClearAimHighlight(PreviewActor);
    if(bActive)
    {
        if(!Open){PlacementCheckAt=0;TargetUpdateAt=0;UpdateTarget();}
        UpdateWidget();
    }
}

bool UVoxelBuildComponent::HandlePanelKey(const FKey& Key)
{
    if(!Palette)return false;
    if(Key==EKeys::Zero){SelectComponent(NAME_None);return true;}
    const int32 Index=NumberKeyIndex(Key);
    if(Index==INDEX_NONE)return false;
    if(Palette->Materials.IsValidIndex(Index)){SelectMaterial(Palette->Materials[Index].Id);return true;}
    const int32 ComponentIndex=Index-Palette->Materials.Num();
    if(Palette->Components.IsValidIndex(ComponentIndex)){SelectComponentByIndex(ComponentIndex);return true;}
    return false;
}

bool UVoxelBuildComponent::HandleDrawerKey(const FKey& Key)
{
    if(!bPanelOpen)return false;
    if(Key==EKeys::B){SetBuildMode(false);return true;}
    if(Key==EKeys::Escape){SetPanelOpen(false);return true;}
    if(Key==EKeys::Zero){SelectComponent(NAME_None);return true;}
    return false;
}

void UVoxelBuildComponent::MarkDrawerKeyHandled()
{
    DrawerKeyFrame=GFrameCounter;
}

void UVoxelBuildComponent::SelectMaterial(FName Id)
{
    if(Palette&&Palette->Find(Id))
    {
        SelectedMaterial=Id;SelectedComponent=NAME_None;ComponentYaw=0;
        UE_LOG(LogTemp,Display,TEXT("VOXEL_PANEL SelectMaterial %s"),*Id.ToString());
        FeedbackTime=0;TargetUpdateAt=0;PlacementCheckAt=0;
        if(Widget)Widget->SetSelection(SelectedMaterial,SelectedComponent,Brush);
        SetPanelOpen(false);
    }
}

void UVoxelBuildComponent::SelectShape(FName MaterialId,int32 ShapeMode)
{
    // Drawer 其他构造 entry: the material row owns the shape, so both are set in one action.
    if(!Palette||!Palette->Find(MaterialId))return;
    SelectedMaterial=MaterialId;SelectedComponent=NAME_None;ComponentYaw=0;
    Brush=FMath::Clamp(ShapeMode,0,ShapeCount()-1);
    UE_LOG(LogTemp,Display,TEXT("VOXEL_PANEL SelectShape %s shape=%d"),*MaterialId.ToString(),Brush);
    FeedbackTime=0;TargetUpdateAt=0;PlacementCheckAt=0;
    if(Widget)Widget->SetSelection(SelectedMaterial,SelectedComponent,Brush);
    if(bActive)SetPanelOpen(false);
}

void UVoxelBuildComponent::SelectComponent(FName Id)
{
    const auto Required=VillageBuildDefense::RequiredTier(Id);
    if(Required!=VillageBuildDefense::ETier::None && VillageBuildDefense::UnlockedTier(VillageWorld.Get())<Required)
    {
        Feedback=VillageBuildDefense::LockReason(Required);
        FeedbackTime=2.5f;
        bFeedbackValid=false;
        RefreshVillageConstructionAccess();
        return;
    }
    // Selecting a component leaves voxel material selection untouched; 1/2 returns to voxels.
    SelectedComponent=(Palette&&Palette->FindComponent(Id))?Id:NAME_None;
    UE_LOG(LogTemp,Display,TEXT("VOXEL_PANEL SelectComponent 请求=%s 生效=%s"),*Id.ToString(),
        SelectedComponent.IsNone()?TEXT("None"):*SelectedComponent.ToString());
    ComponentYaw=PrefabPlanYaw=GroundYawDegrees=0;DefenseDockPose.Reset();DefenseDockTarget.Reset();AimedPrefab=nullptr;bPrefabValid=false;
    FeedbackTime=0;TargetUpdateAt=0;PlacementCheckAt=0;
    if(Widget)Widget->SetSelection(SelectedMaterial,SelectedComponent,Brush);
    if(bActive)SetPanelOpen(false);
}

void UVoxelBuildComponent::RefreshVillageConstructionAccess()
{
    const auto Tier=VillageBuildDefense::UnlockedTier(VillageWorld.Get());
    if(Widget)Widget->SetVillageConstructionTier(Tier);
    if(Tier>=VillageBuildDefense::RequiredTier(SelectedComponent))return;
    SelectedComponent=NAME_None;
    SyncVillageCamera();
    ComponentYaw=0;
    AimedPrefab=nullptr;
    bPrefabValid=false;
    TargetUpdateAt=PlacementCheckAt=0;
    if(Widget)Widget->SetSelection(SelectedMaterial,SelectedComponent,Brush);
    if(bActive&&!bPanelOpen)SetPanelOpen(true);
}

void UVoxelBuildComponent::SelectComponentByIndex(int32 Index)
{
    if(!Palette||!Palette->Components.IsValidIndex(Index))return;
    SelectComponent(Palette->Components[Index].Id);
}

const FVoxelBuildPrefab* UVoxelBuildComponent::SelectedPrefab() const
{
    return (Palette&&!SelectedComponent.IsNone())?Palette->FindComponent(SelectedComponent):nullptr;
}

void UVoxelBuildComponent::PushPanelContent()
{
    if(!Widget||!Palette)return;
    TArray<FVoxelBuildPanelCard> Materials,Components;
    for(const FVoxelBuildMaterial& Entry:Palette->Materials)
    {
        if(Entry.Id.IsNone())continue;
        const FVoxelPhysicalMaterial Physics=Palette->Physical(Entry.Id);
        VoxelJointStrength::FMaterial Joint;
        Joint.DensityKgM3=Physics.DensityKgM3;Joint.CompressionPa=Physics.CompressionPa;
        Joint.TensionPa=Physics.TensionPa;Joint.ShearPa=Physics.ShearPa;
        // Offline-verified numbers from the same header Tools/Building/voxel_stress_probe.cpp uses.
        // Sweep long enough to reach the real limit after the 2026-09-16 strength doubling (wood
        // 4.4 m / stone 4.0 m); the probe scans the same 25 cells.
        constexpr int32 SpanSweepCells=25;
        const double SpanSelf=VoxelJointStrength::MaxSpanMeters(Joint,0.,SpanSweepCells);
        const double SpanLoaded=VoxelJointStrength::MaxSpanMeters(Joint,100.,SpanSweepCells);
        const double CellAreaM2=0.04;
        const double CellLoadT=Physics.CompressionPa*CellAreaM2/9.81/1000.;
        FVoxelBuildPanelCard Card;
        Card.Id=Entry.Id;
        Card.Caption=Entry.DisplayName.IsEmpty()?Entry.Id.ToString():Entry.DisplayName.ToString();
        Card.Detail=TEXT("20 cm");
        Card.bComponent=false;
        Card.Subtitle=FString::Printf(TEXT("体素 · %s · 20 cm 立方"),*Card.Caption);
        Card.Rows.Add({TEXT("物理参数"),TEXT("")});
        Card.Rows.Add({TEXT("密度"),FString::Printf(TEXT("%.0f kg/m³"),Physics.DensityKgM3)});
        Card.Rows.Add({TEXT("单格质量"),FString::Printf(TEXT("%s（20×20×20 cm）"),*MassText(Joint.MassPerCellKg()))});
        Card.Rows.Add({TEXT("抗压"),StrengthText(Physics.CompressionPa)});
        Card.Rows.Add({TEXT("抗拉"),StrengthText(Physics.TensionPa)});
        Card.Rows.Add({TEXT("抗剪"),StrengthText(Physics.ShearPa)});
        Card.Rows.Add({TEXT("耐久 / 单点冲击"),FString::Printf(TEXT("%.0f / %.0f J"),Physics.Durability,Physics.JoulesPerDamage)});
        Card.Rows.Add({TEXT("建造能力"),TEXT("")});
        Card.Rows.Add({TEXT("保证净跨"),TEXT("2.0 m")});
        Card.Rows.Add({TEXT("最长挑空（自重）"),SpanText(SpanSelf,SpanSweepCells*0.2)});
        Card.Rows.Add({TEXT("最长挑空（跨中站人）"),SpanText(SpanLoaded,SpanSweepCells*0.2)});
        Card.Rows.Add({TEXT("每平方米承重"),FString::Printf(TEXT("%s/m²"),*MassText(Joint.LoadPerSquareMeterT()*1000.))});
        Card.Rows.Add({TEXT("单格承重（20×20 cm 面）"),MassText(CellLoadT*1000.)});
        for(const auto& Row:Card.Rows)if(!Row.Value.IsEmpty())Card.NumericRows.Add(Row.Key);
        Card.bExpandable=true;
        Card.Note=TEXT("跨度数值按当前材质强度和标准布置估算，实际承重还取决于形状、载荷与支撑。接缝超限或失去地基连接会倒塌。右侧「其他构造」展开该分类的体素形状与构件。");
        // The drawer draws this material's shapes with the same 20 cm block the player places.
        Card.IconMesh=Entry.ExampleMesh;
        if(Card.IconMesh.IsNull())
            Card.IconMesh=TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(Entry.Id==TEXT("wood")
                ?TEXT("/Game/Building/Voxels/Rounded/SM_Voxel20_Wood.SM_Voxel20_Wood")
                :TEXT("/Game/Building/Voxels/Rounded/SM_Voxel20_Stone.SM_Voxel20_Stone")));
        Card.IconSurface=Entry.Surface;
        Materials.Add(MoveTemp(Card));
    }
    // The drawer lists these under every material row, so a shape entry is only ever picked together
    // with the material that owns it (SelectShape).
    TArray<FVoxelBuildPanelCard> Shapes;
    for(int32 Index=0;Index<ShapeCount();++Index)
    {
        const FIntVector Cells=ShapeSize(Index);
        FVoxelBuildPanelCard Card;
        Card.Id=FName(*FString::Printf(TEXT("shape_%d"),Index));
        Card.Caption=ShapeName(Index);
        Card.Detail=FString::Printf(TEXT("%d×%d×%d"),Cells.X*20,Cells.Y*20,Cells.Z*20);
        Card.ShapeMode=Index;
        // 2026-10-14：屋顶阶梯族用格子生成器出真实排列（占格数/图标同步真实值），
        // Box 形状保持包围盒实心填充——两条路径都走 ShapeCells 统一真源。
        ShapeCells(Index,false,Card.IconCells);
        Card.Subtitle=TEXT("体素构造 · 20 cm 格吸附");
        Card.Rows.Add({TEXT("尺寸"),FString::Printf(TEXT("%d × %d × %d cm"),Cells.X*20,Cells.Y*20,Cells.Z*20)});
        Card.Rows.Add({TEXT("20 cm 占格"),FString::Printf(TEXT("%d × %d × %d"),Cells.X,Cells.Y,Cells.Z)});
        Card.Rows.Add({TEXT("占格数"),FString::Printf(TEXT("%d 格"),Card.IconCells.Num())});
        Card.Rows.Add({TEXT("旋转（R）"),ShapeSize(Index,true)==Cells?TEXT("尺寸不变"):TEXT("交换 X／Y")});
        Card.NumericRows={TEXT("尺寸"),TEXT("20 cm 占格"),TEXT("占格数")};
        Card.Note=Index==0?TEXT("与滚轮顺序一致：单格 → 地块/墙面/直线 → 45°屋面坡 → 26°屋面坡 → 山墙三角 → 金字塔顶。体素按 20 cm 格放置，参与承重与倒塌。"):
            !ShapeIsStaircase(Index)?
            TEXT("形状与材质一起选中：点这一条就用该材质放这个形状。放置、拆除、承重和存档与单格体素完全相同。"):
            TEXT("一层薄壳：45°坡刷只放坡面顶格（1×5=5格，2×5=10格），低边/檐口锚在瞄准格，R 键换四个坡向；瞄准已放好的坡面再放会沿同一平面续接，顶格之间按 20×20 共面坡棱接缝承重。单层切割在台阶处有固有可见缝隙，要绝对无缝请用实心补结构或薄板构件；26°/山墙/金字塔仍是实心+顶格切割。");
        Shapes.Add(MoveTemp(Card));
    }
    for(const FVoxelBuildPrefab& Entry:Palette->Components)
    {
        if(Entry.Id.IsNone())continue;
        FVoxelBuildPanelCard Card;
        Card.Id=Entry.Id;
        Card.Caption=Entry.DisplayName.IsEmpty()?Entry.Id.ToString():Entry.DisplayName.ToString();
        Card.Detail=FString::Printf(TEXT("%d × %d × %d cm"),Entry.Footprint.X*20,Entry.Footprint.Y*20,Entry.Footprint.Z*20);
        Card.bComponent=true;
        const FVoxelBuildMaterial* Group=Entry.Material.IsNone()?nullptr:Palette->Find(Entry.Material);
        Card.MaterialId=Group?Group->Id:NAME_None;
        Card.IconMesh=Entry.Mesh;Card.IconSurface=Entry.Surface;Card.IconPivotOffsetCm=Entry.PivotOffsetCm;
        Card.IconActorClass=Entry.ActorClass;
        const bool bWall=Entry.Mount==EVoxelPrefabMount::Wall;
        Card.Subtitle=bWall?TEXT("壁挂构件 · 贴合竖直表面"):TEXT("构件 · 20 cm 格吸附");
        const bool bVillage=VillageBuildDefense::IsVillageRecipe(Entry.Id);
        const bool bWallStairs=Entry.Id==VillageWallStairs::Id;
        Card.Rows.Add({TEXT("归属构造"),bVillage?FString(TEXT("村庄建筑")):
            Group?(Group->DisplayName.IsEmpty()?Group->Id.ToString():Group->DisplayName.ToString()):FString(TEXT("其他（未归类）"))});
        Card.Rows.Add({TEXT("占格尺寸"),Card.Detail});
        Card.Rows.Add({TEXT("20 cm 占格"),FString::Printf(TEXT("%d × %d × %d"),Entry.Footprint.X,Entry.Footprint.Y,Entry.Footprint.Z)});
        Card.Rows.Add({TEXT("放置方式"),bWallStairs?TEXT("地面放置或对接高墙步道"):
            VillageWallStairs::CanDock(Entry.Id)?TEXT("落地或吸附至城防接口"):
            bWall?TEXT("壁挂 · 朝向跟随墙面"):TEXT("表面放置 · 可切换吸附")});
        Card.NumericRows={TEXT("占格尺寸"),TEXT("20 cm 占格")};
        Card.Note=bWall?TEXT("只能贴在墙、柱等竖直表面，右键拆除。壁挂件不参与失去地面支撑后的脱落计算。"):
            TEXT("R 旋转 90°，右键拆除。构件不按体素接缝计算承重，可为相邻体素提供支撑；失去支撑后会脱落。占格尺寸表示放置范围，缩略图展示构件外观。");
        if(bVillage)
        {
            Card.Rows.Add({TEXT("解锁条件"),VillageBuildDefense::ProjectName(VillageBuildDefense::RequiredTier(Entry.Id))});
            Card.Rows.Add({TEXT("施工视角"),TEXT("选择后进入俯视。空格切换角度，鼠标靠边平移。")});
            if(bWallStairs)
            {
                Card.Subtitle=TEXT("村庄城防 · 折返石阶");
                Card.Note=TEXT("沿平台折返登上 3.6 米步道。地面滚轮每格旋转 1°。瞄准完好高墙内侧时，用滚轮选择平台的对接边。");
            }
            else if(Entry.Id==VillageBuildDefense::HighWall)
            {
                Card.Subtitle=TEXT("村庄城防 · 带城垛的石墙");
                Card.Note=TEXT("地面滚轮每格旋转 1°。墙端可对接高墙、石城门或高塔楼。吸附时滚轮切换接法。步道朝村内，可接城墙石阶。");
            }
            else if(Entry.Id==VillageBuildDefense::OilPot)
            {
                Card.Subtitle=TEXT("村庄城防 · 热油锅");
                Card.Note=TEXT("可在平地、塔顶或城门平台建造。按 E 取油，左键向前方 3 米泼洒。热油持续 10 秒，范围 5 米，友军和自己也会受伤。");
            }
            else if(Entry.Id==VillageBuildDefense::Ballista)
            {
                Card.Subtitle=TEXT("村庄城防 · 固定式弩炮");
                Card.Note=TEXT("可在塔顶、城门平台或平地建造。弩炮可水平旋转 360° 自动索敌，靠近按 E 可手动瞄准。");
            }
            else if(Entry.Id==VillageBuildDefense::Trebuchet)
            {
                Card.Subtitle=TEXT("村庄城防 · 配重投石机");
                Card.Note=TEXT("可部署在平地或足够宽的塔顶、城门平台。底架须避开楼梯口，后方和上方须留出投臂摆动空间。滚轮调整朝向。");
            }
            else if(Entry.Id==VillageBuildDefense::HighTower)
            {
                Card.Subtitle=TEXT("村庄城防 · 方形高塔楼");
                Card.Note=TEXT("把塔楼移近高墙端部，或靠近连续高墙的村内一侧，塔门会平接 3.6 米步道。滚轮可换向，F 可切换自由放置。");
            }
            else if(Entry.Id==VillageBuildDefense::StoneGate)
            {
                Card.Subtitle=TEXT("村庄城防 · 石拱门与升降铁闸");
                Card.Note=TEXT("门洞净宽 6.6 米，按 E 升降铁闸。二层守卫平台连通两侧墙顶，城墙石阶可另接在内侧。");
            }
            else if(Entry.Id==VillageBuildDefense::WoodGate)
            {
                Card.Subtitle=TEXT("村庄城防 · 双扇木门");
                Card.Note=TEXT("地面滚轮每格旋转 1°。两扇木门向两侧开启，放置时请留足摆动空间。");
            }
            else
            {
                Card.Subtitle=TEXT("村庄城防 · 砌石墙段");
                Card.Note=TEXT("地面滚轮每格旋转 1°。沿边界连续放置墙段，留出大门的通行位置。");
            }
        }
        if(Entry.Id==TEXT("campfire"))
        {
            Card.Subtitle=TEXT("篝火 · 添柴取暖与烧烤");
            Card.Rows.Add({TEXT("生效半径"),TEXT("5 m")});
            Card.Rows.Add({TEXT("饥饿自然消耗"),TEXT("−50%")});
            Card.Rows.Add({TEXT("水分自然消耗"),TEXT("−50%")});
            Card.NumericRows.Add(TEXT("生效半径"));
            Card.NumericRows.Add(TEXT("饥饿自然消耗"));
            Card.NumericRows.Add(TEXT("水分自然消耗"));
            Card.Note=TEXT("E 打开篝火面板，添加木材后持续燃烧；燃烧时范围内所有玩家生效，燃尽或离开失效，多个篝火不叠加。不恢复饥饿或水分，也不减免相关伤害。R 旋转，右键拆除。");
        }
        Components.Add(MoveTemp(Card));
    }
    Widget->SetContent(Materials,Shapes,Components);
    Widget->SetSelection(SelectedMaterial,SelectedComponent,Brush);
}

void UVoxelBuildComponent::UpdateWidget()
{
    if(!Widget||!Palette||!BuildWorld)return;
    // 审计 U1（2026-09-23）：签名前移到生产端。消费端 ShowState 的守卫只挡 SetText，而这里
    // 每帧无条件构造 Message/Headline/Brush（4–8 次 Printf + 堆分配），面板收起的建造态照跑。
    // 廉价分量拼键；消息文本本身也进签名（一次 GetTypeHash，无 Printf）：ValidatePlacement 会在
    // 同一 Revision 下改写 TargetMessage（如"可放置 N 格"计数变化），漏了就会显示陈旧状态行。
    // FeedbackTime 的衰减不入键——它的可见效果只有"Feedback 顶替 LiveMessage"这一个边沿。
    const FString& LiveMessage=SelectedPrefab()?PrefabMessage:TargetMessage;
    // Placement 的**内容**（格数 + 首格坐标）必须入键：幽灵行的"第 N 层 格(x,y,z)"随瞄准移动，
    // 而 Revision 不变——只记 IsEmpty 会让状态行冻结在旧落点（审计 U1 自检发现）。
    // 位域：flags 0..4，Clipped 5..8，Brush 9..12，HasComp 13，Material 14..25，Yaw 26..27，
    // PrefabMode 28，GrowUp 29，PlacementNum 30..39，CellHash 40..55。
    const FIntVector SignalCell=Placement.IsEmpty()?FIntVector::ZeroValue:Placement[0];
    const uint64 CellHash=(uint64)GetTypeHash(SignalCell)&0xFFFF;   // 16 bit 足够区分相邻列
    const bool bDocked=!SelectedComponent.IsNone()&&DefenseDockPose.IsSet();
    const int32 GroundYaw=PlannedGroundYaw();
    const int32 ShownYaw=bDocked?FMath::RoundToInt(FRotator::ClampAxis(DefenseDockPose->Rotator().Yaw))%360:
        (GroundYaw!=INDEX_NONE?GroundYaw:PrefabPlanYaw*90);
    const uint64 CheapKey=(uint64)(bCanPlace?1:0)|(uint64)(bPrefabValid?2:0)|(uint64)(bSnapEnabled?4:0)
        |(uint64)(ClippedPlayerCells&0xF)<<5|(uint64)(Brush&0xF)<<9
        |(uint64)(SelectedComponent.IsNone()?0:1)<<13
        |((uint64)(GetTypeHash(SelectedMaterial)&0xFFF))<<14
        |(uint64)(PrefabPlanYaw&3)<<26|(uint64)(SelectedPrefab()?1:0)<<28
        |(uint64)(GrowUpPlan?1:0)<<29|(uint64)(Placement.Num()&0x3FF)<<30|CellHash<<40
        |(uint64)bDocked<<56|(uint64)bPanelOpen<<57|(uint64)bVillageVertical<<58;
    const FString Signal=FeedbackTime>0?Feedback:LiveMessage;
    // StructureStatus 的过渡态（正在保存/正在计算/倒塌处理中）不随 Revision 变化，必须入键，
    // 否则状态行会在整个过渡期冻结。世界侧用 StatusFingerprint() 把这些内部标志折成 uint64；
    // WeakestJointSummary 文本哈希覆盖"同 Revision 下最弱接缝读数变了"的情况（一次 GetTypeHash）。
    // JointBits 与 Signal 哈希各占 12 bit、彼此错开，避免移位丢位。
    const uint64 JointBits=(uint64)GetTypeHash(BuildWorld->WeakestJointSummary())&0xFFF;
    const uint64 SignalBits=(uint64)GetTypeHash(Signal)&0xFFF;
    // 位域：Revision 0..31，StatusFingerprint 32..39，JointBits 40..51，SignalBits 52..63。
    const uint64 Revision=((BuildWorld->StructureRevision()&0xFFFFFFFFull)
        |((BuildWorld->StatusFingerprint()&0xFFull)<<32))
        |(JointBits<<40)|(SignalBits<<52);
    const uint64 LayoutKey=CheapKey^GetTypeHash(SelectedComponent)^(uint64(ShownYaw)<<46);
    if(LayoutKey==LastWidgetCheapKey&&Revision==LastWidgetRevision)
    {
        UpdateStructureWarning(*BuildWorld);   // 播报状态机自己带边沿守卫，保持每帧
        return;
    }
    LastWidgetCheapKey=LayoutKey;LastWidgetRevision=Revision;
    if(IsVillageCameraPlacing() && VillageCameraCaption)
    {
        if(const auto* Piece=SelectedPrefab())
        {
            const FString Status=FString::Printf(TEXT("%s　·　%s　·　朝向 %d°　·　%s\n%s\n空格 切换视角　·　鼠标靠边 平移　·　滚轮 旋转　·　左键 放置　·　Esc 退出"),
                *Piece->DisplayName.ToString(),bVillageVertical?TEXT("垂直俯视"):TEXT("45° 俯视"),ShownYaw,
                bSnapEnabled?TEXT("吸附开"):TEXT("吸附关"),*Signal);
            VillageCameraCaption->SetText(FText::FromString(Status));
        }
    }
    Widget->SetSelection(SelectedMaterial,SelectedComponent,Brush);
    UpdateStructureWarning(*BuildWorld);
    if(bPanelOpen)
    {
        FString Current;
        if(const auto* Piece=SelectedPrefab())
            Current=Piece->DisplayName.IsEmpty()?Piece->Id.ToString():Piece->DisplayName.ToString();
        else if(const auto* Material=Palette->Find(SelectedMaterial))
        {
            const FString Name=Material->DisplayName.IsEmpty()?Material->Id.ToString():Material->DisplayName.ToString();
            Current=FString::Printf(TEXT("%s · %s"),*Name,ShapeName(Brush));
        }
        Widget->ShowState(FString(),Current,FString(),true,bSnapEnabled,
            BuildWorld->WeakestJointRatio(),BuildWorld->WeakestJointSummary());
        return;
    }
    const FString ClipNote=ClippedPlayerCells>0?FString::Printf(TEXT(" · 已跳过 %d 格（角色所在位置）"),ClippedPlayerCells):FString();
    const FString Message=(FeedbackTime>0?Feedback:(SelectedPrefab()?PrefabMessage:TargetMessage))+ClipNote+TEXT("\n")+BuildWorld->StructureStatus();
    if(const FVoxelBuildPrefab* Prefab=SelectedPrefab())
    {
        const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Prefab->Footprint,PrefabPlanYaw);
        Widget->ShowState(FString::Printf(TEXT("%s · 构件 %d 件 · 体素 %d 格"),*Prefab->DisplayName.ToString(),BuildWorld->PrefabCount(),BuildWorld->BlockCount()),
            bDocked?FString::Printf(TEXT("%s · %d° · 滚轮调向"),SelectedComponent==VillageWallStairs::Id?TEXT("平台已对齐步道"):TEXT("城防接口已对齐"),ShownYaw):
                FString::Printf(TEXT("构件 · %d × %d × %d cm · %d°"),Footprint.X*20,Footprint.Y*20,Footprint.Z*20,ShownYaw),
            Message,FeedbackTime>0?bFeedbackValid:bPrefabValid,bSnapEnabled,
            BuildWorld->WeakestJointRatio(),BuildWorld->WeakestJointSummary());
        return;
    }
    const auto* Entry=Palette->Find(SelectedMaterial);const FIntVector Size=BrushSize()*20;
    const FString Name=Entry?Entry->DisplayName.ToString():SelectedMaterial.ToString();
    const TCHAR* Shape=ShapeName(Brush);
    // Where the plan actually lands: layer index and cell, so upward building is unambiguous.
    const FIntVector FirstCell=Placement.IsEmpty()?FIntVector::ZeroValue:Placement[0];
    const FString Where=Placement.IsEmpty()?FString():
        FString::Printf(TEXT(" · 第 %d 层 格(%d,%d,%d)"),FirstCell.Z+1,FirstCell.X,FirstCell.Y,FirstCell.Z);
    Widget->ShowState(FString::Printf(TEXT("%s · 已建造 %d 格"),*Name,BuildWorld->BlockCount()),
        FString::Printf(TEXT("%s · %d × %d × %d cm%s"),Shape,Size.X,Size.Y,Size.Z,*Where),
        Message,FeedbackTime>0?bFeedbackValid:bCanPlace,bSnapEnabled,
        BuildWorld->WeakestJointRatio(),BuildWorld->WeakestJointSummary());
}

void UVoxelBuildComponent::UpdateStructureWarning(AVoxelBuildWorld& World)
{
    const float Risk=World.WeakestJointRatio();
    // Below the warning line the warning re-arms, so a structure that recovers can warn again while a
    // structure that simply sits at the limit does not spam the notice bar.
    if(Risk<.8f){NoticeRisk=0;return;}
    if(Risk<.85f)return;
    // 审计 P11：下面只会有一个分支真正播报（NoticeRisk 是上一次的读数，跨阈值才触发）。
    // 原实现无条件先构造 WeakestJointSummary()（一次 FString::Printf），在 Risk 长期停留在
    // 85%–100% 的结构上等于每帧白构造一次字符串。先判是否真的会播报。
    // 注意保持原语义：Model 缺失时也要更新 NoticeRisk（否则每帧重进本函数、等于每次都重算）。
    const bool bBreak=Risk>=1.f&&NoticeRisk<1.f;
    const bool bWarn=Risk<1.f&&NoticeRisk<.85f;
    if(bBreak||bWarn)
    {
        if(auto* Model=GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr)
        {
            const FString Summary=World.WeakestJointSummary();
            const FString Detail=Summary.IsEmpty()?FString::Printf(TEXT("%.0f%%"),Risk*100.):Summary;
            Model->PostNotice(bBreak?TEXT("结构超限"):TEXT("结构预警"),
                bBreak?Detail+FString(TEXT(" · 接缝正在断裂")):Detail+FString(TEXT(" · 加厚或补支撑")),FString(),3.2f);
        }
    }
    NoticeRisk=Risk;
}

