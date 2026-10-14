#include "ColdSteelProfileRecovery.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

void ColdSteelProfileRecovery::LoadedAmmo(FColdSteelItem& Into,const FColdSteelItem& From)
{
    Into.Magazine=From.Magazine;Into.Reserve=From.Reserve;
    Into.VirtualMagazineAmmo=From.VirtualMagazineAmmo;Into.LoadedAmmoType=From.LoadedAmmoType;
    if(Into.Data==From.Data)return;
    const bool HasRuntimeData=Into.Data.Contains(TEXT("reload_pending_cycle"))||From.Data.Contains(TEXT("reload_pending_cycle"))||
        Into.Data.Contains(TEXT("revolver_case_count"))||From.Data.Contains(TEXT("revolver_case_count"));
    if(!HasRuntimeData)return;
    TSharedPtr<FJsonObject> Target,Source;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Into.Data),Target)||!Target||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(From.Data),Source)||!Source)return;
    for(const TCHAR* Key:{TEXT("reload_pending_cycle"),TEXT("reload_cycle_empty"),TEXT("revolver_case_count")})
    {
        if(const auto* Value=Source->Values.Find(Key))Target->SetField(Key,*Value);
        else Target->RemoveField(Key);
    }
    Into.Data.Reset();FJsonSerializer::Serialize(Target.ToSharedRef(),TJsonWriterFactory<>::Create(&Into.Data));
}
