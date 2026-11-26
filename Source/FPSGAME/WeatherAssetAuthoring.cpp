#include "WeatherAssetAuthoring.h"
#include "WeatherViewEffectsComponent.h"
#include "Materials/MaterialInterface.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"
#include "UObject/GarbageCollection.h"
#if WITH_EDITOR
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UObject/SavePackage.h"
#endif

bool UWeatherAssetAuthoring::SaveWetMaterialIndex(const FString& PackageName,const TMap<FString,FString>& Paths)
{
#if WITH_EDITOR
    auto* Package=CreatePackage(*PackageName);
    auto* Asset=FindObject<UWeatherPresentationAssets>(Package,*FPackageName::GetShortName(PackageName));
    if(!Asset)
    {
        Asset=NewObject<UWeatherPresentationAssets>(Package,*FPackageName::GetShortName(PackageName),RF_Public|RF_Standalone);
        FAssetRegistryModule::AssetCreated(Asset);
    }
    Asset->WetMaterials.Reset();Asset->WetMaterialPaths.Reset();
    for(const auto& Entry:Paths)Asset->WetMaterialPaths.Add(FName(*Entry.Key),TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(Entry.Value)));
    Package->MarkPackageDirty();
    FSavePackageArgs Args;Args.TopLevelFlags=RF_Public|RF_Standalone;Args.SaveFlags=SAVE_NoError;
    const FString Filename=FPackageName::LongPackageNameToFilename(PackageName,FPackageName::GetAssetPackageExtension());
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Filename),true);
    return UPackage::SavePackage(Package,Asset,*Filename,Args);
#else
    return false;
#endif
}

FString UWeatherAssetAuthoring::DescribeWeatherInterface(UObject* Object)
{
    if(!Object)return TEXT("{}");
    auto Root=MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> Functions;
    const auto Relevant=[](const FString& Name)
    {return Name.Contains(TEXT("Weather"))||Name.Contains(TEXT("Exposure"))||Name.Contains(TEXT("Lightning"))||Name.Contains(TEXT("Thunder"))||Name.Contains(TEXT("Sound"))||Name.Contains(TEXT("Rain"));};
    for(TFieldIterator<UFunction> It(Object->GetClass());It;++It)if(Relevant(It->GetName()))
    {
        auto Function=MakeShared<FJsonObject>();Function->SetStringField(TEXT("name"),It->GetName());
        TArray<TSharedPtr<FJsonValue>> Params;
        for(TFieldIterator<FProperty> P(*It);P;++P)if(P->HasAnyPropertyFlags(CPF_Parm))
        {
            auto Param=MakeShared<FJsonObject>();Param->SetStringField(TEXT("name"),P->GetName());
            Param->SetStringField(TEXT("type"),P->GetCPPType());Param->SetBoolField(TEXT("out"),P->HasAnyPropertyFlags(CPF_OutParm));
            Param->SetBoolField(TEXT("return"),P->HasAnyPropertyFlags(CPF_ReturnParm));Params.Add(MakeShared<FJsonValueObject>(Param));
        }
        Function->SetArrayField(TEXT("params"),Params);Functions.Add(MakeShared<FJsonValueObject>(Function));
    }
    Root->SetArrayField(TEXT("functions"),Functions);
    auto Props=MakeShared<FJsonObject>();
    for(TFieldIterator<FProperty> P(Object->GetClass());P;++P)if(Relevant(P->GetName()))
    {
        auto Prop=MakeShared<FJsonObject>();Prop->SetStringField(TEXT("type"),P->GetCPPType());
        FString Value;P->ExportText_InContainer(0,Value,Object,Object,Object,PPF_None);Prop->SetStringField(TEXT("value"),Value.Left(500));
        if(auto* Delegate=CastField<FMulticastDelegateProperty>(*P))
        {
            TArray<TSharedPtr<FJsonValue>> Params;
            for(TFieldIterator<FProperty> Arg(Delegate->SignatureFunction);Arg;++Arg)if(Arg->HasAnyPropertyFlags(CPF_Parm))
                Params.Add(MakeShared<FJsonValueString>(Arg->GetName()+TEXT(":")+Arg->GetCPPType()));
            Prop->SetArrayField(TEXT("params"),Params);
        }
        Props->SetObjectField(P->GetName(),Prop);
    }
    Root->SetObjectField(TEXT("properties"),Props);
    FString Result;auto Writer=TJsonWriterFactory<>::Create(&Result);FJsonSerializer::Serialize(Root,Writer);return Result;
}

void UWeatherAssetAuthoring::ReleaseAuthoringBatch()
{
#if WITH_EDITOR
    if(IsRunningCommandlet())CollectGarbage(RF_NoFlags,true);
#endif
}
