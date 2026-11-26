// Offline audit: verify the stale-save shovel equip chain end-to-end without
// PIE or rendering. Loads the player's real PIE profile, then:
//   1) the shovel item lands wherever the save put it (compartment in the
//      reported case),
//   2) DefaultAction equips it into main hand slot 6,
//   3) NormalizeProductionState synced tool_viewmodel/animation prefix into the
//      saved item Data (old saves carry pre-equip catalog data),
//   4) the referenced viewmodel + 6 clips exist on disk.
#include "ShovelEquipAuditCommandlet.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelInventoryTypes.h"

#if WITH_EDITOR
int32 UShovelEquipAuditCommandlet::Main(const FString& Params)
{
    const FString Profile = Params.Contains(TEXT("PIE")) ? TEXT("ColdSteelPlayer_PIE_0") : TEXT("ColdSteelPlayer_A");

    UGameInstance* GI = nullptr;
    UWorld* World = nullptr;
    UColdSteelStatusModel* Model = nullptr;
    auto Shutdown = [&]()
    {
        if (GI) GI->Shutdown();
        if (World) { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); }
        if (GI) GI->RemoveFromRoot();
    };
    ON_SCOPE_EXIT { Shutdown(); };
    GI = NewObject<UGameInstance>(GEngine);
    GI->AddToRoot();
    GI->InitializeStandalone(TEXT("ShovelEquipAuditWorld"));
    World = GI->GetWorld();
    Model = GI->GetSubsystem<UColdSteelStatusModel>();
    if (!World || !Model) return 2;

    // Point the model at the real player slot (friend access; the game's own
    // Initialize derives it from the platform name the same way).
    Model->SaveSlot = Profile;

    TArray<FString> Report;
    auto Check = [&](bool b, const FString& Msg)
    {
        Report.Add(FString::Printf(TEXT("%s %s"), b ? TEXT("PASS") : TEXT("FAIL"), *Msg));
        return b;
    };

    Check(Model->ReloadProfile(), TEXT("profile reload"));
    const auto Items = Model->Items();
    const FColdSteelItem* Shovel = nullptr;
    for (const auto& I : Items)
        if (I.Definition == TEXT("tool_shovel")) { Shovel = &I; break; }
    if (!Check(Shovel != nullptr, TEXT("shovel item exists in save"))) return WriteReport(Report, Profile), 3;
    Report.Add(FString::Printf(TEXT("INFO shovel place=%d cell=%d"), Shovel->Place, Shovel->Cell));

    // A full bag legitimately blocks the displaced-item return (real gameplay
    // constraint). Clear a 2x3 window as the player would, then equip.
    if (Shovel->Place == 0)
    {
        auto P = Model->Snapshot();
        int32 Freed = 0;
        for (int32 N = P.Items.Num() - 1; N >= 0 && Freed < 6; --N)
            if (P.Items[N].Place == 0 && P.Items[N].Definition != TEXT("tool_shovel"))
            { P.Items.RemoveAt(N); ++Freed; }
        Model->CommitState(P);
        Shovel = nullptr;
        for (const auto& I : Model->Items())
            if (I.Definition == TEXT("tool_shovel")) { Shovel = &I; break; }
    }
    // Already equipped from a previous audit run? Then DefaultAction would
    // unequip (Place==1 toggles to bag); verify the equipped state directly.
    if (Shovel->Place == 1)
        Check(true, TEXT("shovel already in equipment (previous run persisted)"));
    else
    {
        const bool bEquipped = Model->DefaultAction(Shovel->InstanceId);
        Check(bEquipped, FString::Printf(TEXT("DefaultAction equips (place %d) reason=%s"), Shovel->Place, *Model->ResultMessage()));
    }
    Shovel = nullptr;
    for (const auto& I : Model->Items())
        if (I.Definition == TEXT("tool_shovel")) { Shovel = &I; break; }
    if (!Check(Shovel != nullptr && Shovel->Place == 1, TEXT("shovel now in equipment"))) return WriteReport(Report, Profile), 4;

    const FString Viewmodel = ColdSteelInventory::Text(*Shovel, TEXT("tool_viewmodel"));
    Check(!Viewmodel.IsEmpty(), TEXT("item Data carries tool_viewmodel (normalize sync)"));
    const FString Prefix = ColdSteelInventory::Text(*Shovel, TEXT("tool_animation_prefix"));
    Check(!Prefix.IsEmpty(), TEXT("item Data carries tool_animation_prefix"));

    auto PackageToFile = [](const FString& PackagePath)
    {
        // Catalog values are bare package paths (no ".AssetName"); optional object
        // suffixes are trimmed. The file is always <package>.uasset.
        FString P = PackagePath;
        const int32 Dot = P.Find(TEXT("."), ESearchCase::IgnoreCase, ESearchDir::FromEnd);
        const int32 Slash = P.Find(TEXT("/"), ESearchCase::IgnoreCase, ESearchDir::FromEnd);
        if (Dot > Slash) P = P.Left(Dot);
        return FPaths::ProjectContentDir() / P.RightChop(5) + TEXT(".uasset");
    };
    Check(FPaths::FileExists(PackageToFile(Viewmodel)), TEXT("viewmodel package on disk: ") + PackageToFile(Viewmodel));
    for (const TCHAR* Clip : {TEXT("Idle"), TEXT("Equip"), TEXT("Swing"), TEXT("HitRecover"), TEXT("Walk"), TEXT("Run")})
    {
        Check(FPaths::FileExists(PackageToFile(Prefix + Clip)), FString::Printf(TEXT("clip %s on disk"), Clip));
    }
    // Active weapon slot follows the item; the tool component reads ActiveProductionTool().
    const auto* Active = Model->ActiveProductionTool();
    Check(Active && Active->InstanceId == Shovel->InstanceId, TEXT("ActiveProductionTool resolves the equipped shovel"));
    WriteReport(Report, Profile);
    return Report.ContainsByPredicate([](const FString& L) { return L.StartsWith(TEXT("FAIL")); }) ? 5 : 0;
}

void UShovelEquipAuditCommandlet::WriteReport(const TArray<FString>& Report, const FString& Profile)
{
    const FString Path = FPaths::ProjectSavedDir() / TEXT("ShovelEquipAudit") / TEXT("report.txt");
    FString Text = FString::Printf(TEXT("profile %s\n"), *Profile);
    for (const auto& L : Report) Text += L + LINE_TERMINATOR;
    FFileHelper::SaveStringToFile(Text, *Path);
    UE_LOG(LogTemp, Display, TEXT("SHOVEL_EQUIP_AUDIT\n%s"), *Text);
}
#else
int32 UShovelEquipAuditCommandlet::Main(const FString&) { return 1; }
#endif
