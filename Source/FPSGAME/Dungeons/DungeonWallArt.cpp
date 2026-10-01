#include "DungeonWallArt.h"

namespace
{
    using J=TSharedPtr<FJsonObject>;
    FVector WallArtVector(const J& O,const TCHAR* Key)
    {
        const auto& V=O->GetArrayField(Key);
        return FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber());
    }
    void VectorField(const J& O,const TCHAR* Key,const FVector& V)
    {
        O->SetArrayField(Key,{MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)});
    }
    template<typename T> void Shuffle(TArray<T>& Values,FRandomStream& Random)
    {
        for(int32 I=Values.Num()-1;I>0;--I)Values.Swap(I,Random.RandRange(0,I));
    }
}

TArray<TSharedPtr<FJsonValue>> DungeonWallArt::Build(const J& Module,int32 Seed,int32 ModuleIndex)
{
    TArray<TSharedPtr<FJsonValue>> Parts;
    const TSharedPtr<FJsonObject>* Recipe=nullptr;
    if(!Module->TryGetObjectField(TEXT("wall_art"),Recipe))return Parts;
    const J Pools=(*Recipe)->GetObjectField(TEXT("pools"));
    TSet<FString> Used;TArray<FBox> Occupied;
    for(const auto& Value:(*Recipe)->GetArrayField(TEXT("groups")))
    {
        const J Group=Value->AsObject();
        FRandomStream Random(int32(HashCombineFast(uint32(Seed)^0x41525457u,
            HashCombineFast(uint32(ModuleIndex),GetTypeHash(Group->GetStringField(TEXT("id")))))));
        TArray<TSharedPtr<FJsonValue>> Slots=Group->GetArrayField(TEXT("slots"));
        TArray<TSharedPtr<FJsonValue>> Choices=Pools->GetArrayField(Group->GetStringField(TEXT("pool")));
        Shuffle(Slots,Random);Shuffle(Choices,Random);
        const int32 Wanted=Random.RandRange(Group->GetIntegerField(TEXT("min_count")),Group->GetIntegerField(TEXT("max_count")));
        int32 Made=0;
        FString Fallback;Group->TryGetStringField(TEXT("fallback_pool"),Fallback);
        for(const auto& SlotValue:Slots)
        {
            const J Slot=SlotValue->AsObject();
            TArray<TSharedPtr<FJsonValue>> Candidates=Choices;
            if(Made>=Wanted)
            {
                if(Fallback.IsEmpty())break;
                Candidates=Pools->GetArrayField(Fallback);
            }
            for(const auto& Candidate:Candidates)
            {
                const J Art=Candidate->AsObject();const FString Id=Art->GetStringField(TEXT("id"));
                bool Repeat=false;Group->TryGetBoolField(TEXT("allow_repeat"),Repeat);
                if(!Repeat&&Used.Contains(Id))continue;
                const FVector Extent=WallArtVector(Art,TEXT("extent"));
                const double Scale=Art->GetNumberField(TEXT("scale"));
                const double HalfWidth=Extent.X*Scale,HalfHeight=Extent.Z*Scale;
                const double AvailableX=Slot->GetNumberField(TEXT("half_width"))-HalfWidth;
                const double AvailableZ=Slot->GetNumberField(TEXT("half_height"))-HalfHeight;
                if(AvailableX<0||AvailableZ<0)continue;
                const FRotator Rotation(0,Slot->GetNumberField(TEXT("yaw")),0);
                FVector Center=WallArtVector(Slot,TEXT("center"));
                const double Jitter=Slot->GetNumberField(TEXT("jitter"));
                Center+=Rotation.RotateVector(FVector(Random.FRandRange(-1,1)*FMath::Min(Jitter,AvailableX),0,
                    Random.FRandRange(-1,1)*FMath::Min(Jitter*.5,AvailableZ)));
                // A separate placement envelope prevents art from stacking even if
                // author slots are later edited to intersect. Actual geometry stays flat.
                const FVector LocalHalf(HalfWidth+12,2,HalfHeight+12);
                const FBox Bounds=FBox(-LocalHalf,LocalHalf).TransformBy(FTransform(Rotation,Center));
                bool Overlap=false;for(const FBox& Other:Occupied)if(Bounds.Intersect(Other)){Overlap=true;break;}
                if(Overlap)continue;
                J Part=MakeShared<FJsonObject>();Part->SetStringField(TEXT("mesh"),Art->GetStringField(TEXT("mesh")));
                VectorField(Part,TEXT("position"),Center-Rotation.RotateVector(WallArtVector(Art,TEXT("origin"))*Scale));
                VectorField(Part,TEXT("scale"),FVector(Scale));Part->SetNumberField(TEXT("yaw"),Rotation.Yaw);
                Part->SetBoolField(TEXT("collision"),false);Part->SetBoolField(TEXT("affects_navigation"),false);
                Part->SetBoolField(TEXT("fluid"),false);Part->SetBoolField(TEXT("cast_shadow"),false);
                Part->SetBoolField(TEXT("wall_art"),true);
                Part->SetArrayField(TEXT("materials"),Art->GetArrayField(TEXT("materials")));
                Parts.Add(MakeShared<FJsonValueObject>(Part));Occupied.Add(Bounds);Used.Add(Id);++Made;break;
            }
        }
    }
    return Parts;
}
