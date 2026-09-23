#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

// Owns immutable parse results only. Callers editing JSON must parse a private copy.
class FColdSteelJsonReadCache
{
    struct FKeys : TDefaultMapHashableKeyFuncs<FString,TSharedPtr<const FJsonObject>,false>
    {
        static bool Matches(const FString& A,const FString& B)
        {return A.Equals(B,ESearchCase::CaseSensitive);}
    };
    TMap<FString,TSharedPtr<const FJsonObject>,FDefaultSetAllocator,FKeys> Entries;
    TArray<FString> Order;
    int32 Next=0;
public:
    TSharedPtr<const FJsonObject> Get(const FString& Key,TFunctionRef<TSharedPtr<const FJsonObject>()> Parse)
    {
        if(const auto* Found=Entries.Find(Key))return *Found;
        const auto Value=Parse();
        constexpr int32 Capacity=128;
        if(Order.Num()<Capacity)Order.Add(Key);
        else {Entries.Remove(Order[Next]);Order[Next]=Key;Next=(Next+1)%Capacity;}
        Entries.Add(Key,Value);
        return Value;
    }
};

namespace ColdSteelItemData
{
    TSharedPtr<const FJsonObject> Read(const FString& Json);
}
