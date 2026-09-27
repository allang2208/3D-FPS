#include "AuthoredDungeonCatalog.h"
#include "Dom/JsonValue.h"

bool DungeonCatalog::ResolveRecipes(const TSharedPtr<FJsonObject>& Catalog,FString& Error)
{
    const TSharedPtr<FJsonObject>* Library=nullptr;
    if(!Catalog->TryGetObjectField(TEXT("room_recipe_library"),Library))return true;
    const TSharedPtr<FJsonObject>* Shells=nullptr;const TSharedPtr<FJsonObject>* Interiors=nullptr;
    if(!(*Library)->TryGetObjectField(TEXT("shells"),Shells)||!(*Library)->TryGetObjectField(TEXT("interiors"),Interiors))
    {Error=TEXT("房间共享配方缺少外壳或内部组合表");return false;}
    TArray<TSharedPtr<FJsonValue>> Resolved;
    for(const auto& V:Catalog->GetArrayField(TEXT("modules")))
    {
        const auto Module=V->AsObject();FString ShellId,InteriorId;
        if(!Module->TryGetStringField(TEXT("shell_id"),ShellId)){Resolved.Add(V);continue;}
        Module->TryGetStringField(TEXT("interior_recipe_id"),InteriorId);
        const TSharedPtr<FJsonObject>* Shell=nullptr;const TSharedPtr<FJsonObject>* Interior=nullptr;
        if(!(*Shells)->TryGetObjectField(ShellId,Shell)||!(*Interiors)->TryGetObjectField(InteriorId,Interior))
        {Error=TEXT("房间引用了不存在的外壳/内部配方：")+Module->GetStringField(TEXT("id"));return false;}
        const TArray<TSharedPtr<FJsonValue>>* Compatible=nullptr;
        if((*Interior)->TryGetArrayField(TEXT("compatibility_shells"),Compatible)&&
           !Compatible->ContainsByPredicate([&](const auto& Value){return Value->AsString()==ShellId;}))
        {Error=TEXT("房壳与内部配方不兼容：")+ShellId+TEXT(" / ")+InteriorId;return false;}
        const auto Out=MakeShared<FJsonObject>(**Shell);
        for(const auto& Field:(*Interior)->Values)Out->SetField(Field.Key,Field.Value);
        for(const auto& Field:Module->Values)Out->SetField(Field.Key,Field.Value);
        TArray<TSharedPtr<FJsonValue>> Parts=(*Shell)->GetArrayField(TEXT("parts"));
        Parts.Append((*Interior)->GetArrayField(TEXT("parts")));
        const TArray<TSharedPtr<FJsonValue>>* Extra=nullptr;
        if(Module->TryGetArrayField(TEXT("parts"),Extra))Parts.Append(*Extra);
        Out->SetArrayField(TEXT("parts"),Parts);
        const TArray<TSharedPtr<FJsonValue>>* Anchors=nullptr;
        if(Out->TryGetArrayField(TEXT("encounter_anchors"),Anchors))Out->SetArrayField(TEXT("anchors"),*Anchors);
        // Resolved modules no longer need a second expansion in this transient copy.
        Out->SetStringField(TEXT("resolved_shell_id"),ShellId);Out->RemoveField(TEXT("shell_id"));
        Resolved.Add(MakeShared<FJsonValueObject>(Out));
    }
    Catalog->SetArrayField(TEXT("modules"),Resolved);return true;
}
