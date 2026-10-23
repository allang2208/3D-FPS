#include "BackpackCapacityAuditCommandlet.h"
#include "ColdSteelInventoryTypes.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Misc/Parse.h"
#if WITH_EDITOR
int32 RunBackpackMotionDiagnostic(const FString& Params);
int32 RunBackpackLifecycleDiagnostic(const FString& Params);
#endif

int32 UBackpackCapacityAuditCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    if(FParse::Param(*Params,TEXT("LifecycleOnly")))return RunBackpackLifecycleDiagnostic(Params);
    if(FParse::Param(*Params,TEXT("MotionOnly")))return RunBackpackMotionDiagnostic(Params);
#endif
    using namespace ColdSteelInventory;
    int32 Passed=0,Failed=0;FString Report;
    auto Check=[&](bool OK,const FString& Label){(OK?Passed:Failed)++;Report+=FString::Printf(TEXT("%s %s\n"),OK?TEXT("PASS"):TEXT("FAIL"),*Label);};
    FString Json;TSharedPtr<FJsonObject> Catalog;
    if(!FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/items.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Catalog)||!Catalog)return 2;
    auto Item=[&](const FString& Key,const FString& Id){
        FColdSteelItem I;I.Definition=Key;I.InstanceId=Id;
        FJsonSerializer::Serialize(Catalog->GetObjectField(Key).ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));
        const auto Size=Footprint(I);I.Width=Size.X;I.Height=Size.Y;return I;};
    const struct {const TCHAR* Key;FIntPoint Grid;int32 Rows;} Cases[]={
        {TEXT("ue_simple_sling_bag"),FIntPoint(3,4),5},
        {TEXT("ue_mountain_backpack"),FIntPoint(5,6),5},
        {TEXT("ue_portable_backpack"),FIntPoint(6,6),5},
        {TEXT("ue_expedition_backpack"),FIntPoint(8,6),6},
        {TEXT("ue_pathfinder_backpack"),FIntPoint(12,6),7}};
    for(const auto& Case:Cases)
    {
        const TCHAR* Key=Case.Key;const FIntPoint Expected=Case.Grid;const int32 Capacity=Case.Rows*18;
        for(int32 Legacy=0;Legacy<3;++Legacy)
        {
            auto Bag=Item(Key,TEXT("bag"));Bag.Place=1;Bag.Cell=14;
            if(Legacy)
            {
                TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Bag.Data),Data);
                for(const TCHAR* Field:{TEXT("bagExtraCells"),TEXT("bagCompartmentCells"),TEXT("bagCompartmentColumns"),TEXT("bagCompartmentRows")})
                    if(Legacy==1)Data->RemoveField(Field);else Data->SetNumberField(Field,0);
                Bag.Data.Empty();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Bag.Data));
            }
            TArray<FColdSteelItem> Items{Bag};const FString Label=FString::Printf(TEXT("%s snapshot=%d"),Key,Legacy);
            Check(BagRows(Items)==Case.Rows&&CompartmentGrid(Items)==Expected,Label+TEXT(" authored main and compartment capacity"));
            FColdSteelItem Marker;Marker.InstanceId=TEXT("marker");Marker.Definition=TEXT("test_marker");Marker.Data=TEXT("{}");Marker.Place=0;Marker.Cell=0;Items.Add(Marker);
            auto Last=Move(Items,Marker.InstanceId,0,Capacity-1);
            Check(Last.bValid&&Last.Items.ContainsByPredicate([Capacity](const auto& I){return I.InstanceId==TEXT("marker")&&I.Cell==Capacity-1;}),Label+TEXT(" last expanded cell usable"));
            Check(!Move(Items,Marker.InstanceId,0,Capacity).bValid,Label+TEXT(" first cell outside capacity rejected"));
            auto Unequip=Move(Last.Items,Bag.InstanceId,0,-1);
            Check(Unequip.bValid&&BagRows(Unequip.Items)==4&&CompartmentCells(Unequip.Items)==0
                &&Unequip.Items.Num()==2&&Unequip.Items.ContainsByPredicate([](const auto& I){return I.InstanceId==TEXT("marker")&&I.Cell<72;}),Label+TEXT(" unequip safely returns fifth-row item"));
            auto Carried=Bag;Carried.Place=0;Carried.Cell=0;TArray<FColdSteelItem> Carry{Carried};
            Check(BagRows(Carry)==4&&CompartmentCells(Carry)==0,Label+TEXT(" carried bag grants no capacity"));
        }
    }
    auto Large=Item(TEXT("ue_portable_backpack"),TEXT("large"));Large.Place=1;Large.Cell=14;
    auto Small=Item(TEXT("ue_mountain_backpack"),TEXT("small"));Small.Place=0;Small.Cell=0;
    FColdSteelItem Nested;Nested.InstanceId=TEXT("nested");Nested.Definition=TEXT("test_marker");Nested.Data=TEXT("{}");Nested.Place=5;Nested.Cell=35;
    auto Swap=Move({Large,Small,Nested},Small.InstanceId,1,14);
    Check(Swap.bValid&&BagRows(Swap.Items)==5&&CompartmentGrid(Swap.Items)==FIntPoint(5,6)&&Swap.Items.Num()==3
        &&Swap.Items.ContainsByPredicate([](const auto& I){return I.InstanceId==TEXT("nested")&&I.Place==0;}),TEXT("swap 6x6 to 5x6 returns sixth-column content without loss"));
    TArray<FColdSteelItem> Full{Large};for(int32 C=0;C<90;++C){auto I=Nested;I.InstanceId=FString::Printf(TEXT("full%d"),C);I.Place=0;I.Cell=C;Full.Add(I);}
    Check(!Move(Full,Large.InstanceId,0,-1).bValid&&BagRows(Full)==5&&Full.Num()==91,TEXT("full inventory refuses bag removal without losing contents"));
    auto Pathfinder=Item(TEXT("ue_pathfinder_backpack"),TEXT("pathfinder"));Pathfinder.Place=1;Pathfinder.Cell=14;
    auto OldPack=Item(TEXT("ue_expedition_backpack"),TEXT("old_pack"));OldPack.Place=0;OldPack.Cell=0;
    auto Edge=Nested;Edge.InstanceId=TEXT("last_compartment_cell");Edge.Cell=71;
    auto Bottom=Nested;Bottom.InstanceId=TEXT("seventh_row_item");Bottom.Place=0;Bottom.Cell=125;
    auto Shrink=Move({Pathfinder,OldPack,Edge,Bottom},OldPack.InstanceId,1,14);
    Check(Shrink.bValid&&Shrink.Items.Num()==4&&BagRows(Shrink.Items)==6&&CompartmentGrid(Shrink.Items)==FIntPoint(8,6)
        &&Shrink.Items.ContainsByPredicate([](const auto& I){return I.InstanceId==TEXT("last_compartment_cell")&&I.Place==0&&I.Cell<108;})
        &&Shrink.Items.ContainsByPredicate([](const auto& I){return I.InstanceId==TEXT("seventh_row_item")&&I.Place==0&&I.Cell<108;}),
        TEXT("pathfinder shrink relocates both seventh row and twelfth compartment column without loss"));
    TArray<FColdSteelItem> FullPathfinder{Pathfinder};for(int32 C=0;C<126;++C){auto I=Nested;I.InstanceId=FString::Printf(TEXT("pathfull%d"),C);I.Place=0;I.Cell=C;FullPathfinder.Add(I);}
    Check(!Move(FullPathfinder,Pathfinder.InstanceId,0,-1).bValid&&FullPathfinder.Num()==127&&BagRows(FullPathfinder)==7,
        TEXT("full pathfinder refuses unequip atomically"));
    // Same migration entry used by guest sanitization; retain layout and item
    // identity when the former expedition grid changes its row-major stride.
    FColdSteelProfile Legacy;Legacy.Hotbar.SetNum(4);Legacy.HotbarDefinitions.SetNum(4);Legacy.WarehouseLayoutVersion=1;
    for(FName Key:{FName("str"),FName("dex"),FName("intt"),FName("con"),FName("wis"),FName("luck")})Legacy.Attributes.Add(Key,10);
    auto Expedition=Item(TEXT("ue_expedition_backpack"),TEXT("expedition"));Expedition.Place=1;Expedition.Cell=14;
    TSharedPtr<FJsonObject> OldData;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Expedition.Data),OldData);
    OldData->SetNumberField(TEXT("bagCompartmentColumns"),6);OldData->SetNumberField(TEXT("bagCompartmentRows"),8);
    Expedition.Data.Reset();FJsonSerializer::Serialize(OldData.ToSharedRef(),TJsonWriterFactory<>::Create(&Expedition.Data));
    FColdSteelItem Long;Long.InstanceId=TEXT("long_item");Long.Definition=TEXT("test_long");Long.Data=TEXT("{\"grid_w\":1,\"grid_h\":4}");Long.Width=1;Long.Height=4;Long.Place=5;Long.Cell=5;
    auto Marker=Nested;Marker.InstanceId=TEXT("row_marker");Marker.Cell=13;
    Legacy.Items={Long,Marker,Expedition};FString Reason;bool Migrated=false;
    Check(!Validate(Legacy,Reason),TEXT("old 6x8 fixture rejected if validated against current 8x6 too early"));
    const bool Migration=MigrateAuthoredGridFootprints(Legacy,Migrated,Reason);
    Check(Migration&&Migrated&&Validate(Legacy,Reason)&&Legacy.Items.Num()==3&&CompartmentGrid(Legacy.Items)==FIntPoint(8,6)
        &&Legacy.Items.ContainsByPredicate([](const auto& I){return I.InstanceId==TEXT("long_item")&&I.Place==5&&I.Cell==5;})
        &&Legacy.Items.ContainsByPredicate([](const auto& I){return I.InstanceId==TEXT("row_marker")&&I.Place==5&&I.Cell==17;}),TEXT("guest layout migration retains items and accepts current 8x6"));
    // Read saved payloads directly. Do not create a GameInstance, load a model,
    // migrate the real profiles, save a slot, or run any pawn/gameplay.
    TArray<FString> Files;if(!FParse::Param(*Params,TEXT("SyntheticOnly")))IFileManager::Get().FindFiles(Files,*(FPaths::ProjectSavedDir()/TEXT("SaveGames/ColdSteelPlayer*.sav")),true,false);
    for(const auto& File:Files)
    {
        const auto* Save=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(FPaths::GetBaseFilename(File),0));
        if(!Save)continue;
        Report+=FString::Printf(TEXT("SAVE %s generation=%lld effective_rows=%d\n"),*File,Save->Profile.Generation,BagRows(Save->Profile.Items));
        for(const auto& I:Save->Profile.Items)if(I.Definition==TEXT("ue_mountain_backpack")||I.Definition==TEXT("ue_portable_backpack"))
            Report+=FString::Printf(TEXT("  %s place=%d cell=%d snapshot_extra=%.0f effective_compartment=%dx%d\n"),*I.Definition,I.Place,I.Cell,
                Number(I,TEXT("bagExtraCells"),-1),CompartmentGridOf(I).X,CompartmentGridOf(I).Y);
    }
    Report+=FString::Printf(TEXT("RESULT passed=%d failed=%d; real saves read only; no game started\n"),Passed,Failed);
    FString Dir;FParse::Value(*Params,TEXT("ReportDir="),Dir);
    if(Dir.IsEmpty())Dir=FPaths::ProjectDir()/TEXT("SourceAssets/BackpacksReview20261021");IFileManager::Get().MakeDirectory(*Dir,true);
    FFileHelper::SaveStringToFile(Report,*(Dir/TEXT("capacity_checks.txt")));
    UE_LOG(LogTemp,Display,TEXT("%s"),*Report);return Failed?1:0;
}
