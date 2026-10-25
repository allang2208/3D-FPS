#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Misc/PackageName.h"
#include "UObject/SoftObjectPath.h"

namespace FPSBodyOutfitResources
{
inline FName FittedShirt(const TSharedPtr<FJsonObject>& Recipe,FName Requested)
{
    if(!Recipe||Requested.IsNone())return NAME_None;
    const TSharedPtr<FJsonObject>* Variants=nullptr;FString Path;
    return Recipe->TryGetObjectField(TEXT("world_mesh_by_shirt"),Variants)
        &&(*Variants)->TryGetStringField(Requested.ToString(),Path)&&!Path.IsEmpty()?Requested:NAME_None;
}
inline FString StringForShirt(const TSharedPtr<FJsonObject>& Recipe,const TCHAR* Field,FName Shirt)
{
    FString Path;if(!Recipe)return Path;Recipe->TryGetStringField(Field,Path);
    const TSharedPtr<FJsonObject>* Variants=nullptr;
    if(!Shirt.IsNone()&&Recipe->TryGetObjectField(FString(Field)+TEXT("_by_shirt"),Variants))
        (*Variants)->TryGetStringField(Shirt.ToString(),Path);
    return Path;
}
// A selected legacy recipe can contain shirt-dependent backpack variants and
// both material override maps. Read its paths without loading the whole catalog.
inline void Gather(const TSharedPtr<FJsonValue>& Value, TSet<FSoftObjectPath>& Out)
{
    if (!Value) return;
    if (Value->Type == EJson::String)
    {
        const FString Path = Value->AsString();
        if (Path.StartsWith(TEXT("/Game/")) || Path.StartsWith(TEXT("/Engine/")))
            Out.Add(FSoftObjectPath(Path.Contains(TEXT(".")) ? Path : Path + TEXT(".") + FPackageName::GetShortName(Path)));
    }
    else if (Value->Type == EJson::Object)
        for (const auto& Pair : Value->AsObject()->Values) Gather(Pair.Value, Out);
    else if (Value->Type == EJson::Array)
        for (const auto& Element : Value->AsArray()) Gather(Element, Out);
}
inline void GatherSelected(const TSharedPtr<FJsonValue>& Value,FName Shirt,TSet<FSoftObjectPath>& Out)
{
    if(!Value)return;
    if(Value->Type!=EJson::Object){Gather(Value,Out);return;}
    const auto Object=Value->AsObject();
    for(const auto& Pair:Object->Values)
    {
        const FString Key(*Pair.Key);
        if(Key.EndsWith(TEXT("_by_shirt")))continue;
        auto Selected=Pair.Value;const TSharedPtr<FJsonObject>* Variants=nullptr;
        if(!Shirt.IsNone()&&Object->TryGetObjectField(Key+TEXT("_by_shirt"),Variants))
            if(auto Variant=(*Variants)->TryGetField(Shirt.ToString()))Selected=Variant;
        GatherSelected(Selected,Shirt,Out);
    }
}
inline void GatherOutfit(const TSharedPtr<FJsonValue>& Recipe,FName Requested,TSet<FSoftObjectPath>& Out)
{
    const FName Shirt=Recipe&&Recipe->Type==EJson::Object?FittedShirt(Recipe->AsObject(),Requested):NAME_None;
    GatherSelected(Recipe,Shirt,Out);
}
}
