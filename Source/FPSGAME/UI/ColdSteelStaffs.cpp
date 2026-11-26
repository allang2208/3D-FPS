#include "ColdSteelStatusModel.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void UColdSteelStatusModel::LoadStaffDefinitions()
{
    FString S;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(S,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/staffs.json")))||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(S),Root)||!Root)return;
    for(const auto& Pair:Root->Values)
    {FString Data;FJsonSerializer::Serialize(Pair.Value->AsObject().ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Data));Definitions.Add(FString(*Pair.Key),Data);}
}
bool UColdSteelStatusModel::NormalizeStaffState(FColdSteelProfile& State) const
{
    const auto NormalizeItem=[this](FColdSteelItem& I)
    {
        const FString& Definition=ColdSteelStaff::CanonicalDefinition(I.Definition);
        if(Definition!=TEXT("ue_apprentice_staff")&&!ColdSteelStaff::IsStaff(I))return false;
        const auto* Source=Definitions.Find(Definition);if(!Source)return false;
        TSharedPtr<FJsonObject> D,Defaults;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),D)||!D||
            !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Source),Defaults)||!Defaults)return false;
        FString Type;
        if(!Defaults->TryGetStringField(TEXT("weaponType"),Type)||Type!=TEXT("staff"))return false;
        FString PreviousData=MoveTemp(I.Data);
        const bool ChangedIdentity=I.Definition!=Definition;
        const bool HadAmmo=I.Magazine!=0||I.Reserve!=0||I.VirtualMagazineAmmo!=0||!I.LoadedAmmoType.IsEmpty();
        I.Definition=Definition;
        for(const auto& F:Defaults->Values)if(!D->HasField(FString(*F.Key)))D->SetField(FString(*F.Key),F.Value);
        ColdSteelStaff::ApplyEquipmentDefinition(*D,*Defaults);
        FJsonSerializer::Serialize(D.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&I.Data));
        I=ColdSteelStaff::Resolve(I);
        I.LoadedAmmoType.Reset();
        return ChangedIdentity||HadAmmo||PreviousData!=I.Data;
    };
    bool Changed=false;
    for(auto& I:State.Items)Changed|=NormalizeItem(I);
    if(!State.EnhancementItem.InstanceId.IsEmpty())Changed|=NormalizeItem(State.EnhancementItem);
    if(!State.WoodworkingJob.Item.InstanceId.IsEmpty())Changed|=NormalizeItem(State.WoodworkingJob.Item);
    const auto UpdateDefinition=[&Changed](FString& Id)
    {
        const FString& Canonical=ColdSteelStaff::CanonicalDefinition(Id);
        if(Id!=Canonical){Id=Canonical;Changed=true;}
    };
    for(auto& Id:State.HotbarDefinitions)UpdateDefinition(Id);
    for(auto& Binding:State.QuickBindings)UpdateDefinition(Binding.ItemDefinition);
    const int32 OldReceipts=State.ArmoryReceived.RemoveAll([](const FString& Id){return ColdSteelStaff::CanonicalDefinition(Id)!=Id;});
    if(OldReceipts){State.ArmoryReceived.AddUnique(TEXT("ue_apprentice_staff"));Changed=true;}
    return Changed;
}
