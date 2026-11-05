#include "ColdSteelProfileRecovery.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

void ColdSteelProfileRecovery::LoadedAmmo(FColdSteelItem& Into,const FColdSteelItem& From)
{
    Into.Magazine=From.Magazine;Into.Reserve=From.Reserve;
    Into.VirtualMagazineAmmo=From.VirtualMagazineAmmo;Into.LoadedAmmoType=From.LoadedAmmoType;
    if(Into.Data==From.Data)return;
    const TCHAR* const RuntimeKeys[]={TEXT("reload_pending_cycle"),TEXT("reload_cycle_empty"),
        TEXT("m24_interrupted_shot"),TEXT("m24_pending_casing"),TEXT("revolver_case_count")};
    bool HasRuntimeData=false;
    for(const TCHAR* Key:RuntimeKeys)
        if(Into.Data.Contains(Key)||From.Data.Contains(Key)){HasRuntimeData=true;break;}
    if(!HasRuntimeData)return;
    TSharedPtr<FJsonObject> Target,Source;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Into.Data),Target)||!Target||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(From.Data),Source)||!Source)return;
    for(const TCHAR* Key:RuntimeKeys)
    {
        if(const auto* Value=Source->Values.Find(Key))Target->SetField(Key,*Value);
        else Target->RemoveField(Key);
    }
    Into.Data.Reset();FJsonSerializer::Serialize(Target.ToSharedRef(),TJsonWriterFactory<>::Create(&Into.Data));
}
