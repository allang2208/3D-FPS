#include "WeaponReloadStages.h"
#include "DanWesson715WeaponAssets.h"
#include "RSH12WeaponAssets.h"
#include "ASH12WeaponAssets.h"
#include "SVDWeaponAssets.h"
#include "M16WeaponAssets.h"
#include "PKMLowpolyWeaponAssets.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

FWeaponReloadStages WeaponReloadStages::ForWeapon(const FString& Definition, bool Empty, bool Drum, bool SingleRound, int32 RoundCount)
{
    if ((Definition == TEXT("ue_dan_wesson715") || Definition == TEXT("ue_rsh12")))
    {
        using namespace DanWesson715WeaponAssets;
        if (SingleRound)
        {
            const float Tail = SingleLoopBegin(Empty) + SingleStep * RoundCount;
            // Same closure contact the audio cue table uses; one named constant so
            // the Ready stage and the Close sound cannot drift apart.
            return {SingleSeatTime(0, Empty), Tail, Tail + SingleCloseContact};
        }
        const float Scale = Empty ? EmptyReload / NormalReload : 1.f;
        return {Seat * Scale, 2.68f * Scale, Close * Scale};
    }
    if (Definition == SVDWeaponAssets::Definition)
        return {SVDWeaponAssets::MagazineInsert,SVDWeaponAssets::ChargeStart,Empty?SVDWeaponAssets::ChargeRelease:SVDWeaponAssets::MagazineInsert};
    if (Definition == TEXT("ue_m1911") || Definition == TEXT("ue_g18") || Definition == TEXT("ue_pit_viper2011")) return {126.f/120.f, 164.f/120.f, Empty ? 192.f/120.f : 126.f/120.f};
    if (Definition == TEXT("ue_akm") || Definition == TEXT("ue_a762") || Definition == TEXT("ue_lmg201"))
        return {220.f/120.f, 270.f/120.f, Empty ? 350.f/120.f : 220.f/120.f};
    if (Definition == TEXT("ue_qbz191"))
        return {76.f/60.f, 126.f/60.f, Empty ? 151.f/60.f : 76.f/60.f};
    if (Definition == TEXT("ue_ash12"))
        return {ASH12WeaponAssets::MagazineInsert, 1.91f, Empty ? ASH12WeaponAssets::ChargeRelease : ASH12WeaponAssets::MagazineInsert};
    if (Definition == TEXT("ue_pkm_lowpoly"))
        return {PKMLowpolyWeaponAssets::ReloadEventTime(4.35f,Empty),
            PKMLowpolyWeaponAssets::ReloadEventTime(5.1f,Empty),
            PKMLowpolyWeaponAssets::ReloadEventTime(Empty ? 6.45f : 5.72f,Empty)};
    if (Definition == TEXT("ue_m16a2") && Empty)
        return {M16WeaponAssets::MagazineInsert, 111.f/60.f, M16WeaponAssets::ChargeRelease};
    return {Empty ? 54.f/60.f : 76.f/60.f, 88.f/60.f,
        Empty ? (Drum ? 116.f/60.f : 130.f/60.f) : 76.f/60.f};
}

bool WeaponReloadStages::NeedsCycle(const FColdSteelItem& Item)
{
    TSharedPtr<FJsonObject> Data;
    bool Pending = false;
    return FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data), Data) && Data
        && Data->TryGetBoolField(TEXT("reload_pending_cycle"), Pending) && Pending;
}

bool WeaponReloadStages::UsesEmptyCycle(const FColdSteelItem& Item)
{
    TSharedPtr<FJsonObject> Data;
    bool Empty = true;
    if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data) && Data)
        Data->TryGetBoolField(TEXT("reload_cycle_empty"),Empty);
    return Empty;
}

bool WeaponReloadStages::SetNeedsCycle(FColdSteelItem& Item, int32 Pending)
{
    TSharedPtr<FJsonObject> Data;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data), Data) || !Data) return false;
    if (Pending)
    {
        Data->SetBoolField(TEXT("reload_pending_cycle"), true);
        Data->SetBoolField(TEXT("reload_cycle_empty"), Pending!=2);
    }
    else
    {
        Data->RemoveField(TEXT("reload_pending_cycle"));
        Data->RemoveField(TEXT("reload_cycle_empty"));
    }
    FString Json;
    if (!FJsonSerializer::Serialize(Data.ToSharedRef(), TJsonWriterFactory<>::Create(&Json))) return false;
    Item.Data = MoveTemp(Json);
    return true;
}
