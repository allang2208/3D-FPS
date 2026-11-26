#include "VoxelBuildComponent.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "VoxelBuildDebug.h"
#include "../WorldGeneration/VillageDefenseRepairTargets.h"
#include "Camera/CameraTypes.h"
#include "Camera/PlayerCameraManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "VoxelCollapseFragment.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildPrefabActor.h"
#include "VillageBuildDefense.h"
#include "VillageGateReplacement.h"
#include "VoxelBuildWidget.h"
#include "VoxelJointStrength.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/VillageDefenseSection.h"
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

void UVoxelBuildComponent::RefreshPlacementInput()
{
    FeedbackTime=0;
    PlacementCheckAt=0;
    TargetUpdateAt=0;
    UpdateTarget();
}

bool UVoxelBuildComponent::HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen)
{
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC)return false;
    const FKey Key=Event.Key;const bool Pressed=Event.Event==IE_Pressed;
    // Other menus still end building; our own drawer keeps the cursor and stays open.
    if(bMenuOpen)
    {
        UE_LOG(LogTemp,Display,TEXT("VOXEL_PANEL 建造输入被其它菜单挡住 key=%s active=%d panel=%d"),
            *Key.ToString(),bActive?1:0,bPanelOpen?1:0);
        if(bActive)SetBuildMode(false);
        return false;
    }
    if(!VillageCamera&&!bPanelOpen&&(PC->bShowMouseCursor||PC->IsMoveInputIgnored()||PC->IsLookInputIgnored()))
    {
        // 画面里没有别的菜单时，光标/输入锁只可能来自退出不干净的界面；先清干净再让建造继续，
        // 否则 SetBuildMode(true) 的守卫会静默拒绝，表现为"按 B 打不开面板、数字键也换不了料"。
        // 只在建造自己消费的键上清（B/数字键/滚轮）：其它系统若合法持有这些锁
        // （过场、脚本化视角等），建造路径之外的按键不把它们踩掉。
        const bool bBuildOwnedKey=Key==EKeys::B||Key==EKeys::Zero||NumberKeyIndex(Key)!=INDEX_NONE
            ||Key==EKeys::MouseScrollUp||Key==EKeys::MouseScrollDown;
        if(!bBuildOwnedKey)return false;
        UE_LOG(LogTemp,Display,TEXT("VOXEL_PANEL 检测到残留输入锁 cursor=%d move=%d look=%d active=%d panel=%d key=%s"),
            PC->bShowMouseCursor?1:0,PC->IsMoveInputIgnored()?1:0,PC->IsLookInputIgnored()?1:0,
            bActive?1:0,bPanelOpen?1:0,*Key.ToString());
        PC->SetIgnoreMoveInput(false);PC->SetIgnoreLookInput(false);PC->bShowMouseCursor=false;
        PC->SetInputMode(FInputModeGameOnly());
    }
    // A key the focused drawer widget already handled must not run twice in the same frame.
    const bool bDrawerHandled=GFrameCounter==DrawerKeyFrame;
    if(Key==EKeys::B)
    {
        if(Pressed&&!bDrawerHandled)
        {
            if(!bActive)SetBuildMode(true);          // enter building, drawer open
            else if(bPanelOpen)SetBuildMode(false);  // second B in the drawer: leave building
            else SetPanelOpen(true);                 // back to the drawer from placing
            UE_LOG(LogTemp,Display,TEXT("VOXEL_PANEL B 键 active=%d panel=%d 处理过=%d"),
                bActive?1:0,bPanelOpen?1:0,bDrawerHandled?1:0);
        }
        return true;
    }
    if(!bActive)return false;
    if(Key==EKeys::Escape)
    {
        if(Pressed&&!bDrawerHandled){if(bPanelOpen)SetPanelOpen(false);else SetBuildMode(false);}
        return true;
    }
    if(Pressed&&(Key==EKeys::Tab||Key==EKeys::K||Key==EKeys::J||Key==EKeys::F6||Key==EKeys::LeftAlt))
    {SetBuildMode(false);return false;}
    // The drawer numbers its own visible rows (a 其他构造 submenu shifts them), so a key it already
    // consumed this frame must not also run the palette-order shortcut. While the drawer owns the
    // cursor, 1-9／0 belong to its widget alone: a press the widget did not see is swallowed
    // instead of falling back to palette order, which used to pick an entry the current category
    // was not showing and start building with it (2026-09-19 审计)。建造态（面板收起）仍按调色板
    // 顺序快捷选择。
    if(Pressed&&!bDrawerHandled)
    {
        const bool bNumberKey=NumberKeyIndex(Key)!=INDEX_NONE||Key==EKeys::Zero;
        if(bPanelOpen)
        {
            if(bNumberKey)return true;
        }
        else if(HandlePanelKey(Key))return true;
    }
    // Placement commands belong to the aiming state; the drawer does not move or build.
    if(bPanelOpen)return false;
    if(IsVillageCameraPlacing() && Key==EKeys::SpaceBar)
    {
        if(Pressed)
        {
            bVillageVertical=!bVillageVertical;
            PositionVillageCamera();
            PC->PlayerCameraManager->UpdateCamera(0.f);
            RefreshPlacementInput();
        }
        return true;
    }
    const bool bWheel=Key==EKeys::MouseScrollUp||Key==EKeys::MouseScrollDown;
    if(bWheel||Key==EKeys::R)
    {
        if(Pressed)
        {
            const int32 Step=Key==EKeys::MouseScrollDown?-1:1;
            if(const FVoxelBuildPrefab* Piece=SelectedPrefab())
            {
                if(PlannedGroundYaw()!=INDEX_NONE)
                {
                    const int32 Degrees=bWheel?Step:90;
                    GroundYawDegrees=(GroundYawDegrees+Degrees+360)%360;
                }
                else if(Piece->Mount!=EVoxelPrefabMount::Wall)ComponentYaw=(ComponentYaw+Step+4)%4;
            }
            else if(bWheel)Brush=(Brush+Step+ShapeCount())%ShapeCount();
            else BrushRotation=(BrushRotation+1)&3;
            RefreshPlacementInput();
        }
        return true;
    }
    if(Key==EKeys::F){if(Pressed){bSnapEnabled=!bSnapEnabled;RefreshPlacementInput();}return true;}
    if(Key==EKeys::LeftControl||Key==EKeys::RightControl)
    {bUndoModifier=Event.Event!=IE_Released;return true;}
    if(Key==EKeys::Z&&bUndoModifier)
    {
        if(Pressed)
        {
            // 撤销 = 拆除最后一**批**放置：方块按拆除规则回收（进背包，溢出掉脚下），不再恢复旧方块。
            if(GetNetMode()!=NM_Standalone)
            {FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Building;R.Mode=TEXT("undo");
             if(auto* PS=PC->GetPlayerState<AColdSteelPlayerState>())PS->RequestInventoryAction(R);return true;}
            TMap<FName,int32> Removed;
            bFeedbackValid=BuildWorld->Undo(&Removed);
            if(bFeedbackValid)GrantDismantledBlocks(Removed);
            Feedback=BuildWorld->ResultMessage();FeedbackTime=2;
        }
        return true;
    }
    if(Key==EKeys::MiddleMouseButton)
    {
        if(!Pressed)return true;
        const auto* Piece=Cast<AVoxelBuildPrefabActor>(AimedPrefab.Get());
        if(Piece&&Piece->GetOwner()==BuildWorld&&!Piece->IsFalling()&&VillageBuildDefense::IsVillageRecipe(Piece->PrefabId()))
        {
            const FName Id=Piece->PrefabId();
            SelectComponent(Id);
            if(SelectedComponent==Id&&VillageBuildDefense::UnlockedTier(VillageWorld.Get())>=VillageBuildDefense::RequiredTier(Id))
            {
                GroundYawDegrees=FMath::RoundToInt(FRotator::ClampAxis(Piece->GetActorRotation().Yaw))%360;
                RefreshPlacementInput();
            }
        }
        else if(!IsVillageCameraPlacing()&&!Removal.IsEmpty())SelectMaterial(BuildWorld->VolumeMaterialAt(HitCell.Volume,HitCell.Cell));
        return true;
    }
    if(Key==EKeys::LeftMouseButton||Key==EKeys::RightMouseButton)
    {
        if(Pressed)
        {
            auto* RemovalTarget=Cast<AVoxelBuildPrefabActor>(AimedPrefab.Get());
            if(Key==EKeys::RightMouseButton)
            {
                // A collapsed player-built piece keeps its footprint but has no collision to aim at.
                const AVillageDefenseSection* Breach=nullptr;
                if(IsVillageCameraPlacing())
                {
                    FVector Eye,Ray;
                    if(VillageCursorRay(Eye,Ray))
                    {
                        const FVector End=Hit.bBlockingHit?Hit.ImpactPoint:Eye+Ray*VillageBuildDefense::SurveyTraceLength;
                        if(auto* Ruins=GetWorld()->GetSubsystem<UVillageDefenseRepairTargets>())
                            Breach=Ruins->Trace(*PC->GetPawn(),Eye,End,nullptr,FVector::Distance(Eye,End));
                    }
                }
                else Breach=Cast<AVillageDefenseSection>(ColdSteelWorldInteraction::TraceUseTargets(PC).Target);
                if(Breach && Breach->GetHealth()<=0.f)
                    if(auto* Placed=Cast<AVoxelBuildPrefabActor>(Breach->GetAttachParentActor()))
                        RemovalTarget=Placed;
                if(IsVillageCameraPlacing() && (!RemovalTarget || !VillageBuildDefense::IsVillageRecipe(RemovalTarget->PrefabId()) ||
                    !VillageBuildDefense::InSurveyRange(PC->GetPawn()->GetPawnViewLocation(),RemovalTarget->GetActorLocation())))
                {
                    Feedback=TEXT("请指向施工范围内已建造的村庄建筑");bFeedbackValid=false;FeedbackTime=2;
                    return true;
                }
            }
            if(GetNetMode()!=NM_Standalone)
            {
                FColdSteelInventoryRequest R;R.Action=EColdSteelInventoryAction::Building;
                R.ContainerRevision=int64(BuildWorld->StructureRevision());
                if(Key==EKeys::LeftMouseButton)
                {
                    if(const auto* P=SelectedPrefab())
                    {
                        if(!bPrefabValid)return true;
                        R.Mode=DefenseDockPose.IsSet()?TEXT("wallDockPrefab"):TEXT("prefab");
                        if(DefenseDockSocket==VillageGateReplacement::ReplacementSocket)
                        {
                            R.Mode=TEXT("replaceWallGate");
                            R.Count=WallCutSelection;
                        }
                        R.Definition=P->Id;R.Anchor=PrefabCell;R.Orientation=PrefabPlanYaw;
                        const int32 GroundYaw=PlannedGroundYaw();
                        if(GroundYaw!=INDEX_NONE)
                        {
                            R.Mode=TEXT("groundDefensePrefab");
                            R.Orientation=GroundYaw;
                        }
                        R.Target=DefenseDockTarget.Get();
                        if(DefenseDockPose.IsSet())R.Cell=DefenseDockSocket;
                    }
                    else {if(!bCanPlace)return true;R.Mode=bPlacementSnap?TEXT("place"):TEXT("free");R.Definition=PlacementMaterial;R.Volume=PlacementVolume;R.Origin=PlacementOrigin;R.Cells=Placement;
                        // 2026-10-17：切割随事务上行（吸附放置的世界格子才带；自由体积不切割）。
                        if(bPlacementSnap&&!PlacementVolume.IsValid())R.CellShapes=PlacementCuts;}
                }
                else if(RemovalTarget){R.Mode=TEXT("removePrefab");R.Target=RemovalTarget;R.Anchor=RemovalTarget->AnchorCell();}
                else if(!Removal.IsEmpty()){R.Mode=TEXT("remove");R.Volume=HitCell.Volume;R.Cells=Removal;}
                else {R.Mode=TEXT("debris");R.Target=Hit.GetActor();}
                if(auto* PS=PC->GetPlayerState<AColdSteelPlayerState>())PS->RequestInventoryAction(R);
                return true;
            }
            // Input runs before the next camera/preview tick. Recasting here
            // would commit an unseen target. The world revalidates this exact
            // displayed plan without changing its origin or cells.
            if(Key==EKeys::LeftMouseButton)
            {
                if(SelectedPrefab())PlacePrefab();
                else if(bCanPlace)
                {
                    // 2026-09-16：建造消耗体素块（背包优先、仓库兜底）。先扣料再提交，提交失败立刻退回。
                    const int32 Cost=Placement.Num();
                    if(!ConsumePlacementBlocks(PlacementMaterial,Cost)){bFeedbackValid=false;Feedback=BlockMessage;FeedbackTime=2.5f;}
                    else
                    {
                        // 2026-10-15：世界格子的吸附放置带楔形切割（地基柱等后附格按 0 补齐）；
                        // 自由体积放置不切割，走原路。
                        if(bPlacementSnap&&!PlacementVolume.IsValid()&&PlacementCuts.Num()>0)
                        {
                            TArray<uint8> Shapes=PlacementCuts;
                            if(Shapes.Num()<Placement.Num())Shapes.SetNumZeroed(Placement.Num());
                            else if(Shapes.Num()>Placement.Num())Shapes.SetNum(Placement.Num());
                            {
                                int32 NZ=0;for(const uint8 C:Shapes)if(C)++NZ;
                                // 2026-10-17 无开关追踪：直写文件，任何会话/开关状态都留痕（含编译指纹）。
                                const FString Line=FString::Printf(TEXT("commit shaped cells=%d cuts=%d nz=%d rot=%d brush=%d cont=%d build=%s %s\n"),
                                    Placement.Num(),Shapes.Num(),NZ,BrushRotation,Brush,
                                    bPlacementContinued?1:0,TEXT(__DATE__),TEXT(__TIME__));
                                FFileHelper::SaveStringToFile(Line,*(FPaths::ProjectSavedDir()/TEXT("voxel_commit_trace.txt")),FFileHelper::EEncodingOptions::AutoDetect,&IFileManager::Get(),FILEWRITE_Append);
                            }
                            bFeedbackValid=BuildWorld->EditCellsShaped(Placement,PlacementMaterial,Shapes);
                        }
                        else if(bPlacementSnap)bFeedbackValid=BuildWorld->EditVolumeCells(PlacementVolume,Placement,PlacementMaterial);
                        else bFeedbackValid=BuildWorld->PlaceFree(PlacementOrigin,Placement,PlacementMaterial);
                        if(!bFeedbackValid)RefundPlacementBlocks(PlacementMaterial,Cost);
                    }
                    Feedback=BuildWorld->ResultMessage();
                }
                else {bFeedbackValid=false;Feedback=TargetMessage;}
            }
            else if(RemovalTarget)
            {bFeedbackValid=BuildWorld->RemovePrefab(RemovalTarget);Feedback=BuildWorld->ResultMessage();}
            else if(!Removal.IsEmpty())
            {
                // 拆除出来的体素直接进背包：先按材料统计，编辑成功后才发放，失败不会凭空产生物品。
                TMap<FName,int32> Removed;
                for(const FIntVector& Cell:Removal)
                {const FName Material=BuildWorld->VolumeMaterialAt(HitCell.Volume,Cell);if(!Material.IsNone())Removed.FindOrAdd(Material)++;}
                bFeedbackValid=BuildWorld->EditVolumeCells(HitCell.Volume,Removal,NAME_None);
                Feedback=BuildWorld->ResultMessage();
                if(bFeedbackValid)GrantDismantledBlocks(Removed);
            }
            else if(auto* Debris=Cast<AVoxelCollapseFragment>(Hit.GetActor()))
            {
                // 拆除静止的残骸 = 直接回收成体素块（进背包，放不下的掉在脚下）；还在下落时仍按撞击拆碎。
                if(!Debris->IsMoving())
                {
                    TMap<FName,int32> Removed;
                    for(const FVoxelDebrisCell& Cell:Debris->Data().Cells)
                        if(!Cell.Material.IsNone())Removed.FindOrAdd(Cell.Material)++;
                    BuildWorld->RemoveFragment(Debris);
                    GrantDismantledBlocks(Removed);
                    bFeedbackValid=true;Feedback=TEXT("残骸已回收为体素块");
                }
                else
                {BuildWorld->QueueFragmentDamage(Debris,Hit.ImpactPoint-Hit.ImpactNormal*.25,1000000,0,0);bFeedbackValid=true;Feedback=TEXT("已提交残骸拆除");}
            }
            else {bFeedbackValid=false;Feedback=TEXT("只能拆除自己建造的体素和残骸");}
            FeedbackTime=2;
            PlacementCheckAt=0;TargetUpdateAt=0;
        }
        return true;
    }
    if(IsVillageCameraPlacing())return true;
    if(Key==EKeys::E)
    {
        if(Pressed && !bPanelOpen)
            if(auto* Player=Cast<AFPSGAMEPlayerController>(PC))
                if(auto* Breach=ColdSteelWorldInteraction::TraceUseTargets(Player).RepairTarget())
                    Player->RequestVillageRepair(Breach);
        return true;
    }
    if(Key==EKeys::G||Key==EKeys::Three||Key==EKeys::Four||Key==EKeys::Five)return true;
    return false;
}

