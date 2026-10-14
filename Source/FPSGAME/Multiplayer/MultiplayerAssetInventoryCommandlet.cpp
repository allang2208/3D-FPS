#include "MultiplayerAssetInventoryCommandlet.h"
#if WITH_EDITOR
#include "AssetRegistry/AssetRegistryModule.h"
#include "Blueprint/BlueprintSupport.h"
#include "Dom/JsonObject.h"
#include "Engine/Blueprint.h"
#include "Engine/LevelScriptBlueprint.h"
#include "Engine/Level.h"
#include "Engine/LevelStreaming.h"
#include "Components/ActorComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Interfaces/IPluginManager.h"
#include "Engine/World.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "GameFramework/Actor.h"
#include "GameFramework/WorldSettings.h"
#include "GameFramework/GameModeBase.h"
#include "../FPSGAMEGameMode.h"
#include "ColdSteelPlayerState.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/GarbageCollection.h"
#include "UObject/UnrealType.h"

namespace FPSMultiplayerAssetInventory
{
using FRows=TArray<TSharedPtr<FJsonValue>>;
UClass* NativeParent(UClass* Class)
{while(Class&&!Class->HasAnyClassFlags(CLASS_Native))Class=Class->GetSuperClass();return Class;}
TSharedPtr<FJsonObject> ActorInfo(AActor* Actor)
{
    auto Row=MakeShared<FJsonObject>();
    auto* Native=NativeParent(Actor->GetClass());const auto* Default=Native?Native->GetDefaultObject<AActor>():nullptr;
    Row->SetStringField(TEXT("object"),Actor->GetPathName());
    Row->SetStringField(TEXT("class"),Actor->GetClass()->GetPathName());
    Row->SetStringField(TEXT("native"),GetPathNameSafe(Native));
    Row->SetBoolField(TEXT("replicates"),Actor->GetIsReplicated());
    Row->SetBoolField(TEXT("movement"),Actor->IsReplicatingMovement());
    Row->SetBoolField(TEXT("load_on_client"),Actor->bNetLoadOnClient);
    Row->SetBoolField(TEXT("native_load_on_client"),Default&&Default->bNetLoadOnClient);
    Row->SetBoolField(TEXT("native_replicates"),Default&&Default->GetIsReplicated());
    Row->SetBoolField(TEXT("native_movement"),Default&&Default->IsReplicatingMovement());
    FRows Components;
    for(const auto* Component:Actor->GetComponents())if(Component)
    {
        auto C=MakeShared<FJsonObject>();C->SetStringField(TEXT("name"),Component->GetName());
        C->SetStringField(TEXT("class"),Component->GetClass()->GetPathName());
        C->SetBoolField(TEXT("replicates"),Component->GetIsReplicated());
        if(const auto* Primitive=Cast<UPrimitiveComponent>(Component))
        {
            C->SetBoolField(TEXT("simulate_physics"),Primitive->BodyInstance.bSimulatePhysics);
            C->SetNumberField(TEXT("collision"),int32(Primitive->GetCollisionEnabled()));
        }
        Components.Add(MakeShared<FJsonValueObject>(C));
    }
    Row->SetArrayField(TEXT("components"),Components);
    if(const auto* Property=FindFProperty<FSoftObjectProperty>(Actor->GetClass(),TEXT("WorldAsset")))
        Row->SetStringField(TEXT("world_asset"),Property->GetPropertyValue_InContainer(Actor).ToString());
    return Row;
}
FRows Graphs(UBlueprint* Blueprint)
{
    FRows Rows;TArray<UEdGraph*> Graphs;Blueprint->GetAllGraphs(Graphs);
    for(const auto* Graph:Graphs)if(Graph)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("graph"),Graph->GetName());
        FRows Nodes;
        for(const UEdGraphNode* Node:Graph->Nodes)if(Node)
        {
            auto N=MakeShared<FJsonObject>();N->SetStringField(TEXT("id"),Node->NodeGuid.ToString());
            N->SetStringField(TEXT("type"),Node->GetClass()->GetName());
            N->SetStringField(TEXT("title"),Node->GetNodeTitle(ENodeTitleType::ListView).ToString());
            if(const auto* Flags=FindFProperty<FIntProperty>(Node->GetClass(),TEXT("FunctionFlags")))
                N->SetNumberField(TEXT("function_flags"),Flags->GetPropertyValue_InContainer(Node));
            FRows Pins;
            for(const auto* Pin:Node->Pins)if(Pin&&!Pin->bHidden)
            {
                auto P=MakeShared<FJsonObject>();P->SetStringField(TEXT("name"),Pin->PinName.ToString());
                P->SetStringField(TEXT("category"),Pin->PinType.PinCategory.ToString());
                P->SetBoolField(TEXT("output"),Pin->Direction==EGPD_Output);
                if(!Pin->DefaultValue.IsEmpty())P->SetStringField(TEXT("default"),Pin->DefaultValue);
                if(Pin->DefaultObject)P->SetStringField(TEXT("default_object"),Pin->DefaultObject->GetPathName());
                FRows Links;for(const auto* To:Pin->LinkedTo)if(To&&To->GetOwningNode())
                    Links.Add(MakeShared<FJsonValueString>(To->GetOwningNode()->NodeGuid.ToString()+TEXT(":")+To->PinName.ToString()));
                P->SetArrayField(TEXT("links"),Links);Pins.Add(MakeShared<FJsonValueObject>(P));
            }
            N->SetArrayField(TEXT("pins"),Pins);Nodes.Add(MakeShared<FJsonValueObject>(N));
        }
        Row->SetArrayField(TEXT("nodes"),Nodes);Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    return Rows;
}
}
#endif

int32 UMultiplayerAssetInventoryCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    using namespace FPSMultiplayerAssetInventory;
    FString Output;if(!FParse::Value(*Params,TEXT("Output="),Output))return 1;
    const bool bAll=FParse::Param(*Params,TEXT("AllContent"));
    auto Root=MakeShared<FJsonObject>();FRows Blueprints,Maps,Skipped,Errors,Plugins;
    auto& Registry=FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get();
    Registry.SearchAllAssets(true);
    FARFilter Filter;Filter.PackagePaths.Add(TEXT("/Game"));Filter.bRecursivePaths=true;
    for(const auto& Plugin:IPluginManager::Get().GetEnabledPlugins())
    {
        auto P=MakeShared<FJsonObject>();P->SetStringField(TEXT("name"),Plugin->GetName());
        P->SetStringField(TEXT("descriptor"),Plugin->GetDescriptorFileName());
        P->SetStringField(TEXT("content_root"),Plugin->GetMountedAssetPath());
        FRows Modules;for(const auto& Module:Plugin->GetDescriptor().Modules)
            Modules.Add(MakeShared<FJsonValueString>(Module.Name.ToString()+TEXT(":")+EHostType::ToString(Module.Type)));
        P->SetArrayField(TEXT("modules"),Modules);Plugins.Add(MakeShared<FJsonValueObject>(P));
        if(bAll&&Plugin->CanContainContent())Filter.PackagePaths.Add(*Plugin->GetMountedAssetPath());
    }
    Root->SetArrayField(TEXT("plugins"),Plugins);
    TArray<FAssetData> Assets;Registry.GetAssets(Filter,Assets);
    // Package references also include unloaded streaming and LevelInstance assets.
    // This mode reads registry metadata only, without loading or executing Blueprints.
    if(FParse::Param(*Params,TEXT("ReferencesOnly")))
    {
        auto References=MakeShared<FJsonObject>();FRows Catalog;
        for(const auto& Data:Assets)
        {
            const FString Package=Data.PackageName.ToString();
            auto A=MakeShared<FJsonObject>();A->SetStringField(TEXT("package"),Package);
            A->SetStringField(TEXT("object"),Data.GetSoftObjectPath().ToString());
            A->SetStringField(TEXT("class"),Data.AssetClassPath.ToString());
            Catalog.Add(MakeShared<FJsonValueObject>(A));
            if(References->HasField(Package))continue;
            TArray<FName> Dependencies;Registry.GetDependencies(Data.PackageName,Dependencies);
            FRows Values;for(FName Dependency:Dependencies)Values.Add(MakeShared<FJsonValueString>(Dependency.ToString()));
            References->SetArrayField(Package,Values);
        }
        Root->SetObjectField(TEXT("references"),References);Root->SetArrayField(TEXT("catalog"),Catalog);
        FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
        IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output),true);
        return FFileHelper::SaveStringToFile(Json,*Output,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)?0:2;
    }
    TSet<FString> RecordedBlueprints;
    const auto RecordBlueprint=[&](UBlueprint* BP,const FString& Origin)
    {
        if(!BP||!BP->GeneratedClass||RecordedBlueprints.Contains(BP->GetPathName()))return;
        RecordedBlueprints.Add(BP->GetPathName());
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("asset"),BP->GetPathName());Row->SetStringField(TEXT("origin"),Origin);
        Row->SetStringField(TEXT("parent"),GetPathNameSafe(BP->ParentClass));
        FRows Variables;for(const auto& Variable:BP->NewVariables)
        {
            auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("name"),Variable.VarName.ToString());
            V->SetBoolField(TEXT("net"),(Variable.PropertyFlags&CPF_Net)!=0);
            V->SetStringField(TEXT("notify"),Variable.RepNotifyFunc.ToString());
            Variables.Add(MakeShared<FJsonValueObject>(V));
        }
        Row->SetArrayField(TEXT("variables"),Variables);
        if(BP->GeneratedClass->IsChildOf(AActor::StaticClass()))Row->SetObjectField(TEXT("actor"),ActorInfo(BP->GeneratedClass->GetDefaultObject<AActor>()));
        Row->SetArrayField(TEXT("graphs"),Graphs(BP));Blueprints.Add(MakeShared<FJsonValueObject>(Row));
    };
    FString MapList;TArray<FString> RequestedMaps;
    const bool bSelectedMaps=FParse::Value(*Params,TEXT("MapList="),MapList);
    if(bSelectedMaps&&!FFileHelper::LoadFileToStringArray(RequestedMaps,*MapList))return 3;
    FString AssetList;TArray<FString> RequestedAssets;
    const bool bSelectedAssets=FParse::Value(*Params,TEXT("AssetList="),AssetList);
    if(bSelectedAssets&&!FFileHelper::LoadFileToStringArray(RequestedAssets,*AssetList))return 3;
    Root->SetNumberField(TEXT("requested_asset_count"),RequestedAssets.Num());
    int32 Read=0;
    for(const auto& Data:Assets)
    {
        if(bSelectedMaps||(bSelectedAssets&&!RequestedAssets.Contains(Data.PackageName.ToString())))continue;
        // Worlds also publish their embedded LevelScript's GeneratedClass tag.
        // Read those through the map branch, not as failed standalone Blueprints.
        if(Data.AssetClassPath==UWorld::StaticClass()->GetClassPathName())continue;
        FString Native;Data.GetTagValue(FBlueprintTags::NativeParentClassPath,Native);
        FString Generated;Data.GetTagValue(FBlueprintTags::GeneratedClassPath,Generated);
        if(bAll?Generated.IsEmpty():(!Native.Contains(TEXT("/Script/FPSGAME."))&&!Native.Contains(TEXT("/Script/ColdSteelNet."))))continue;
        auto* BP=Cast<UBlueprint>(Data.GetAsset());
        if(!BP||!BP->GeneratedClass){Errors.Add(MakeShared<FJsonValueString>(Data.GetSoftObjectPath().ToString()));continue;}
        RecordBlueprint(BP,bAll?TEXT("asset_catalog"):TEXT("native_derivative"));
        UE_LOG(LogTemp,Display,TEXT("MP_ASSET Blueprint %s"),*Data.PackageName.ToString());
        if(++Read%12==0)CollectGarbage(RF_NoFlags);
    }
    FString DefaultMode;GConfig->GetString(TEXT("/Script/EngineSettings.GameMapsSettings"),TEXT("GlobalDefaultGameMode"),DefaultMode,GEngineIni);
    Root->SetStringField(TEXT("default_game_mode"),DefaultMode);
    for(const auto& Data:Assets)
    {
        if(Data.AssetClassPath!=UWorld::StaticClass()->GetClassPathName())continue;
        const FString Package=Data.PackageName.ToString();
        if(bSelectedMaps&&!RequestedMaps.Contains(Package))continue;
        if(bSelectedAssets&&!RequestedAssets.Contains(Package))continue;
        if(!bAll&&!Package.StartsWith(TEXT("/Game/GameMaps/"))&&!Package.StartsWith(TEXT("/Game/Clearwater/")))
        {Skipped.Add(MakeShared<FJsonValueString>(Package));continue;}
        auto* World=Cast<UWorld>(Data.GetAsset());
        if(!World||!World->PersistentLevel){Errors.Add(MakeShared<FJsonValueString>(Package));continue;}
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("map"),Package);FRows Actors;
        Row->SetBoolField(TEXT("world_partition"),World->GetWorldPartition()!=nullptr);
        FRows Streaming;
        for(const auto* Level:World->GetStreamingLevels())if(Level)
        {
            auto S=MakeShared<FJsonObject>();S->SetStringField(TEXT("package"),Level->GetWorldAssetPackageName());
            S->SetStringField(TEXT("class"),Level->GetClass()->GetPathName());
            S->SetBoolField(TEXT("loaded"),Level->ShouldBeLoaded());
            S->SetBoolField(TEXT("client_only_visible"),Level->bClientOnlyVisible);
            S->SetBoolField(TEXT("visible"),Level->GetShouldBeVisibleFlag());
            Streaming.Add(MakeShared<FJsonValueObject>(S));
        }
        Row->SetArrayField(TEXT("streaming"),Streaming);
        AWorldSettings* Settings=nullptr;
        for(AActor* Actor:World->PersistentLevel->Actors)if(Actor)
        {
            if(auto* S=Cast<AWorldSettings>(Actor))Settings=S;
            const auto* Native=NativeParent(Actor->GetClass());
            auto* BP=Cast<UBlueprint>(Actor->GetClass()->ClassGeneratedBy);
            if(BP)RecordBlueprint(BP,Package);
            if(bAll||BP||(Native&&Native->GetPathName().StartsWith(TEXT("/Script/FPSGAME."))))Actors.Add(MakeShared<FJsonValueObject>(ActorInfo(Actor)));
        }
        UClass* Mode=Settings?Settings->DefaultGameMode.Get():nullptr;
        if(!Mode&&!DefaultMode.IsEmpty())Mode=LoadClass<AGameModeBase>(nullptr,*DefaultMode);
        Row->SetStringField(TEXT("game_mode"),GetPathNameSafe(Mode));
        if(const auto* CDO=Mode?Mode->GetDefaultObject<AGameModeBase>():nullptr)
        {
            RecordBlueprint(Cast<UBlueprint>(Mode->ClassGeneratedBy),Package);
            for(UClass* Class:{CDO->DefaultPawnClass.Get(),CDO->PlayerControllerClass.Get(),CDO->PlayerStateClass.Get()})
                if(Class)RecordBlueprint(Cast<UBlueprint>(Class->ClassGeneratedBy),Package);
            Row->SetStringField(TEXT("default_pawn"),GetPathNameSafe(CDO->DefaultPawnClass.Get()));
            Row->SetStringField(TEXT("player_controller"),GetPathNameSafe(CDO->PlayerControllerClass.Get()));
            Row->SetStringField(TEXT("player_state"),GetPathNameSafe(CDO->PlayerStateClass.Get()));
            Row->SetBoolField(TEXT("multiplayer_player_state"),CDO->PlayerStateClass&&CDO->PlayerStateClass->IsChildOf(AColdSteelPlayerState::StaticClass()));
        }
        Row->SetArrayField(TEXT("actors"),Actors);
        if(auto* Script=World->PersistentLevel->GetLevelScriptBlueprint(true))Row->SetArrayField(TEXT("level_graphs"),Graphs(Script));
        Maps.Add(MakeShared<FJsonValueObject>(Row));
        UE_LOG(LogTemp,Display,TEXT("MP_ASSET Map %s actors=%d"),*Package,Actors.Num());CollectGarbage(RF_NoFlags);
    }
    Root->SetArrayField(TEXT("blueprints"),Blueprints);Root->SetArrayField(TEXT("maps"),Maps);
    Root->SetArrayField(TEXT("maps_outside_scope"),Skipped);Root->SetArrayField(TEXT("load_failures"),Errors);
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output),true);
    return FFileHelper::SaveStringToFile(Json,*Output,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)?0:2;
#else
    return 1;
#endif
}
