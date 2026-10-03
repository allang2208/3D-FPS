#include "StaffDormitoryLayout.h"

#include "Components/SceneComponent.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

AStaffDormitoryLayout::AStaffDormitoryLayout()
{
    PrimaryActorTick.bCanEverTick=false;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("LayoutOrigin")));
}

void AStaffDormitoryLayout::BeginPlay()
{
    Super::BeginPlay();
    TSharedPtr<FJsonObject> Config;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(LayoutJson),Config)||!Config.IsValid())return;
    const TArray<TSharedPtr<FJsonValue>>* Rooms=nullptr;
    if(!Config->TryGetArrayField(TEXT("rooms"),Rooms))return;
    TMap<FString,AActor*> Slots;
    const FString Prefix(TEXT("StaffDormitory.LayoutSlot."));
    for(const auto& Entry:LayoutActors)
    {
        auto* Actor=Entry.Get();
        if(IsValid(Actor))for(const FName Tag:Actor->Tags)
            if(Tag.ToString().StartsWith(Prefix)){Slots.Add(Tag.ToString().RightChop(Prefix.Len()),Actor);break;}
    }
    FRandomStream Random(RandomSeed<0?FMath::Rand():RandomSeed);
    TArray<int32> Bag;
    int32 PreviousChoice=INDEX_NONE;
    for(const auto& RoomValue:*Rooms)
    {
        const auto Room=RoomValue->AsObject();
        const TArray<TSharedPtr<FJsonValue>>* Variants=nullptr;
        if(!Room.IsValid()||!Room->TryGetArrayField(TEXT("variants"),Variants)||Variants->IsEmpty())continue;
        if(Bag.IsEmpty())
        {
            for(int32 I=0;I<Variants->Num();++I)Bag.Add(I);
            for(int32 I=Bag.Num()-1;I>0;--I)Bag.Swap(I,Random.RandRange(0,I));
            if(Bag.Num()>1&&Bag.Last()==PreviousChoice)Bag.Swap(Bag.Num()-1,0);
        }
        const int32 Choice=Bag.Pop(EAllowShrinking::No);PreviousChoice=Choice;
        const auto Variant=(*Variants)[Choice]->AsObject();
        const TArray<TSharedPtr<FJsonValue>>* Placements=nullptr;
        if(!Variant.IsValid()||!Variant->TryGetArrayField(TEXT("placements"),Placements))continue;
        for(const auto& PlacementValue:*Placements)
        {
            const auto Pose=PlacementValue->AsObject();
            FString Slot;double Yaw=0;
            const TArray<TSharedPtr<FJsonValue>>* Position=nullptr;
            if(!Pose.IsValid()||!Pose->TryGetStringField(TEXT("id"),Slot)
                ||!Pose->TryGetArrayField(TEXT("position_cm"),Position)||Position->Num()!=3)continue;
            AActor* Actor=Slots.FindRef(Slot);
            if(!IsValid(Actor))continue;
            Pose->TryGetNumberField(TEXT("yaw_ue"),Yaw);
            const FVector Local((*Position)[0]->AsNumber(),(*Position)[1]->AsNumber(),(*Position)[2]->AsNumber());
            const FQuat Facing=GetActorQuat()*FRotator(0,Yaw,0).Quaternion();
            Actor->SetActorLocationAndRotation(GetActorTransform().TransformPosition(Local),Facing,false,nullptr,ETeleportType::TeleportPhysics);
        }
    }
}
