#include "ColdSteelPlantingAuditCommandlet.h"
#include "ColdSteelPlantingSystem.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPrefabActor.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"

int32 UColdSteelPlantingAuditCommandlet::Main(const FString& Params)
{
    if(FParse::Param(*Params,TEXT("PlantingNetworkAudit")))return RunNetworkAudit(Params);
    FString Root;
    if(!FParse::Value(*Params,TEXT("PlantingAuditRoot="),Root)||Root.IsEmpty())return 2;
    Root=FPaths::ConvertRelativePathToFull(Root);FPaths::NormalizeDirectoryName(Root);
    FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());FPaths::NormalizeDirectoryName(Saved);
    const FString Allowed=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("SourceAssets/PlantingGameplay20261022"));
    if(!Root.StartsWith(Allowed+TEXT("/"))||!Saved.StartsWith(Root+TEXT("/")))return 2;
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=PlantingAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("PlantingAuditFixture"));
    auto* World=GI->GetWorld();
    ON_SCOPE_EXIT
    {
        GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);
        GI->RemoveFromRoot();FCommandLine::Set(*Original);
    };
    auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();auto* System=GI->GetSubsystem<UColdSteelPlantingSystem>();
    if(!Model||!System||!Model->IsAudit()||!Model->ProfileSlot().StartsWith(TEXT("ColdSteel_PlantingAudit_")))return 2;
    int32 Checks=0,Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;FString Reason;
    auto Check=[&](bool Pass,const FString& Name)
    {
        ++Checks;if(!Pass)++Failures;
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("name"),Name);Row->SetBoolField(TEXT("passed"),Pass);Rows.Add(MakeShared<FJsonValueObject>(Row));
        if(!Pass){Row->SetStringField(TEXT("reason"),Reason);Row->SetStringField(TEXT("model_message"),Model->ResultMessage());}
        UE_LOG(LogTemp,Display,TEXT("PLANTING_AUDIT %s %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name,Pass?TEXT(""):*Reason);return Pass;
    };
    ON_SCOPE_EXIT
    {
        auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("checks"),Checks);Result->SetNumberField(TEXT("failures"),Failures);
        Result->SetArrayField(TEXT("results"),Rows);Result->SetBoolField(TEXT("graphical_editor_started"),false);Result->SetBoolField(TEXT("game_or_pie_started"),false);
        Result->SetStringField(TEXT("profile_slot"),Model->ProfileSlot());Result->SetStringField(TEXT("saved_root"),Saved);
        FString Output;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*(Root/TEXT("planting-audit.json")));
        UE_LOG(LogTemp,Display,TEXT("PLANTING_AUDIT_COMPLETE checks=%d failures=%d"),Checks,Failures);
    };
    Check(System->Catalog().Num()==4,TEXT("four configured crops"));
    int32 Meshes=0;
    for(const auto& Rule:System->Catalog())for(const auto& Variant:Rule.Variants)for(const auto& Path:Variant.Value)
    {if(auto* Mesh=Cast<UStaticMesh>(Path.TryLoad())){++Meshes;System->MeshCache.AddUnique(Mesh);}}
    System->bAssetsReady=Meshes==36;
    Check(Meshes==36,TEXT("all 36 V3 stages load from actual project packages"));
    auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();
    // This empty fixture never initializes actors for play. Register the controller
    // explicitly, as AController::PostInitializeComponents normally does.
    World->AddController(PC);
    auto* Pawn=World->SpawnActor<APawn>();PC->Possess(Pawn);
    if(!Check(World->GetFirstPlayerController()==PC&&PC->GetPawn()==Pawn,TEXT("isolated interaction fixture has registered player and pawn")))return 3;
    auto* Building=World->SpawnActor<AVoxelBuildWorld>();Building->WorldKey=TEXT("PlantingAuditWorld_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    auto* Bed=World->SpawnActor<AVoxelBuildPrefabActor>();Bed->SetOwner(Building);
    Bed->Configure(UColdSteelPlantingSystem::BedPrefabId(),FIntVector::ZeroValue,0,nullptr,nullptr,nullptr);
    FVoxelBuildPrefabInstance Record;Record.Id=UColdSteelPlantingSystem::BedPrefabId();Record.Cell=FIntVector::ZeroValue;Record.InstanceId=FGuid::NewGuid();Record.Footprint=FIntVector(10,10,2);
    Building->Prefabs.Add(Record);Building->PrefabActors.Add(Record.Cell,Bed);
    if(!Check(System->Bed(Building,Record.Cell)==Bed&&Building->PrefabInstanceIdentity(Record.Cell)==Record.InstanceId,
        TEXT("isolated fixture uses real bed identity lookup")))return 3;
    auto Blank=Model->Snapshot();Blank.Items.Reset();Blank.PlantingCrops.Reset();Blank.Hotbar.Init(TEXT(""),4);Blank.HotbarDefinitions.Init(TEXT(""),4);
    for(auto& Binding:Blank.QuickBindings)Binding=FColdSteelQuickBinding();
    Blank.ActiveProductionTool.Reset();Blank.ForgeJob={};Blank.GunAssemblyJob={};Blank.WoodworkingJob={};
    Model->AdoptNetMirror(Blank);
    const FName Tomato(TEXT("tomato"));const FIntVector Cell=FIntVector::ZeroValue;
    Check(!System->Act(Building,Cell,0,Tomato,Reason)&&Reason.Contains(TEXT("种植材料不足"))&&Model->PlantingCrops().IsEmpty(),TEXT("insufficient inventory leaves plot empty"));
    auto Seed=Blank;Check(ColdSteelInventory::Insert(Seed.Items,Model->CreateItem(TEXT("tomato"),1)),TEXT("fixture uses actual inventory insertion"));
    Check(Model->CommitState(Seed),TEXT("isolated checked profile commit"));
    Model->AuditFailNextSave=true;
    Check(!System->Act(Building,Cell,0,Tomato,Reason)&&!Model->AuditFailNextSave&&Model->CountMaterial(TEXT("tomato"))==1&&Model->PlantingCrops().IsEmpty(),TEXT("save failure rolls back material and plant together"));
    Check(System->Act(Building,Cell,0,Tomato,Reason)&&Model->CountMaterial(TEXT("tomato"))==0&&Model->PlantingCrops().Num()==1,TEXT("successful planting deducts exactly one material"));
    if(Model->PlantingCrops().Num()!=1)return 3;
    const FColdSteelCropPlant Plant=Model->PlantingCrops()[0];
    Check(Plant.BedId==Record.InstanceId&&Plant.WorldKey==Building->BuildingWorldKey(),TEXT("plant bound to stable world and bed instance identity"));
    Check(Plant.Variant==TEXT("A")||Plant.Variant==TEXT("B")||Plant.Variant==TEXT("C"),TEXT("one stable A/B/C variant"));
    Check(Plant.YawDegrees>=0&&Plant.YawDegrees<=360&&Plant.UniformScale>=.9f&&Plant.UniformScale<=1.f,TEXT("persisted bounded yaw and scale"));
    Check(!System->Act(Building,Cell,0,Tomato,Reason)&&Model->PlantingCrops().Num()==1,TEXT("duplicate plant click rejected"));
    const auto* Secondary=System->Occupant(Building,Cell,5);
    Check(!System->CanAct(Building,Cell,1,Tomato,Reason)&&Secondary&&Secondary->PlantId==Plant.PlantId,TEXT("2x2 occupancy resolves secondary cells to same plant"));
    Check(!System->CanAct(Building,Cell,15,Tomato,Reason),TEXT("2x2 planting cannot cross bed boundary"));
    const int64 Start=Plant.PlantedUtcTicks;
    Check(Plant.Stage(Start)==1&&Plant.Stage(Start+int64(Plant.GrowthSeconds*.5*ETimespan::TicksPerSecond))==2
        &&Plant.Stage(Start+int64(Plant.GrowthSeconds*ETimespan::TicksPerSecond))==3,TEXT("three stages use one planting clock including offline elapsed time"));
    const auto BeforeStages=Model->Snapshot();
    const FTransform ExpectedTransform=FTransform(FRotator(0,Plant.YawDegrees,0),Plant.LocalRootCm,FVector(Plant.UniformScale))*Bed->GetActorTransform();
    for(int32 StageIndex=0;StageIndex<3;++StageIndex)
    {
        auto StageState=BeforeStages;auto& StagePlant=StageState.PlantingCrops[0];
        const double Age=StageIndex==0?0.:StageIndex==1?Plant.GrowthSeconds*.75:Plant.GrowthSeconds+1.;
        StagePlant.PlantedUtcTicks=FDateTime::UtcNow().GetTicks()-int64(Age*ETimespan::TicksPerSecond);
        Check(Model->CommitState(StageState),FString::Printf(TEXT("stage %d fixture checked commit"),StageIndex+1));
        System->UpdateWorld(Building,1.f);
        const auto* Rule=System->Find(Plant.Crop);
        const FString MeshPath=Rule->Variants.FindChecked(Plant.Variant)[StageIndex].ToString();
        const auto* Group=System->MeshGroups.Find(MeshPath);FTransform Presented;
        int32 VisibleInstances=0;for(const auto& Pair:System->MeshGroups)VisibleInstances+=Pair.Value->GetInstanceCount();
        const auto& Kept=Model->PlantingCrops()[0];
        const bool Stable=Kept.PlantId==Plant.PlantId&&Kept.Variant==Plant.Variant&&Kept.YawDegrees==Plant.YawDegrees
            &&Kept.UniformScale==Plant.UniformScale&&Kept.LocalRootCm==Plant.LocalRootCm;
        Check(Stable&&VisibleInstances==1&&Group&&(*Group)->GetInstanceCount()==1&&(*Group)->GetInstanceTransform(0,Presented,true)
            &&Presented.Equals(ExpectedTransform,.001),FString::Printf(TEXT("stage %d uses matching V3 variant mesh and unchanged instance transform"),StageIndex+1));
    }
    Check(Model->CommitState(BeforeStages),TEXT("stage fixture restores original planting clock"));
    auto* Save=NewObject<UColdSteelProfileSave>();Save->Profile=Model->Snapshot();TArray<uint8> Bytes;
    Check(UGameplayStatics::SaveGameToMemory(Save,Bytes),TEXT("profile serializes planting data"));
    auto* Loaded=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromMemory(Bytes));
    const bool HasLoaded=Loaded&&Loaded->Profile.PlantingCrops.Num()==1;
    Check(HasLoaded,TEXT("profile planting record round trip"));
    if(HasLoaded)
    {
        const auto& P=Loaded->Profile.PlantingCrops[0];
        Check(P.PlantId==Plant.PlantId&&P.BedId==Plant.BedId&&P.Variant==Plant.Variant&&P.YawDegrees==Plant.YawDegrees
            &&P.UniformScale==Plant.UniformScale&&P.LocalRootCm==Plant.LocalRootCm&&P.PlantedUtcTicks==Plant.PlantedUtcTicks
            &&P.OutputCount==Plant.OutputCount&&P.GrowthSeconds==Plant.GrowthSeconds,TEXT("save/load preserves transform variant clock and yield"));
    }
    Check(Model->ReloadProfile()&&Model->PlantingCrops().Num()==1&&Model->PlantingCrops()[0].PlantId==Plant.PlantId,TEXT("checked disk save reload retains same plant"));
    auto Mature=Model->Snapshot();Mature.PlantingCrops[0].PlantedUtcTicks=FDateTime::UtcNow().GetTicks()-int64((Plant.GrowthSeconds+1)*ETimespan::TicksPerSecond);
    Check(Model->CommitState(Mature),TEXT("fixture matures existing plant without rerolling it"));
    auto Full=Model->Snapshot();Full.Items.Reset();
    for(int32 I=0;I<512;++I)
    {
        auto Item=Model->CreateItem(TEXT("tomato"),1);Item.Count=FMath::Max<int64>(1,int64(ColdSteelInventory::Number(Item,TEXT("maxStack"),1)));
        if(!ColdSteelInventory::Insert(Full.Items,Item))break;
    }
    Check(Model->CommitState(Full),TEXT("full backpack fixture is a valid real inventory"));
    const int64 BeforeCount=Model->CountMaterial(TEXT("tomato"));
    Check(!System->Act(Building,Cell,0,Tomato,Reason,Plant.PlantId)&&Model->PlantingCrops().Num()==1&&Model->CountMaterial(TEXT("tomato"))==BeforeCount,
        TEXT("full backpack does not clear mature plant or grant a partial harvest"));
    auto Empty=Model->Snapshot();Empty.Items.Reset();Check(Model->CommitState(Empty),TEXT("backpack capacity restored"));
    Check(System->Act(Building,Cell,0,Tomato,Reason,Plant.PlantId)&&Model->PlantingCrops().IsEmpty()
        &&Model->CountMaterial(Plant.OutputItem)==Plant.OutputCount,TEXT("harvest grants configured yield and clears all occupied cells atomically"));
    Check(!System->Act(Building,Cell,0,Tomato,Reason,Plant.PlantId)&&Model->CountMaterial(Plant.OutputItem)==Plant.OutputCount,TEXT("duplicate harvest receipt cannot harvest or replant"));
    auto Other=Blank;auto OtherSeed=Model->CreateItem(TEXT("tomato"),1);OtherSeed.Place=4;OtherSeed.Container=TEXT("unrelated_chest");OtherSeed.Cell=0;Other.Items.Add(OtherSeed);
    Model->AdoptNetMirror(Other);
    Check(!System->Act(Building,Cell,0,Tomato,Reason),TEXT("unrelated chest material excluded from planting source"));
    for(const auto& Rule:System->Catalog())
    {
        auto State=Blank;ColdSteelInventory::Insert(State.Items,Model->CreateItem(Rule.InputItem,Rule.InputCount));Model->AdoptNetMirror(State);
        Check(System->Act(Building,Cell,0,Rule.Id,Reason)&&Model->PlantingCrops().Num()==1&&Model->PlantingCrops()[0].Crop==Rule.Id,
            TEXT("actual crop transaction: ")+Rule.Id.ToString());
    }
    auto Stale=Model->Snapshot();const FGuid OldBed=Record.InstanceId;Building->Prefabs[0].InstanceId=FGuid::NewGuid();
    Check(!System->Occupant(Building,Cell,0),TEXT("replacement bed at same cell does not revive old plant"));
    System->UpdateWorld(Building,1.f);
    Check(Model->PlantingCrops().IsEmpty(),TEXT("removed bed identity clears orphan crop through checked commit"));
    System->ClearPresentation();PC->UnPossess();Pawn->Destroy();PC->Destroy();Bed->Destroy();Building->Destroy();
    return Failures?1:0;
}
