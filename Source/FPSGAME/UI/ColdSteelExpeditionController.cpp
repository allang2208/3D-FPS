#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Building/VoxelBuildComponent.h"
#include "ColdSteelExpeditionWidget.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelWorldInteraction.h"
#include "TransitLoadingSubsystem.h"
#include "WeatherControlWidget.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"

namespace
{
    const TCHAR* RandomizedDungeonMap = TEXT("/Game/GameMaps/L_Dungeon_Randomized");
    const FName RandomizedDungeonId(TEXT("randomized_dungeon"));
    const TCHAR* DataArchiveSubjectMap = TEXT("/Game/GameMaps/Design/L_AbandonedDataArchive_Subject");
    const FName DataArchiveSubjectId(TEXT("data_archive_subject"));
}

bool AFPSGAMEPlayerController::OpenExpedition()
{
    if (ExpeditionPanel || !IsLocalController()) return false;
    if (!ColdSteelWorldInteraction::IsExpeditionAltar(ColdSteelWorldInteraction::TraceTarget(this))) return false;
    CloseGunsmith();
    CloseEnhancement();
    if (WeatherPanel && WeatherPanel->IsPanelOpen()) WeatherPanel->SetPanelOpen(false);
    if (VoxelBuilder && VoxelBuilder->IsPanelOpen()) VoxelBuilder->ClosePanel();

    auto* Panel = CreateWidget<UColdSteelExpeditionWidget>(this);
    if (!Panel) return false;
    bExpeditionReturnToInventory = ColdSteelHUD && ColdSteelHUD->IsInventoryOpen();
    bExpeditionReturnToCursor = bShowMouseCursor && !bExpeditionReturnToInventory;
    UWidgetBlueprintLibrary::CancelDragDrop();
    if (ColdSteelHUD)
    {
        ColdSteelHUD->CancelQuickDrag();
        ColdSteelHUD->HideItemTooltip(true);
        if (bExpeditionReturnToInventory) ColdSteelHUD->ToggleInventory();
        ColdSteelHUD->SetExternalDrawerOpen(true);
    }
    if (auto* PawnCharacter = Cast<AFPSGAMECharacter>(GetPawn())) PawnCharacter->SuspendWeaponForMenu();

    FColdSteelExpeditionDestination Facility;
    Facility.Id = RandomizedDungeonId;
    Facility.Name = TEXT("地下设施");
    Facility.Category = TEXT("地牢 / 地下探索");
    Facility.Description = TEXT("深入废弃的地下设施。工业通道连接遗迹与异常区域，封闭空间中仍有未知的威胁等待揭晓。");
    Facility.Scale = TEXT("随机作者房间装配，含支线与首领终点");
    Facility.Threat = TEXT("封闭通道、怪物与首领遭遇");
    Facility.EntryCost = TEXT("无需祭品");
    Facility.bCanDepart = true;
    Facility.Rules = {
        TEXT("本次出征不消耗祭品与钥匙。"),
        TEXT("确认后进入随机地牢；地牢内起点与首领房可返回主场景。"),
    };
    TArray<FColdSteelExpeditionDestination> Entries;
    Entries.Add(MoveTemp(Facility));
    FColdSteelExpeditionDestination Archive;
    Archive.Id = DataArchiveSubjectId;
    Archive.Name = TEXT("废弃数据档案中心 · 主体样板");
    Archive.Category = TEXT("地下设施 / 独立场景");
    Archive.Description = TEXT("多边形档案调度厅，中央下沉开放区与四向宽梯连接外围设备环廊。机柜分区、熄灭屏幕及桥架保留检索设施的轮廓。");
    Archive.Scale = TEXT("24 × 24 米主体，中央下沉 0.6 米");
    Archive.Threat = TEXT("设备停用；主体制作阶段，无怪物与环境伤害");
    Archive.EntryCost = TEXT("无需祭品");
    Archive.bCanDepart = true;
    Archive.Rules = { TEXT("进入独立主体场景，不改变随机房间池。"), TEXT("入口门斗内按 E 返回主场景。") };
    Entries.Add(MoveTemp(Archive));
    Panel->SetDestinations(MoveTemp(Entries));
    Panel->OnDepartureRequested.BindLambda([this](FName Id)
    {
        const TCHAR* DestinationMap = Id == RandomizedDungeonId ? RandomizedDungeonMap :
            Id == DataArchiveSubjectId ? DataArchiveSubjectMap : nullptr;
        if (!DestinationMap) return FText::FromString(TEXT("未知目的地"));
        if (GetNetMode() != NM_Standalone) return FText::FromString(TEXT("联机模式暂不支持出征"));
        if (!FPackageName::DoesPackageExist(DestinationMap))
            return FText::FromString(TEXT("目的地关卡缺失，出征已取消"));
        // OpenLevel tears down this world before ConfirmDeparture can Close().
        // Release the expedition UIOnly locks first so travel does not inherit them,
        // and skip reopening the backpack on a map that is about to unload.
        bExpeditionReturnToInventory = false;
        bExpeditionReturnToCursor = false;
        CloseExpedition();
        if (auto* Loading = GetGameInstance() ? GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>() : nullptr)
            Loading->BeginTransition(DestinationMap);
        UE_LOG(LogTemp, Display, TEXT("Expedition: Travel %s"), DestinationMap);
        UGameplayStatics::OpenLevel(this, FName(DestinationMap), true);
        return FText::GetEmpty();
    });
    ExpeditionPanel = Panel;
    Panel->AddToPlayerScreen(60);
    SetIgnoreMoveInput(true);
    SetIgnoreLookInput(true);
    bShowMouseCursor = true;
    FInputModeUIOnly Mode;
    Mode.SetWidgetToFocus(Panel->TakeWidget());
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    SetInputMode(Mode);
    Panel->SetKeyboardFocus();
    return true;
}

void AFPSGAMEPlayerController::CloseExpedition()
{
    if (!ExpeditionPanel) return;
    ExpeditionPanel->RemoveFromParent();
    ExpeditionPanel = nullptr;
    if (ColdSteelHUD) ColdSteelHUD->SetExternalDrawerOpen(false);
    // Release only the input locks added by OpenExpedition; do not reset other owners' counters.
    SetIgnoreMoveInput(false);
    SetIgnoreLookInput(false);
    bShowMouseCursor = bExpeditionReturnToCursor;
    if (bExpeditionReturnToCursor)
    {
        FInputModeGameAndUI Mode;
        Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
        Mode.SetHideCursorDuringCapture(false);
        SetInputMode(Mode);
    }
    else SetInputMode(FInputModeGameOnly());
    if (bExpeditionReturnToInventory && ColdSteelHUD && !ColdSteelHUD->IsInventoryOpen()) ColdSteelHUD->ToggleInventory();
    bExpeditionReturnToInventory = false;
    bExpeditionReturnToCursor = false;
}
