#include "CargoWarehouseContainers.h"
#include "Dom/JsonValue.h"

namespace CargoWarehouseContainers
{
TSharedPtr<FJsonObject> Compose(const TSharedPtr<FJsonObject>& Module,int32 Seed,int32 Node)
{
    using J=TSharedPtr<FJsonObject>;
    using V=TSharedPtr<FJsonValue>;
    const J* Rules=nullptr;
    if(!Module->TryGetObjectField(TEXT("warehouse_containers"),Rules))return Module;
    J Out=MakeShared<FJsonObject>(*Module);
    FRandomStream Random(int32(HashCombineFast(uint32(Seed)^0x43415247u,uint32(Node))));
    TSet<FString> Replaced;
    TArray<V> Actors;
    const TArray<V>* Existing=nullptr;
    if(Module->TryGetArrayField(TEXT("runtime_actors"),Existing))Actors=*Existing;
    for(const V& GroupValue:(*Rules)->GetArrayField(TEXT("groups")))
    {
        const J Group=GroupValue->AsObject();
        const auto& Slots=Group->GetArrayField(TEXT("slots"));
        const auto& Counts=Group->GetArrayField(TEXT("pick_count"));
        TArray<int32> Order;
        for(int32 I=0;I<Slots.Num();++I)Order.Add(I);
        for(int32 I=Order.Num()-1;I>0;--I)Order.Swap(I,Random.RandRange(0,I));
        const int32 Count=FMath::Min(Order.Num(),Random.RandRange(int32(Counts[0]->AsNumber()),int32(Counts[1]->AsNumber())));
        TArray<int32> Choices;
        for(int32 I=0;I<Count;++I)
        {
            const J Slot=Slots[Order[I]]->AsObject();
            const auto& Variants=Slot->GetArrayField(TEXT("variants"));
            if(Choices.IsEmpty())
            {
                for(int32 C=0;C<Variants.Num();++C)Choices.Add(C);
                for(int32 C=Choices.Num()-1;C>0;--C)Choices.Swap(C,Random.RandRange(0,C));
            }
            const J Variant=Variants[Choices.Pop(EAllowShrinking::No)]->AsObject();
            Replaced.Add(Slot->GetStringField(TEXT("id")));
            for(const V& ContainerValue:Variant->GetArrayField(TEXT("containers")))
            {
                J Spec=MakeShared<FJsonObject>(*ContainerValue->AsObject());
                const FString Identity=Spec->GetStringField(TEXT("container_id"));
                Spec->SetStringField(TEXT("container_id"),FString::Printf(TEXT("Run%d.Node%d.%s"),Seed,Node,*Identity));
                Actors.Add(MakeShared<FJsonValueObject>(Spec));
            }
        }
    }
    TArray<V> Parts;
    for(const V& Value:Module->GetArrayField(TEXT("parts")))
    {
        FString Slot;Value->AsObject()->TryGetStringField(TEXT("container_replace_slot"),Slot);
        if(!Replaced.Contains(Slot))Parts.Add(Value);
    }
    Out->SetArrayField(TEXT("parts"),Parts);
    Out->SetArrayField(TEXT("runtime_actors"),Actors);
    return Out;
}
}
