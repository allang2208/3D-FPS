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
    Facility.Scale = TEXT("三条主题路线 · 每条 5–7 间");
    Facility.Threat = TEXT("封闭通道 · 区域清剿 · 首领战");
    Facility.EntryCost = TEXT("无需祭品");
    Facility.Completion = TEXT("清理任意一路与数据档案中心，进入最终首领区域。");
    Facility.bDungeonLoot = true;
    Facility.Routes = {
        {TEXT("货运路线"),TEXT("货运转运间 → 货运仓库 → 地下车站")},
        {TEXT("医疗路线"),TEXT("排水间 → 隔离病区 → 解剖教学剧场")},
        {TEXT("处理路线"),TEXT("破损支护室 → 焚化处理厅 → 净化站")},
    };
    Facility.bCanDepart = GetNetMode()!=NM_Client && FPackageName::DoesPackageExist(RandomizedDungeonMap);
    if(!Facility.bCanDepart)Facility.BlockReason=GetNetMode()==NM_Client?TEXT("联机模式暂不支持出征"):TEXT("目的地关卡缺失");
    Facility.Rules = {
        {TEXT("进入与路线"),TEXT("无需祭品或钥匙。三条路线可自由选择；清理任意一条完整路线与数据档案中心，即可开启通往首领的闸门，无需清完全部三路。")},
        {TEXT("房间与闸门"),TEXT("每条路线由前置 1–2 间过渡房、固定 3 间主题房、后置 1–2 间过渡房组成。货运转运间清怪后开闸，依次进入仓库与地下车站。")},
        {TEXT("探索与奖励"),TEXT("额外支路可继续探索，随机宝箱侧室并非每局必有。击败首领后开放最终宝箱房；宝箱内容随机抽取，预览物品不保证全部获得。")},
        {TEXT("返程与再次出征"),TEXT("通过起点返程入口或首领后的奖励区入口返回主场景。再次出征会生成新的地牢，原局清理进度不会作为下一局继续。")},
        {TEXT("死亡与已获物品"),TEXT("死亡后在当前关卡重新生成角色；已经获得并保存的物品不会因死亡或返程被清空。首领交战在死亡或离场后重置。")},
        {TEXT("领取与背包空间"),TEXT("宝箱奖励领取后随角色档案保存，弹药进入弹药袋。背包放不下的物品留在宝箱旁，返程前请拾取；主背包空格数不代表一定能放入任意形状的大件。")},
    };
    TArray<FColdSteelExpeditionDestination> Entries;
    Entries.Add(MoveTemp(Facility));
    Panel->SetDestinations(MoveTemp(Entries));
    Panel->OnDepartureRequested.BindLambda([this](FName Id)
    {
        const TCHAR* DestinationMap = Id == RandomizedDungeonId ? RandomizedDungeonMap : nullptr;
        if (!DestinationMap) return FText::FromString(TEXT("未知目的地"));
        if (GetNetMode() == NM_Client) return FText::FromString(TEXT("联机模式暂不支持出征"));
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

void AFPSGAMEPlayerController::PrepareExpeditionEquipment()
{
    // Reuse the existing close path so this panel releases only its own input locks.
    bExpeditionReturnToInventory=false;
    bExpeditionReturnToCursor=false;
    CloseExpedition();
    if(ColdSteelHUD&&!ColdSteelHUD->IsInventoryOpen())ToggleInventory();
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
