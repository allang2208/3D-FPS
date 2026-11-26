#include "FoodSpoilage.h"
#include "../Building/CampfireSharedTypes.h"
#include "../Building/SmeltingSystem.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/VoxelBuildPersistence.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"

// Uses real failed file writes inside the guarded commandlet directory. No
// production fault switches, sockets, live world or caller-supplied saves.
struct FCampfireRecoveryAuditAccess
{
    static void Run(UWorld* World,UColdSteelStatusModel* Model,AVoxelBuildWorld* Building,FIntVector Cell,
        TFunctionRef<void(bool,const FString&)> Check)
    {
        auto Report=[&](bool Pass,const FString& Name)
        {Check(Pass,TEXT("campfire recovery: ")+Name);return Pass;};
        FString Root=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("SourceAssets/FoodSpoilage20261015/TestRuns"));
        FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());
        FPaths::NormalizeDirectoryName(Root);FPaths::NormalizeDirectoryName(Saved);
        if(!Report(World&&Model&&Building&&Building->GetWorld()==World&&Model->IsAudit()
            &&Model->ProfileSlot().StartsWith(TEXT("ColdSteel_FoodSpoilageAudit_"))&&Saved.StartsWith(Root+TEXT("/"))
            &&World->GetNetMode()==NM_Standalone&&!World->GetNetDriver()&&World->NextURL.IsEmpty(),
            TEXT("rejects formal saves and requires an idle isolated audit world")))return;
        TGuardValue<FString> ListenMode(World->NextURL,TEXT("/Engine/Maps/Entry?listen"));
        auto* Shared=World->GetSubsystem<UColdSteelSharedInventorySubsystem>();
        auto* Cooking=World->GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>();
        if(!Report(World->GetNetMode()==NM_ListenServer&&Shared&&!Shared->bInitialized&&Cooking,
            TEXT("isolated in-process listen authority available; no network transport")))return;
        const auto Original=Shared->Current;const FString OriginalSlot=Shared->SaveSlot;
        const bool WasInitialized=Shared->bInitialized,WasBlocked=Shared->bBlocked,WasCommitting=Shared->bCommitting;
        const auto ProfileBefore=Model->Snapshot();
        FString BlockedDirectory,BlockedFile;
        auto RemoveObstructions=[&]()
        {
            bool Removed=true;
            if(!BlockedDirectory.IsEmpty())
            {
                const bool OK=IFileManager::Get().DeleteDirectory(*BlockedDirectory,false,false);
                Removed&=OK;if(OK)BlockedDirectory.Reset();
            }
            if(!BlockedFile.IsEmpty())
            {
                const bool OK=IFileManager::Get().Delete(*BlockedFile,false);
                Removed&=OK;if(OK)BlockedFile.Reset();
            }
            return Removed;
        };
        ON_SCOPE_EXIT
        {
            RemoveObstructions();Shared->Current=Original;Shared->SaveSlot=OriginalSlot;
            Shared->bInitialized=WasInitialized;Shared->bBlocked=WasBlocked;Shared->bCommitting=WasCommitting;
            Model->AdoptNetMirror(ProfileBefore);
        };
        auto Forget=[&]()
        {Shared->Current={};Shared->bInitialized=false;Shared->bBlocked=false;Shared->bCommitting=false;Shared->SaveSlot.Reset();};
        if(!Report(Shared->InitializeAuthority(),TEXT("real shared persistence initialized")))return;
        const FString Slot=Shared->SaveSlot;
        auto Count=[&]()
        {int64 N=0;for(const auto& I:Model->Items())if(I.Definition==TEXT("roasted_sausage"))N+=I.Count;return N;};
        for(const bool FailFinalization:{false,true})
        {
            FString Reason;
            auto Empty=Model->Snapshot();Empty.Items.Reset();Empty.ActiveProductionTool.Reset();Empty.ActiveWeaponSlot=6;
            Empty.Hotbar.Init(TEXT(""),4);Empty.HotbarDefinitions.Init(TEXT(""),4);for(auto& Binding:Empty.QuickBindings)Binding={};
            ColdSteelInventory::Insert(Empty.Items,Model->CreateItem(TEXT("raw_sausage")));
            ColdSteelInventory::Insert(Empty.Items,Model->CreateItem(Cooking->FuelConfig().Item));
            if(!Report(Model->CommitState(Empty),TEXT("raw food and wood inventory committed before failure fixture")))return;
            const auto Clock=ColdSteelFood::Clock(World);
            FCampfireSharedState State;State.FoodEscrowVersion=1;State.FoodClockId=Clock.Id;
            State.FoodSampleDay=Clock.Day;State.FoodUtcTicks=FDateTime::UtcNow().GetTicks();
            auto Food=Model->CreateItem(TEXT("roasted_sausage"));ColdSteelFood::Stamp(Food,Clock,1.);
            auto& Product=State.Products.AddDefaulted_GetRef();Product.Item=Food.Definition;Product.Count=Food.Count;Product.Payload=Food;
            Building->WriteCampfireState(Cell,State);
            auto Pending=Shared->Current;
            const bool Captured=Building->FlushCampfirePersistence()&&Building->MakeNetworkSnapshot(Pending.Building);
            Pending.bBuildingPending=true;
            if(!Report(Captured&&Shared->Commit(Model,nullptr,Model->Snapshot(),MoveTemp(Pending),Reason),
                TEXT("real shared transaction durably records a pending building snapshot")))return;
            if(FailFinalization)
            {
                // A file occupying the expected parent makes the actual shared
                // SaveGameToSlot fail without touching the committed shared slot.
                const FString Parent=TEXT("FoodAudit_BlockedParent_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
                BlockedFile=Saved/TEXT("SaveGames")/Parent;
                if(!Report(FFileHelper::SaveStringToFile(TEXT("isolated obstruction"),*BlockedFile),
                    TEXT("creates isolated finalization-write obstruction")))return;
                Shared->SaveSlot=Parent/TEXT("World");
            }
            else
            {
                // VoxelPersistence writes .sav.pending before an atomic replace.
                // An empty directory at that exact temporary path causes a real
                // write failure and leaves the existing building file intact.
                BlockedDirectory=Saved/TEXT("SaveGames")/(Building->SaveSlotName()+TEXT(".sav.pending"));
                if(!Report(!IFileManager::Get().DirectoryExists(*BlockedDirectory)
                    &&IFileManager::Get().MakeDirectory(*BlockedDirectory),TEXT("creates isolated building-write obstruction")))return;
            }
            const bool Completed=Shared->CompleteBuildingCommit(Building);Shared->SaveSlot=Slot;
            const auto* Disk=Cast<UColdSteelSharedInventorySave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
            Report(!Completed&&Shared->bBlocked&&Shared->Current.bBuildingPending&&Disk&&Disk->Data.bBuildingPending,
                FailFinalization?TEXT("failed pending-clear write retains durable redo and blocks further writes")
                    :TEXT("failed building flush retains durable redo and blocks further writes"));
            const auto InventoryBefore=Model->Snapshot();const int64 Revision=Model->InventoryRevision();
            const bool Collected=Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,2,NAME_None,1,Reason);
            Report(!Collected&&Count()==0&&Model->InventoryRevision()==Revision
                &&Cooking->CampfireState(Building,Cell).Products.Num()==1&&Cooking->IsCampfireSaveBlocked(Building),
                TEXT("independent campfire claim cannot bypass the older pending building snapshot"));
            const bool Queued=Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,1,TEXT("roast_sausage"),1,Reason);
            const bool Fueled=Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,0,NAME_None,1,Reason);
            bool Unchanged=Model->Items().Num()==InventoryBefore.Items.Num();
            if(Unchanged)for(int32 N=0;N<InventoryBefore.Items.Num();++N)
                Unchanged&=FColdSteelItem::StaticStruct()->CompareScriptStruct(&InventoryBefore.Items[N],&Model->Items()[N],0);
            Report(!Queued&&!Fueled&&Unchanged&&Model->InventoryRevision()==Revision,
                TEXT("pending redo blocks new paid orders and fuel without changing any inventory field"));
            if(!Report(RemoveObstructions(),TEXT("removes only the isolated failure obstruction")))return;
            Forget();
            const bool Recovered=Shared->RestoreBuilding(Building);
            const auto* Cleared=Cast<UColdSteelSharedInventorySave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
            if(!Report(Recovered&&Cleared&&!Cleared->Data.bBuildingPending&&!Shared->IsBuildingSaveBlocked(),
                TEXT("actual reload replays and durably finalizes pending building before reopening transactions")))return;
            const bool Once=Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,2,NAME_None,1,Reason);
            Report(Once&&Count()==1&&Cooking->CampfireState(Building,Cell).Products.IsEmpty(),
                TEXT("claim succeeds exactly once after recovery"));
            VoxelPersistence::ELoadResult LoadResult;auto* SavedBuilding=VoxelPersistence::Load(Building->SaveSlotName(),LoadResult,false);
            TArray<uint8> ReloadBytes;
            const bool LoadedBuilding=SavedBuilding&&VoxelPersistence::Encode(VoxelPersistence::Take(SavedBuilding),ReloadBytes)
                &&Building->ApplyNetworkSnapshot(ReloadBytes);
            Forget();const bool Reloaded=LoadedBuilding&&Shared->RestoreBuilding(Building);
            const bool Twice=Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,2,NAME_None,1,Reason);
            Report(Reloaded&&!Twice&&Count()==1&&Cooking->CampfireState(Building,Cell).Products.IsEmpty(),
                TEXT("reloading finalized shared state cannot resurrect an already claimed meal"));
        }
    }
};

void RunCampfireRecoveryAudit(UWorld* World,UColdSteelStatusModel* Model,AVoxelBuildWorld* Building,FIntVector Cell,
    TFunctionRef<void(bool,const FString&)> Check)
{FCampfireRecoveryAuditAccess::Run(World,Model,Building,Cell,Check);}