bool UVoxelBuildComponent::IsFreeBuilding() const
{
    // 开发面板「建造不消耗资源」：扣料与退回共用同一判断，避免免费建造时又凭失败补偿刷出体块。
    const auto* PC=Cast<APlayerController>(GetOwner());
    return PC && UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(PC->GetPawn(),EDevelopmentTuningOption::FreeBuilding);
}

bool UVoxelBuildComponent::ConsumePlacementBlocks(FName Material,int32 Count)
{
    BlockMessage.Empty();
    if(Count<=0||Material.IsNone())return true;
    auto* Model=GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Model)return true;   // 没有档案时不拦建造（预览/审计世界）
    if(IsFreeBuilding())return true;
    const FString Definition=FString::Printf(TEXT("voxel_block_%s"),*Material.ToString());
    if(Model->ConsumeItem(Definition,Count,BlockMessage))return true;
    // 提示栏播报，让玩家立刻知道该去补材料而不是以为卡住了。
    Model->PostNotice(TEXT("材料不足"),BlockMessage.IsEmpty()?FString::Printf(TEXT("缺少 %d 块体素块"),Count):BlockMessage,FString(),3.f);
    return false;
}

void UVoxelBuildComponent::RefundPlacementBlocks(FName Material,int32 Count)
{
    if(Count<=0||Material.IsNone())return;
    // 免费建造没有扣过料，失败时也不能退回，否则等于凭空生成体块。
    if(IsFreeBuilding())return;
    auto* Model=GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Model)return;
    const FString Definition=FString::Printf(TEXT("voxel_block_%s"),*Material.ToString());
    // 编辑最终没生效：把刚扣掉的方块退回去，退不进背包就掉在脚下。
    if(Model->AddItem(Definition,Count))return;
    TMap<FString,int64> Overflow;Overflow.Add(Definition,Count);
    Model->GrantWorldBlocks(Overflow,Hit.ImpactPoint);
    Model->PostNotice(TEXT("放置失败"),FString::Printf(TEXT("%d 块体素已退回脚下 · 按 Z 拾取"),Count),FString(),3.f);
}

