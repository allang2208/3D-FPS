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
void UColdSteelStatusModel::NormalizeStaffState(FColdSteelProfile& State) const
{
    for(auto& I:State.Items)
    {
        if(!ColdSteelStaff::IsStaff(I))continue;
        // Only the known legacy apprentice IDs belong to this migrated definition.
        if(I.Definition==TEXT("apprentice_staff")||I.Definition==TEXT("weapon20"))I.Definition=TEXT("ue_apprentice_staff");
        const auto* Source=Definitions.Find(I.Definition);if(!Source)continue;
        TSharedPtr<FJsonObject> D,Defaults;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),D)||!D||
            !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Source),Defaults)||!Defaults)continue;
        for(const auto& F:Defaults->Values)if(!D->HasField(FString(*F.Key)))D->SetField(FString(*F.Key),F.Value);
        // Equipment semantics are authoritative even for old instance snapshots.
        D->SetBoolField(TEXT("isTwoHanded"),false);
        D->SetStringField(TEXT("weaponCategory"),TEXT("mainhand"));
        D->SetStringField(TEXT("equipSlot"),TEXT("weapon"));
        I.Data.Reset();FJsonSerializer::Serialize(D.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&I.Data));
        I=ColdSteelStaff::Resolve(I);
    }
}
