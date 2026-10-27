#include "CampfireFoodCatalog.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

const TArray<FCampfireFoodVisual>& CampfireFood::Catalog()
{
    static const TArray<FCampfireFoodVisual> Entries=[]
    {
        TArray<FCampfireFoodVisual> Result;FString Text;TSharedPtr<FJsonObject> Root;
        if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/campfire-recipes.json")))
            ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)return Result;
        const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;if(!Root->TryGetArrayField(TEXT("recipes"),Rows))return Result;
        for(const auto& Row:*Rows)
        {
            const auto O=Row->AsObject();if(!O)continue;bool Enabled=true;O->TryGetBoolField(TEXT("enabled"),Enabled);if(!Enabled)continue;
            const TSharedPtr<FJsonObject>* P=nullptr,*In=nullptr,*Out=nullptr;
            if(!O->TryGetObjectField(TEXT("presentation"),P)||!O->TryGetObjectField(TEXT("input"),In)||!O->TryGetObjectField(TEXT("output"),Out))continue;
            FCampfireFoodVisual V;FString Id;O->TryGetStringField(TEXT("id"),Id);V.Recipe=FName(*Id);
            (*In)->TryGetStringField(TEXT("item"),V.Raw);(*Out)->TryGetStringField(TEXT("item"),V.Cooked);
            (*P)->TryGetStringField(TEXT("rawMesh"),V.RawMesh);(*P)->TryGetStringField(TEXT("cookedMesh"),V.CookedMesh);
            V.MotionProfile=V.Cooked;(*P)->TryGetStringField(TEXT("motionProfile"),V.MotionProfile);
            const TArray<TSharedPtr<FJsonValue>>* Anchor=nullptr;
            if((*P)->TryGetArrayField(TEXT("spitAnchor"),Anchor)&&Anchor->Num()==3)
            {V.bCustomSpit=true;V.SpitAnchor=FVector((*Anchor)[0]->AsNumber(),(*Anchor)[1]->AsNumber(),(*Anchor)[2]->AsNumber());}
            if(!V.Recipe.IsNone()&&!V.Raw.IsEmpty()&&!V.Cooked.IsEmpty()&&!V.RawMesh.IsEmpty()&&!V.CookedMesh.IsEmpty())Result.Add(MoveTemp(V));
        }
        return Result;
    }();
    return Entries;
}
const FCampfireFoodVisual* CampfireFood::Cooked(const FString& Definition)
{return Catalog().FindByPredicate([&](const auto& V){return V.Cooked==Definition;});}
bool CampfireFood::Contains(const FString& Definition)
{return Catalog().ContainsByPredicate([&](const auto& V){return V.Raw==Definition||V.Cooked==Definition;});}
