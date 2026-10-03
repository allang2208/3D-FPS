#include "ColdSteelStatusModel.h"
#include "../Weapons/WeaponReloadStages.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void UColdSteelStatusModel::LoadAmmoCatalog()
{
    AmmoTypes.Reset();WeaponAmmoGroups.Reset();
    FString Json;TSharedPtr<FJsonObject> Root;
    if(FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/ammo_types.json"))) &&
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root))
    {
        const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
        if(Root->TryGetArrayField(TEXT("types"),Rows))for(const auto& Value:*Rows)
        {
            const auto Row=Value->AsObject();if(!Row)continue;
            FColdSteelAmmoType Type;double Number=0;
            Row->TryGetStringField(TEXT("id"),Type.Id);Row->TryGetStringField(TEXT("group"),Type.Group);
            Row->TryGetStringField(TEXT("group_name"),Type.GroupName);Row->TryGetStringField(TEXT("name"),Type.Name);
            Row->TryGetStringField(TEXT("description"),Type.Description);Row->TryGetBoolField(TEXT("enabled"),Type.Enabled);
            Row->TryGetStringField(TEXT("icon"),Type.Icon);
            Row->TryGetStringField(TEXT("projectile_mesh"),Type.ProjectileMesh);
            FString TierHex;Row->TryGetStringField(TEXT("tier_name"),Type.TierName);
            if(Row->TryGetStringField(TEXT("tier_color"),TierHex)&&!TierHex.IsEmpty())Type.TierColor=FLinearColor::FromSRGBColor(FColor::FromHex(TierHex));
            Row->TryGetBoolField(TEXT("allow_infinite_reserve"),Type.AllowInfiniteReserve);
            if(Row->TryGetNumberField(TEXT("order"),Number))Type.Order=FMath::Clamp(Number,-100000.,100000.);
            if(Row->TryGetNumberField(TEXT("damage_multiplier"),Number)&&FMath::IsFinite(Number))Type.DamageMultiplier=FMath::Clamp(Number,0.,100.);
            if(Row->TryGetNumberField(TEXT("physical_armor_penetration"),Number)&&FMath::IsFinite(Number))Type.PhysicalArmorPenetration=FMath::Clamp(Number,0.,1.);
            if(Row->TryGetNumberField(TEXT("poison_stacks"),Number)&&FMath::IsFinite(Number))Type.PoisonStacks=FMath::Clamp(int32(Number),0,20);
            if(Row->TryGetNumberField(TEXT("bleed_stacks"),Number)&&FMath::IsFinite(Number))Type.BleedStacks=FMath::Clamp(int32(Number),0,20);
            if(!Type.Id.IsEmpty()&&!Type.Group.IsEmpty()&&!AmmoType(Type.Id))AmmoTypes.Add(MoveTemp(Type));
        }
    }
    // Gunsmith initializes after the profile: read only its compatibility mapping,
    // avoiding a subsystem initialization cycle during save migration.
    Root.Reset();
    if(FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/gunsmith.json"))) &&
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root))
    {
        const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
        if(Root->TryGetArrayField(TEXT("weapons"),Rows))for(const auto& Value:*Rows)
        {
            const auto Row=Value->AsObject();const TSharedPtr<FJsonObject>* Base=nullptr;FString Id,Ammo;
            if(Row&&Row->TryGetStringField(TEXT("id"),Id)&&Row->TryGetObjectField(TEXT("base"),Base)&&
                (*Base)->TryGetStringField(TEXT("ammo_item_id"),Ammo))WeaponAmmoGroups.Add(Id,Ammo);
        }
    }
    AmmoTypes.Sort([](const auto& A,const auto& B){return A.Order==B.Order?A.Id<B.Id:A.Order<B.Order;});
}
const FColdSteelAmmoType* UColdSteelStatusModel::AmmoType(const FString& Id) const
{return AmmoTypes.FindByPredicate([&](const auto& T){return T.Id==Id;});}
FString UColdSteelStatusModel::AmmoGroupFor(const FColdSteelItem& Item) const
{
    if (ColdSteelInventory::IsBow(Item))
    {
        FString Default = ColdSteelInventory::Text(Item, TEXT("arrow_ammo"));
        if (Default.IsEmpty()) Default = TEXT("arrow_wood");
        const auto* Type = AmmoType(Default);
        return Type ? Type->Group : FString();
    }
    return WeaponAmmoGroups.FindRef(Item.Definition);
}
FString UColdSteelStatusModel::AmmoLabel(const FString& Id) const
{const auto* T=AmmoType(Id);return T?T->GroupName+TEXT(" · ")+T->Name:Id;}
int64 UColdSteelStatusModel::PouchCount(const FString& Id) const
{return Current.AmmoPouch.FindRef(Id);}
TArray<FColdSteelAmmoChoice> UColdSteelStatusModel::CompatibleAmmo(const FColdSteelItem& Item) const
{
    TArray<FColdSteelAmmoChoice> Result;const FString Group=AmmoGroupFor(Item),Loaded=AmmoDefinitionFor(Item);
    for(const auto& Type:AmmoTypes)if(Type.Enabled&&Type.Group==Group)
        Result.Add({Type.Id,Type.Name,PouchCount(Type.Id),Type.Id==Loaded});
    return Result;
}
float UColdSteelStatusModel::AmmoDamageMultiplier(const FColdSteelItem& Item) const
{const auto* Type=AmmoType(AmmoDefinitionFor(Item));return Type?Type->DamageMultiplier:1.f;}
float UColdSteelStatusModel::AmmoArmorPenetration(const FColdSteelItem& Item) const
{const auto* Type=AmmoType(AmmoDefinitionFor(Item));return Type?Type->PhysicalArmorPenetration:0.f;}
bool UColdSteelStatusModel::AddAmmoToState(FColdSteelProfile& State,const FString& Id,int64 Count) const
{
    if(!AmmoType(Id)||Count<0||Count>ColdSteelAmmo::MaxCount)return false;
    const int64 Before=State.AmmoPouch.FindRef(Id);
    if(Before<0||Before>ColdSteelAmmo::MaxCount-Count)return false;
    State.AmmoPouch.Add(Id,Before+Count);return true;
}
bool UColdSteelStatusModel::GrantAmmo(const FString& Id,int64 Count)
{
    if(Count<=0)return false;SyncRuntime();auto State=Snapshot();
    if(!AddAmmoToState(State,Id,Count)){Message=TEXT("弹药数量超出可存储范围");return false;}
    if(!CommitState(MoveTemp(State)))return false;
    PostNotice(TEXT("弹药已收纳"),FString::Printf(TEXT("%s +%lld"),*AmmoLabel(Id),Count));return true;
}
bool UColdSteelStatusModel::SpendAmmo(const FString& Id,int64 Count)
{
    if(Count<=0||PouchCount(Id)<Count)return false;
    SyncRuntime();auto State=Snapshot();State.AmmoPouch.FindOrAdd(Id)-=Count;return CommitState(MoveTemp(State));
}
bool UColdSteelStatusModel::NormalizeAmmo(FColdSteelProfile& State,bool& Changed) const
{
    if(State.AmmoPouchVersion<0||State.AmmoPouchVersion>1)return false;
    TSet<FString> Removed;
    for(const auto& Item:State.Items)if(AmmoType(Item.Definition))
    {
        if(!AddAmmoToState(State,Item.Definition,Item.Count))return false;
        Removed.Add(Item.InstanceId);
    }
    if(Removed.Num())
    {
        State.Items.RemoveAll([&](const auto& I){return Removed.Contains(I.InstanceId);});Changed=true;
        for(int32 I=0;I<State.Hotbar.Num();++I)if(Removed.Contains(State.Hotbar[I]) ||
            (State.HotbarDefinitions.IsValidIndex(I)&&AmmoType(State.HotbarDefinitions[I])))
        {State.Hotbar[I].Reset();if(State.HotbarDefinitions.IsValidIndex(I))State.HotbarDefinitions[I].Reset();}
        for(auto& Binding:State.QuickBindings)if(Removed.Contains(Binding.ItemId)||AmmoType(Binding.ItemDefinition))Binding=FColdSteelQuickBinding();
    }
    for(auto& Item:State.Items)
    {
        if (ColdSteelInventory::IsBow(Item))
        {
            const FString Selected = AmmoDefinitionFor(Item);
            if (Item.LoadedAmmoType != Selected) { Item.LoadedAmmoType = Selected; Changed = true; }
            continue;
        }
        const FString Default=AmmoGroupFor(Item);
        if(!Default.IsEmpty()&&Item.LoadedAmmoType.IsEmpty()){Item.LoadedAmmoType=Default;Changed=true;}
        // 201's retired box must not silently discard its excess owned rounds
        // when the character clamps the now-standard 30-round magazine.
        if(Item.Definition==TEXT("ue_lmg201"))
        {
            TSharedPtr<FJsonObject> Data;const TSharedPtr<FJsonObject>* Parts=nullptr;FString MagazinePart;
            if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)&&Data&&
                Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)&&
                (*Parts)->TryGetStringField(TEXT("magazine"),MagazinePart)&&MagazinePart==TEXT("lmg201_ammo_box"))
            {
                const int32 Excess=FMath::Max(0,Item.Magazine-30);
                const int32 Virtual=FMath::Min(Excess,Item.VirtualMagazineAmmo);
                if(Excess>Virtual&&!AddAmmoToState(State,AmmoDefinitionFor(Item),Excess-Virtual))return false;
                Item.Magazine-=Excess;Item.VirtualMagazineAmmo-=Virtual;
                (*Parts)->RemoveField(TEXT("magazine"));
                bool EmptyCycle=true;
                if(Data->TryGetBoolField(TEXT("reload_cycle_empty"),EmptyCycle)&&!EmptyCycle)
                {
                    Data->RemoveField(TEXT("reload_pending_cycle"));
                    Data->RemoveField(TEXT("reload_cycle_empty"));
                }
                Item.Data.Reset();
                FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Item.Data));
                Changed=true;
            }
        }
    }
    if(State.AmmoPouchVersion!=1){State.AmmoPouchVersion=1;Changed=true;}
    return true;
}
bool UColdSteelStatusModel::CanSwitchAmmo(const FString& WeaponId,const FString& Target) const
{
    const auto* Gun=FindItem(WeaponId);const auto* Type=AmmoType(Target);
    return Gun&&Gun->Place==1&&Type&&Type->Enabled&&Type->Group==AmmoGroupFor(*Gun)&&
        AmmoDefinitionFor(*Gun)!=Target&&PouchCount(Target)>0;
}
bool UColdSteelStatusModel::CommitAmmoSwitch(const FString& WeaponId,const FString& Target,int32 Capacity,int32 NeedsCycle,int32 LoadLimit,bool Completed)
{
    if(Capacity<=0||!CurrentPawn.IsValid()||!CanSwitchAmmo(WeaponId,Target))return false;
    SyncRuntime();auto State=Snapshot();
    auto* Gun=State.Items.FindByPredicate([&](const auto& I){return I.InstanceId==WeaponId&&I.Place==1;});
    if(!Gun)return false;
    const int32 Refund=FMath::Max(0,Gun->Magazine-Gun->VirtualMagazineAmmo);
    if(!AddAmmoToState(State,AmmoDefinitionFor(*Gun),Refund))return false;
    // A type change always spends owned rounds, including on the range. Infinite
    // normal reloads remain available, but never unlock unowned ammo types.
    const int32 Loaded=int32(FMath::Min<int64>(FMath::Min(Capacity,LoadLimit),State.AmmoPouch.FindRef(Target)));
    if(Loaded<=0)return false;
    State.AmmoPouch.FindOrAdd(Target)-=Loaded;
    Gun->Magazine=Loaded;Gun->VirtualMagazineAmmo=0;Gun->LoadedAmmoType=Target;
    if(!WeaponReloadStages::SetNeedsCycle(*Gun,NeedsCycle))return false;
    if((Gun->Definition==TEXT("ue_dan_wesson715")||Gun->Definition==TEXT("ue_rsh12")))
    {
        TSharedPtr<FJsonObject> Data;
        if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Gun->Data),Data))
        {Data->SetNumberField(TEXT("revolver_case_count"),Loaded);Gun->Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Gun->Data));}
    }
    if(Completed)ColdSteelSkills::AddExperience(State,DexterousHandsSkill,DexterousHandsSkill.ReloadExperience);
    return CommitState(MoveTemp(State));
}

bool UColdSteelStatusModel::CompleteWeaponReloadCycle(const FString& WeaponId)
{
    const auto* Item=FindItem(WeaponId);
    if(!Item)return false;
    if(!WeaponReloadStages::NeedsCycle(*Item))return true;
    SyncRuntime();auto State=Snapshot();
    auto* Gun=State.Items.FindByPredicate([&](const auto& I){return I.InstanceId==WeaponId;});
    if(!Gun || !WeaponReloadStages::SetNeedsCycle(*Gun,false))return false;
    return CommitState(MoveTemp(State));
}
