#include "GunsmithSystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

/**
 * 采集工具改造目录（伐木斧、矿镐）。
 *
 * 口径与 `references/modular-melee.md` 一致：栏目数不等于网格数，没有独立模型的
 * 数值选项回退到本槽 factory（当前四栏全部沿用原装外形），改造 ID 与 `gunsmith_parts`
 * 存档位置保持不动，后续实体模块按同一 ID 接入。
 *
 * 工具不进入剑类链路：不给连击、格挡、强化或精通伤害（见 references/harvesting-tools.md）。
 */
void UGunsmithSystem::LoadToolCatalog()
{
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/tool-gunsmith.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)
    {UE_LOG(LogTemp,Error,TEXT("Tool gunsmith catalog unavailable"));return;}
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    TMap<FString,TArray<FGunsmithOption>> FactoryOptions;
    for(const auto& Value:Root->GetArrayField(TEXT("columns")))
    {
        const auto Column=Value->AsObject();
        const FString Key=Column->GetStringField(TEXT("key"));
        ToolSlotKeys.Add(Key);ToolCategoryNames.Add(Column->GetStringField(TEXT("name")));
        FGunsmithOption Factory;Factory.Id=TEXT("false");
        Factory.Name=Column->GetStringField(TEXT("default"));
        Factory.Description=Column->GetStringField(TEXT("description"));
        ToolDefaultNames.Add(Factory.Name);
        FactoryOptions.Add(Key,{Factory});
        const TArray<TSharedPtr<FJsonValue>>* Options=nullptr;
        if(Column->TryGetArrayField(TEXT("options"),Options))for(const auto& Entry:*Options)
        {
            const auto Data=Entry->AsObject();FGunsmithOption Part;
            Part.Id=Data->GetStringField(TEXT("id"));Part.Name=Data->GetStringField(TEXT("name"));
            Part.Description=Data->GetStringField(TEXT("description"));
            Data->TryGetStringField(TEXT("appearance"),Part.Appearance);
            const TArray<TSharedPtr<FJsonValue>>* Compatible=nullptr;
            if(Data->TryGetArrayField(TEXT("weapons"),Compatible))for(const auto& Id:*Compatible)Part.CompatibleWeapons.Add(Id->AsString());
            for(const auto& Effect:Data->GetArrayField(TEXT("effects")))
                Part.Effects.Emplace(Effect->AsObject()->GetStringField(TEXT("text")),int32(Effect->AsObject()->GetNumberField(TEXT("benefit"))));
            const auto Stats=Data->GetObjectField(TEXT("stats"));
            Stats->TryGetNumberField(TEXT("damage_mult"),Part.Tool.Damage);
            Stats->TryGetNumberField(TEXT("attack_speed_mult"),Part.Tool.AttackSpeed);
            Stats->TryGetNumberField(TEXT("stamina_mult"),Part.Tool.Stamina);
            Stats->TryGetNumberField(TEXT("combat_reach_mult"),Part.Tool.CombatReach);
            Stats->TryGetNumberField(TEXT("toughness_damage_mult"),Part.Tool.ToughnessDamage);
            Stats->TryGetNumberField(TEXT("harvest_yield_mult"),Part.Tool.HarvestYield);
            Stats->TryGetNumberField(TEXT("harvest_reach_mult"),Part.Tool.HarvestReach);
            Stats->TryGetNumberField(TEXT("harvest_radius_add_cm"),Part.Tool.HarvestRadiusAddCM);
            Stats->TryGetNumberField(TEXT("bonus_harvest_chance"),Part.Tool.BonusHarvestChance);
            Stats->TryGetNumberField(TEXT("crit_chance_add"),Part.Tool.CriticalChanceAdd);
            int32 Hits=0;if(Stats->TryGetNumberField(TEXT("harvest_hits_add"),Hits))Part.Tool.HarvestHitsAdd=Hits;
            FactoryOptions.FindChecked(Key).Add(MoveTemp(Part));
        }
    }
    for(const auto& Value:Root->GetArrayField(TEXT("weapons")))
    {
        // 目录条目是对象（保留 traits 等只读展示字段），与近战目录同构。
        const TSharedPtr<FJsonObject> Entry=Value->AsObject();
        if(!Entry)continue;
        const FString Id=Entry->GetStringField(TEXT("id"));
        const auto Item=Profile->CreateItem(Id);
        if(!ColdSteelInventory::IsEquippedProductionTool(Item))continue;
        FGunsmithWeapon Weapon;Weapon.Id=Id;Weapon.Model=TEXT("production_tool");
        Weapon.Name=ColdSteelInventory::Text(Item,TEXT("name"));
        Weapon.Allowed=ToolSlotKeys;Weapon.Options=FactoryOptions;
        // Source 让物品提示能读到 traits；没有它工具就没有「特殊性质」段。
        Weapon.Source=Entry;
        for(auto& Column:Weapon.Options)Column.Value.RemoveAll([&](const FGunsmithOption& Part){return !Part.CompatibleWeapons.IsEmpty()&&!Part.CompatibleWeapons.Contains(Id);});
        Weapon.Base.Damage=ColdSteelInventory::Number(Item,TEXT("melee_damage"),12);
        Weapon.Base.Interval=ColdSteelInventory::Number(Item,TEXT("swing_seconds"),1.1);
        Weapon.Base.Range=ColdSteelInventory::Number(Item,TEXT("combat_reach_cm"),180)/100.;
        Weapon.Base.ADS=Weapon.Base.Reload=Weapon.Base.EmptyReload=Weapon.Base.Speed=0;
        Weapon.Base.Recoil=Weapon.Base.Shake=Weapon.Base.Spread=0;Weapon.Base.Capacity=0;
        ToolWeapons.Add(Id,MoveTemp(Weapon));
    }
}
