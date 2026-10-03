#include "StationWorkshopAssembly.h"
#include "Dom/JsonValue.h"

TSharedPtr<FJsonObject> StationWorkshopAssembly::Compose(const TSharedPtr<FJsonObject>& Module,int32 Seed,int32 Node)
{
    using J=TSharedPtr<FJsonObject>;
    using V=TSharedPtr<FJsonValue>;
    const J* Rules=nullptr;
    if(!Module->TryGetObjectField(TEXT("station_workshop"),Rules))return Module;
    const auto& Variants=(*Rules)->GetArrayField(TEXT("variants"));
    if(Variants.IsEmpty())return Module;
    FRandomStream Random(int32(HashCombineFast(uint32(Seed)^0x5354574Bu,uint32(Node))));
    const J Variant=Variants[Random.RandRange(0,Variants.Num()-1)]->AsObject();
    J Out=MakeShared<FJsonObject>(*Module);
    Out->SetStringField(TEXT("station_workshop_variant"),Variant->GetStringField(TEXT("id")));
    TArray<V> Parts=Module->GetArrayField(TEXT("parts"));
    Parts.Append(Variant->GetArrayField(TEXT("parts")));
    Out->SetArrayField(TEXT("parts"),Parts);
    TArray<V> Actors;
    const TArray<V>* Existing=nullptr;
    if(Module->TryGetArrayField(TEXT("runtime_actors"),Existing))Actors=*Existing;
    for(const V& Value:Variant->GetArrayField(TEXT("containers")))
    {
        J Spec=MakeShared<FJsonObject>(*Value->AsObject());
        const FString Identity=Spec->GetStringField(TEXT("container_id"));
        Spec->SetStringField(TEXT("container_id"),FString::Printf(TEXT("Run%d.Node%d.%s"),Seed,Node,*Identity));
        Actors.Add(MakeShared<FJsonValueObject>(Spec));
    }
    Out->SetArrayField(TEXT("runtime_actors"),Actors);
    return Out;
}
