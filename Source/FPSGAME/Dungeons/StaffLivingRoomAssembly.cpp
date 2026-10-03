#include "StaffLivingRoomAssembly.h"
#include "Dom/JsonValue.h"

namespace
{
using J=TSharedPtr<FJsonObject>;
using V=TSharedPtr<FJsonValue>;

void ChoosePoses(const J& Module,const TCHAR* Key,FRandomStream& Random,TMap<FString,J>& Poses)
{
    const J* Layout=nullptr;
    if(!Module->TryGetObjectField(Key,Layout))return;
    TArray<int32> Bag;int32 Previous=INDEX_NONE;
    for(const V& Value:(*Layout)->GetArrayField(TEXT("rooms")))
    {
        const auto& Variants=Value->AsObject()->GetArrayField(TEXT("variants"));
        if(Variants.IsEmpty())continue;
        if(Bag.IsEmpty())
        {
            for(int32 I=0;I<Variants.Num();++I)Bag.Add(I);
            for(int32 I=Bag.Num()-1;I>0;--I)Bag.Swap(I,Random.RandRange(0,I));
            if(Bag.Num()>1&&Bag.Last()==Previous)Bag.Swap(Bag.Num()-1,0);
        }
        const int32 Choice=Bag.Pop(EAllowShrinking::No);Previous=Choice;
        for(const V& Placement:Variants[Choice]->AsObject()->GetArrayField(TEXT("placements")))
        {
            const J Pose=Placement->AsObject();Poses.Add(Pose->GetStringField(TEXT("id")),Pose);
        }
    }
}

J ApplyPose(const J& Spec,const FString& Slot,const TMap<FString,J>& Poses)
{
    J Out=MakeShared<FJsonObject>(*Spec);
    if(const J* Pose=Poses.Find(Slot))
    {
        Out->SetArrayField(TEXT("position"),(*Pose)->GetArrayField(TEXT("position_cm")));
        Out->SetNumberField(TEXT("yaw"),(*Pose)->GetNumberField(TEXT("yaw_ue")));
    }
    return Out;
}
}

TSharedPtr<FJsonObject> StaffLivingRoomAssembly::Compose(const J& Module,int32 Seed,int32 Node)
{
    bool Staff=false;Module->TryGetBoolField(TEXT("staff_living"),Staff);
    if(!Staff)return Module;
    J Out=MakeShared<FJsonObject>(*Module);
    FRandomStream Random(int32(HashCombineFast(uint32(Seed)^0x53544146u,uint32(Node))));
    TMap<FString,J> Poses;
    ChoosePoses(Module,TEXT("layout_variants"),Random,Poses);
    ChoosePoses(Module,TEXT("recreation_chair_layout_variants"),Random,Poses);
    TArray<V> Parts;
    for(const V& Value:Module->GetArrayField(TEXT("parts")))
    {
        const J Part=Value->AsObject();FString Slot;
        Part->TryGetStringField(TEXT("layout_slot"),Slot);
        Parts.Add(MakeShared<FJsonValueObject>(ApplyPose(Part,Slot,Poses)));
    }
    Out->SetArrayField(TEXT("parts"),Parts);
    TArray<V> Actors;
    const TArray<V>* Existing=nullptr;
    if(Module->TryGetArrayField(TEXT("runtime_actors"),Existing))Actors=*Existing;
    for(const V& Value:Module->GetArrayField(TEXT("scene_containers")))
    {
        const J Container=Value->AsObject();
        const FString Identity=Container->GetStringField(TEXT("container_id"));
        FString Slot=Identity,LocalSlot;
        if(Identity.Split(TEXT("."),nullptr,&LocalSlot,ESearchCase::CaseSensitive,ESearchDir::FromStart))Slot=LocalSlot;
        Container->TryGetStringField(TEXT("layout_slot"),Slot);
        J Spec=ApplyPose(Container,Slot,Poses);
        Spec->SetStringField(TEXT("type"),TEXT("scene_container"));
        Spec->SetStringField(TEXT("container_id"),FString::Printf(TEXT("Run%d.Node%d.%s"),Seed,Node,*Identity));
        Actors.Add(MakeShared<FJsonValueObject>(Spec));
    }
    Out->SetArrayField(TEXT("runtime_actors"),Actors);
    return Out;
}