void UVoxelBuildComponent::GrantDismantledBlocks(const TMap<FName,int32>& Removed)
{
    if(Removed.IsEmpty())return;
    auto* Model=GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Model)return;
    TMap<FString,int64> Overflow;int64 OverflowTotal=0;
    for(const TPair<FName,int32>& Entry:Removed)
    {
        if(Entry.Value<=0)continue;
        const FString Definition=FString::Printf(TEXT("voxel_block_%s"),*Entry.Key.ToString());
        // Backpack first; whatever does not fit drops at the feet so it is never lost.
        if(Model->AddItem(Definition,Entry.Value))continue;
        Overflow.Add(Definition,Entry.Value);OverflowTotal+=Entry.Value;
    }
    if(Overflow.IsEmpty())return;
    Model->GrantWorldBlocks(Overflow,Hit.ImpactPoint);
    Model->PostNotice(TEXT("背包已满"),FString::Printf(TEXT("%lld 块体素掉在脚下 · 按 Z 拾取"),OverflowTotal),FString(),3.2f);
}

void UVoxelBuildComponent::PlacePrefab()
{
    const FVoxelBuildPrefab* Prefab=SelectedPrefab();
    if(!Prefab){bFeedbackValid=false;Feedback=TEXT("请先选择构件");FeedbackTime=2;return;}
    if(!bPrefabValid){bFeedbackValid=false;Feedback=PrefabMessage;FeedbackTime=2;return;}
    if(DefenseDockPose.IsSet()&&!DefenseDockTarget.IsValid())
    {bFeedbackValid=false;Feedback=TEXT("吸附目标已消失");FeedbackTime=2;return;}
    bFeedbackValid=BuildWorld->PlacePrefab(Prefab->Id,PrefabCell,PrefabPlanYaw,DefenseDockPose.IsSet(),
        DefenseDockTarget.Get(),PlannedGroundYaw(),DefenseDockSocket==VillageGateReplacement::ReplacementSocket,WallCutSelection);
    Feedback=BuildWorld->ResultMessage();FeedbackTime=2;
    PlacementCheckAt=0;TargetUpdateAt=0;
}

