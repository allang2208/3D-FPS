#include "FullAutoTrigger.h"
#include "GunsmithSystem.h"
#include "PistolDualWieldComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "Engine/GameInstance.h"
#include "Serialization/JsonSerializer.h"

bool FullAutoTrigger::Supports(const FString& Definition)
{
    // The current catalog's semi-automatic pistols only; revolvers and the
    // native automatic G18 must not acquire this attachment through save data.
    return Definition == TEXT("ue_m1911") || Definition == TEXT("ue_pit_viper2011");
}

bool FullAutoTrigger::Installed(const FString& Definition, const TMap<FString,FString>& Parts)
{
    return Supports(Definition) && Parts.FindRef(TEXT("trigger")) == Part;
}

bool FullAutoTrigger::Automatic(const FColdSteelItem& Item, bool bInstalled)
{
    if (Item.Definition == TEXT("ue_g18")) return true;
    if (!bInstalled || !Supports(Item.Definition)) return false;
    const auto Data = ColdSteelItemData::Read(Item.Data);
    FString Mode;
    // New installations and older installed instances without a saved choice
    // start automatic; an explicitly selected semi mode remains persistent.
    if (!Data || !Data->TryGetStringField(ModeKey, Mode)) return true;
    return Mode == TEXT("auto");
}

FString FullAutoTrigger::Hint(bool bAutomatic, int32 HandIndex)
{
    return FString(bAutomatic ? TEXT("全自动") : TEXT("半自动"))
        + (HandIndex == 1 ? TEXT(" · H 切换") : TEXT(" · V 切换"));
}

FString AFPSGAMECharacter::GetFireModeHint(int32 HandIndex) const
{
    if (HasOffhandPistol())
    {
        if (HandIndex < 0 || HandIndex > 1 || (HandIndex == 0 && !IsDualWieldingPistols())) return {};
        const auto& Hand = DualPistols->Hand(HandIndex);
        return Hand.SelectableAutomatic ? FullAutoTrigger::Hint(Hand.Automatic, HandIndex) : FString();
    }
    return HandIndex == 0 && bInventoryWeaponReady && bSelectableAutoTrigger
        ? FullAutoTrigger::Hint(bAutomaticTrigger, 0) : FString();
}

void AFPSGAMECharacter::MainFireModePressed() { ToggleWeaponFireMode(0); }
void AFPSGAMECharacter::OffhandFireModePressed() { ToggleWeaponFireMode(1); }

void AFPSGAMECharacter::ToggleWeaponFireMode(int32 HandIndex)
{
    if (!IsLocallyControlled() || IsTraversing() || IsSwitchingWeapon() || IsChoosingAmmo()
        || AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(GetController()))) return;
    if (const auto* Health = FindComponentByClass<UFPSCombatHealthComponent>(); Health && Health->IsDead()) return;
    if (QuickCombatPistol && QuickCombatPistol->IsOccupyingLeftHand()) return;
    auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* Gunsmith = GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    if (!Profile || !Gunsmith) return;
    FString Instance;
    const bool bDualController = HasOffhandPistol();
    if (bDualController)
    {
        if (HandIndex < 0 || HandIndex > 1 || (HandIndex == 0 && !IsDualWieldingPistols())) return;
        const auto& Hand = DualPistols->Hand(HandIndex);
        if (!Hand.SelectableAutomatic || Hand.Reloading || DualPistols->IsEquipping()
            || (HandIndex == 1 && IsCastBlockingLeftHandAction())) return;
        Instance = Hand.Item.InstanceId;
    }
    else
    {
        if (HandIndex != 0 || !bInventoryWeaponReady || !bSelectableAutoTrigger
            || IsWeaponBusy(true) || IsCastBlockingLeftHandAction()) return;
        Instance = ActiveInventoryWeapon;
    }
    Profile->SyncRuntime();
    auto State = Profile->Snapshot();
    auto* Item = State.Items.FindByPredicate([&](const auto& Candidate){ return Candidate.InstanceId == Instance; });
    if (!Item || !FullAutoTrigger::Installed(Item->Definition, Gunsmith->Installed(*Item))) return;
    TSharedPtr<FJsonObject> Data;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item->Data), Data) || !Data) return;
    const bool bNewAutomatic = !FullAutoTrigger::Automatic(*Item, true);
    Data->SetStringField(FullAutoTrigger::ModeKey, bNewAutomatic ? TEXT("auto") : TEXT("semi"));
    Item->Data.Reset();
    FJsonSerializer::Serialize(Data.ToSharedRef(), TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Item->Data));
    // Existing atomic save/publication path owns mode persistence. The other
    // hand's item and cadence remain untouched; a failed save changes neither.
    if (!Profile->CommitState(MoveTemp(State))) return;
    InterruptWeaponInspection();
    // A mode change requires a fresh press, without resetting either cooldown.
    if (bDualController) DualPistols->Trigger(HandIndex, false);
    else { bFireHeld = false; bPistolShotPending = false; }
}
