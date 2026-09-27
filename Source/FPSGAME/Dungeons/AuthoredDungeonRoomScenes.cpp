#include "AuthoredDungeonRoomScenes.h"
#include "Dom/JsonValue.h"

namespace DungeonRoomScenes
{
namespace
{
using FObject = TSharedPtr<FJsonObject>;

FObject Pick(const TArray<TSharedPtr<FJsonValue>>& Candidates, FRandomStream& Random,
    const FString& Family, TMap<FString, FString>& Previous)
{
    TArray<FObject> Choices;
    for (const auto& Value : Candidates)
        if (Value.IsValid() && Value->Type == EJson::Object)
        {
            const auto Object = Value->AsObject();
            FString Id;
            if (Object.IsValid() && Object->TryGetStringField(TEXT("id"), Id) && !Id.IsEmpty()) Choices.Add(Object);
        }
    if (Choices.IsEmpty()) return nullptr;
    if (Choices.Num() > 1)
        if (const FString* Last = Previous.Find(Family))
            Choices.RemoveAll([&](const FObject& Choice) { return Choice->GetStringField(TEXT("id")) == *Last; });
    if (Choices.IsEmpty()) return nullptr;
    const FObject Result = Choices[Random.RandRange(0, Choices.Num() - 1)];
    Previous.Add(Family, Result->GetStringField(TEXT("id")));
    return Result;
}

void Append(const FObject& Destination, const FObject& Source, const TCHAR* Key)
{
    const TArray<TSharedPtr<FJsonValue>>* Extra = nullptr;
    if (!Source->TryGetArrayField(Key, Extra)) return;
    TArray<TSharedPtr<FJsonValue>> Values;
    const TArray<TSharedPtr<FJsonValue>>* Existing = nullptr;
    if (Destination->TryGetArrayField(Key, Existing)) Values = *Existing;
    Values.Append(*Extra);
    Destination->SetArrayField(Key, Values);
}
}

FObject Compose(const FObject& Module, int32 Seed, int32 PieceIndex,
    TMap<FString, FString>& PreviousRecipes, TMap<FString, FString>& PreviousStates)
{
    const TArray<TSharedPtr<FJsonValue>>* Recipes = nullptr;
    if (!Module->TryGetArrayField(TEXT("scene_recipes"), Recipes) || Recipes->IsEmpty()) return Module;
    FString Family = Module->GetStringField(TEXT("id"));
    Module->TryGetStringField(TEXT("family_id"), Family);
    const uint32 RoomSeed = HashCombineFast(uint32(Seed), HashCombineFast(uint32(PieceIndex), GetTypeHash(Family)));
    FRandomStream RecipeRandom(int32(RoomSeed ^ 0x51A7C309u));
    const FObject Recipe = Pick(*Recipes, RecipeRandom, Family, PreviousRecipes);
    if (!Recipe) return Module;

    const FObject Out = MakeShared<FJsonObject>(*Module);
    Out->SetStringField(TEXT("scene_recipe_id"), Recipe->GetStringField(TEXT("id")));
    Append(Out, Recipe, TEXT("parts"));
    Append(Out, Recipe, TEXT("scene_keep_clear"));
    const TArray<TSharedPtr<FJsonValue>>* States = nullptr;
    if (Recipe->TryGetArrayField(TEXT("states"), States))
    {
        FRandomStream StateRandom(int32(RoomSeed ^ 0xA64071D3u));
        if (const FObject State = Pick(*States, StateRandom, Family, PreviousStates))
        {
            Out->SetStringField(TEXT("scene_state_id"), State->GetStringField(TEXT("id")));
            Append(Out, State, TEXT("parts"));
            Append(Out, State, TEXT("scene_keep_clear"));
            double Scale = 1.;
            State->TryGetNumberField(TEXT("light_intensity_scale"), Scale);
            Scale = FMath::Clamp(Scale, .8, 1.);
            TArray<TSharedPtr<FJsonValue>> Lights;
            for (const auto& Value : Module->GetArrayField(TEXT("lights")))
            {
                const FObject Light = MakeShared<FJsonObject>(*Value->AsObject());
                Light->SetNumberField(TEXT("intensity"), Light->GetNumberField(TEXT("intensity")) * Scale);
                Lights.Add(MakeShared<FJsonValueObject>(Light));
            }
            Out->SetArrayField(TEXT("lights"), Lights);
        }
    }
    // Equipment replaces some loose clutter in the budget, not the authored room structure.
    Out->SetNumberField(TEXT("scene_max_floor_props"), 8);
    Out->SetNumberField(TEXT("scene_max_clusters"), 2);
    return Out;
}
}
