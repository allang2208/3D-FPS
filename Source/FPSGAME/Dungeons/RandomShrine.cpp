#include "RandomShrine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

const TSharedPtr<FJsonObject>& RandomShrine::Catalog()
{
    static const TSharedPtr<FJsonObject> Data=[]()
    {
        FString Json;TSharedPtr<FJsonObject> Result;
        if(!FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/shrines.json")))||
           !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Result))
            UE_LOG(LogTemp,Error,TEXT("SHRINE shared catalog unavailable"));
        return Result;
    }();
    return Data;
}

TSharedPtr<FJsonObject> RandomShrine::Choose(FRandomStream& Random,const TSharedPtr<FJsonObject>& Fallback)
{
    const auto& Data=Catalog().IsValid()?Catalog():Fallback;
    const TArray<TSharedPtr<FJsonValue>>* Choices=nullptr;
    if(!Data||!Data->TryGetArrayField(TEXT("statues"),Choices)||Choices->IsEmpty())return nullptr;
    return (*Choices)[Random.RandRange(0,Choices->Num()-1)]->AsObject();
}

void RandomShrine::AddMeshPaths(TArray<FSoftObjectPath>& Paths)
{
    const auto& Data=Catalog();const TArray<TSharedPtr<FJsonValue>>* Choices=nullptr;
    if(Data&&Data->TryGetArrayField(TEXT("statues"),Choices))
        for(const auto& Choice:*Choices)Paths.AddUnique(FSoftObjectPath(Choice->AsObject()->GetStringField(TEXT("mesh"))));
}
