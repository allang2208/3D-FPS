#include "StaffCatalog.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace ColdSteelStaff
{
TSharedPtr<FJsonObject> Catalog()
{
    static const auto Root=[](){FString S;TSharedPtr<FJsonObject> O;
        if(FFileHelper::LoadFileToString(S,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/staff-gunsmith.json"))))
            FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(S),O);return O;}();
    return Root;
}
FParts Installed(const FColdSteelItem& Item)
{
    FParts Result;TSharedPtr<FJsonObject> D;const TSharedPtr<FJsonObject>* P=nullptr;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),D)||!D)return Result;
    if(!D->TryGetObjectField(TEXT("gunsmith_parts"),P))D->TryGetObjectField(TEXT("_craftData"),P);
    if(P)for(const auto& V:(*P)->Values){FString Id;if(V.Value->TryGetString(Id)&&!Id.IsEmpty()&&Id!=TEXT("false"))Result.Add(FString(*V.Key),Id);}
    return Result;
}
FColdSteelItem Resolve(const FColdSteelItem& Item,const FParts* Draft)
{
    FColdSteelItem R=Item;if(!IsStaff(Item))return R;
    const auto C=Catalog();TSharedPtr<FJsonObject> D;
    if(!C||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),D)||!D)return R;
    const auto Parts=Draft?*Draft:Installed(Item);auto Effects=MakeShared<FJsonObject>();auto Valid=MakeShared<FJsonObject>();
    FString Specialty;
    // Head specialty is resolved before conditional crown effects, independent of map order.
    for(const auto& V:C->GetArrayField(TEXT("columns")))
    {
        const auto Col=V->AsObject();if(Col->GetStringField(TEXT("key"))!=TEXT("head_crystal"))continue;
        for(const auto& O:Col->GetArrayField(TEXT("options")))if(O->AsObject()->GetStringField(TEXT("id"))==Parts.FindRef(TEXT("head_crystal")))
            O->AsObject()->GetObjectField(TEXT("effects"))->TryGetStringField(TEXT("staffSpecialty"),Specialty);
    }
    for(const auto& V:C->GetArrayField(TEXT("columns")))
    {
        const auto Col=V->AsObject();const FString Slot=Col->GetStringField(TEXT("key"));
        D->SetStringField(TEXT("staff_part_")+Slot+TEXT("_mesh"),Col->GetStringField(TEXT("factory_mesh")));
        for(const auto& O:Col->GetArrayField(TEXT("options")))
        {
            const auto Part=O->AsObject();if(Part->GetStringField(TEXT("id"))!=Parts.FindRef(Slot))continue;
            Valid->SetStringField(Slot,Parts.FindRef(Slot));D->SetStringField(TEXT("staff_part_")+Slot+TEXT("_mesh"),Part->GetStringField(TEXT("mesh")));
            FString Required;Part->TryGetStringField(TEXT("requires_specialty"),Required);
            if(!Required.IsEmpty()&&Required!=Specialty)continue;
            for(const auto& Effect:Part->GetObjectField(TEXT("effects"))->Values)
            {
                const FString Key(*Effect.Key);double N=0,Previous=0;
                if(Effect.Value->TryGetNumber(N)){Effects->TryGetNumberField(Key,Previous);Effects->SetNumberField(Key,Previous+N);}
                else Effects->SetField(Key,Effect.Value);
            }
        }
    }
    D->SetObjectField(TEXT("gunsmith_parts"),Valid);D->SetObjectField(TEXT("_craftEffects"),Effects);
    D->SetNumberField(TEXT("staff_revision"),1);R.Data.Reset();
    FJsonSerializer::Serialize(D.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&R.Data));
    R.Magazine=R.Reserve=R.VirtualMagazineAmmo=0;return R;
}
int32 TicketCount(const FColdSteelProfile& State)
{
    int64 Count=0;for(const auto& I:State.Items)if(I.Definition==TEXT("reforge_ticket")&&(I.Place==0||(I.Place==4&&I.Container.IsEmpty())))Count+=I.Count;
    return int32(FMath::Min<int64>(Count,MAX_int32));
}
bool DebitTickets(FColdSteelProfile& State,int32 Cost)
{
    if(Cost<0||TicketCount(State)<Cost)return false;
    for(auto& I:State.Items)if(Cost&&I.Definition==TEXT("reforge_ticket")&&(I.Place==0||(I.Place==4&&I.Container.IsEmpty())))
    {const int32 N=int32(FMath::Min<int64>(I.Count,Cost));I.Count-=N;Cost-=N;}
    State.Items.RemoveAll([](const auto& I){return I.Count<=0;});return true;
}
}
