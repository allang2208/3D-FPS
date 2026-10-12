#include "CombatItemFormula.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
TSharedPtr<FJsonObject> CombatItemFormula::Read(const FColdSteelItem& Item)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(CombatItemFormula_Read);
    TSharedPtr<FJsonObject> Data;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return nullptr;
    // Definition-owned balance fields also apply to books created before this update.
    // Instance-owned enhancement level and inventory data remain untouched.
    if(Item.Definition==TEXT("ue_alchemy_spellbook"))
    {
        static const TSharedPtr<FJsonObject> BookDefaults=[] {
            FString Text;TSharedPtr<FJsonObject> Root;
            if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/items.json")))&&
                FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)&&Root)
            {
                const TSharedPtr<FJsonObject>* Book=nullptr;
                if(Root->TryGetObjectField(TEXT("ue_alchemy_spellbook"),Book))return *Book;
            }
            return TSharedPtr<FJsonObject>();}();
        if(BookDefaults)for(const TCHAR* Field:{TEXT("matkFormula"),TEXT("focusEffects"),TEXT("spellbookStatsRevision")})
            if(const auto* Value=BookDefaults->Values.Find(Field))Data->SetField(Field,*Value);
    }
    static const TSharedPtr<FJsonObject> Catalog=[] {
        FString Text;TSharedPtr<FJsonObject> Root;
        if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/source-combat-items.json"))))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root);return Root;}();
    if(!Catalog)return Data;FString WeaponId,Name;Data->TryGetStringField(TEXT("weaponId"),WeaponId);Data->TryGetStringField(TEXT("name"),Name);
    const TSharedPtr<FJsonObject>* Source=nullptr;
    if(!Catalog->TryGetObjectField(WeaponId,Source)&&!Catalog->TryGetObjectField(Name,Source)&&!Catalog->TryGetObjectField(Item.Definition,Source))return Data;
    for(const auto& Pair:(*Source)->Values)if(!Data->HasField(Pair.Key))Data->SetField(Pair.Key,Pair.Value);
    return Data;
}

TSharedPtr<const FJsonObject> CombatItemFormula::ReadOnly(const FColdSteelItem& Item)
{
    static thread_local FColdSteelJsonReadCache Cache;
    const FString Key=FString::FromInt(Item.Definition.Len())+TEXT(":")+Item.Definition+Item.Data
        +(Item.Definition==TEXT("ue_alchemy_spellbook")?TEXT(":spellbook-stats-v2"):TEXT(""));
    return Cache.Get(Key,[&]() -> TSharedPtr<const FJsonObject> {return Read(Item);});
}
