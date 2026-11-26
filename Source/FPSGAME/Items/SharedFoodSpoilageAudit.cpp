#include "SharedFoodSpoilageAudit.h"
#include "FoodSpoilage.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickup.h"
#include "../FPSGAMECharacter.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "TimerManager.h"

namespace
{
int64 SharedFoodAuditCount(const TArray<FColdSteelItem>& Items,const TCHAR* Definition)
{int64 Result=0;for(const auto& I:Items)if(I.Definition==Definition)Result+=I.Count;return Result;}
bool SharedFoodAuditSameItems(const TArray<FColdSteelItem>& A,const TArray<FColdSteelItem>& B)
{
    if(A.Num()!=B.Num())return false;
    for(int32 N=0;N<A.Num();++N)if(!FColdSteelItem::StaticStruct()->CompareScriptStruct(&A[N],&B[N],0))return false;
    return true;
}
bool SharedFoodAuditProducts(const TArray<FColdSteelItem>& Items)
{
    TSet<FString> Ids;
    for(const auto& I:Items)
    {
        if(I.InstanceId.IsEmpty()||Ids.Contains(I.InstanceId))return false;Ids.Add(I.InstanceId);
        if(I.Definition==TEXT("spoiled_food")&&(I.Count<1||I.Count>10||I.StackMax!=10||I.Width!=1||I.Height!=1||I.bRotated))return false;
    }
    return true;
}
bool SharedFoodAuditNear(double A,double B){return FMath::Abs(A-B)<1.e-7;}
}

struct FSharedFoodSpoilageAuditAccess
{
    static void ClearActors(UColdSteelSharedInventorySubsystem* Shared)
    {
        for(auto& Pair:Shared->DropActors)if(Pair.Value.IsValid())Pair.Value->Destroy();
        Shared->DropActors.Reset();Shared->FoodContainerAnchors.Reset();
    }
    static void ForgetRuntime(UColdSteelSharedInventorySubsystem* Shared)
    {
        ClearActors(Shared);Shared->Current={};Shared->bInitialized=false;
        Shared->bBlocked=false;Shared->bCommitting=false;Shared->SaveSlot.Reset();
    }
    static void Run(UWorld* World,UColdSteelStatusModel* Model,
        TFunctionRef<void(bool,const FString&,const FString&)> Check)
    {
        FString Root=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("SourceAssets/FoodSpoilage20261015/TestRuns"));
        FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());
        FPaths::NormalizeDirectoryName(Root);FPaths::NormalizeDirectoryName(Saved);
        const bool Isolated=World&&Model&&World==Model->GetWorld()&&Model->IsAudit()
            &&Model->ProfileSlot().StartsWith(TEXT("ColdSteel_FoodSpoilageAudit_"))&&Saved.StartsWith(Root+TEXT("/"));
        Check(Isolated,TEXT("shared audit rejects formal saves and requires the random isolated profile"),Saved);
        if(!Isolated)return;
        const bool IdleWorld=World->GetNetMode()==NM_Standalone&&!World->GetNetDriver()&&World->NextURL.IsEmpty()
            &&GEngine&&GEngine->GetWorldContextFromWorld(World);
        Check(IdleWorld,TEXT("shared audit has an isolated idle world context"),TEXT("no existing driver, travel or online session"));
        if(!IdleWorld)return;
        // UWorld::AttemptDeriveFromURL supplies the same authority mode used
        // during listen bootstrap. No travel/tick/socket is started by this audit.
        TGuardValue<FString> ListenMode(World->NextURL,TEXT("/Engine/Maps/Entry?listen"));
        const bool AuthorityMode=World->GetNetMode()==NM_ListenServer;
        Check(AuthorityMode,TEXT("real world resolves listen authority for shared initialization"),TEXT("in-process bootstrap; transport is not exercised"));
        if(!AuthorityMode)return;
        auto* Shared=World->GetSubsystem<UColdSteelSharedInventorySubsystem>();
        Check(Shared&&!Shared->bInitialized,TEXT("shared subsystem is available and has no preexisting session"),FString());
        if(!Shared||Shared->bInitialized)return;
        const auto HostBefore=Model->Snapshot();
        TWeakObjectPtr<AFPSGAMECharacter> HostPawn=Model->RuntimePawn();
        const auto SharedBefore=Shared->Current;const FString OriginalSlot=Shared->SaveSlot;
        const auto OriginalHarvest=Shared->SharedHarvestModel;
        const float OriginalHarvestAccum=Shared->HarvestClockAccum;
        const bool OriginalBlocked=Shared->bBlocked,OriginalCommitting=Shared->bCommitting;
        TArray<TWeakObjectPtr<AActor>> GuestActors;
        ON_SCOPE_EXIT
        {
            for(auto It=GuestActors.CreateIterator();It;++It)
                if(auto* PS=Cast<AColdSteelPlayerState>(It->Get())){PS->ShadowModel=nullptr;PS->BoundProfileId.Invalidate();}
            for(auto& Actor:GuestActors)if(Actor.IsValid())Actor->Destroy();
            World->GetTimerManager().ClearTimer(Shared->FoodSpoilageTimer);
            ForgetRuntime(Shared);Shared->Current=SharedBefore;Shared->SaveSlot=OriginalSlot;
            Shared->SharedHarvestModel=OriginalHarvest;Shared->HarvestClockAccum=OriginalHarvestAccum;
            Shared->bBlocked=OriginalBlocked;Shared->bCommitting=OriginalCommitting;
            Model->AdoptNetMirror(HostBefore);if(HostPawn.IsValid())Model->AttachPawn(HostPawn.Get());
        };
        const bool Initialized=Shared->InitializeAuthority();
        Check(Initialized,TEXT("actual shared InitializeAuthority succeeds in isolated listen world"),Shared->WorldKey());
        if(!Initialized)return;
        const FString Slot=Shared->SaveSlot;
        const auto Now=ColdSteelFood::Clock(World);
        Check(Now.Id.IsValid(),TEXT("shared tests use the real authority food clock"),FString());
        if(!Now.Id.IsValid())return;
        auto Snapshot=[&]()
        {FColdSteelSharedInventoryData D;D.FoodVersion=1;D.FoodClockId=Now.Id;D.FoodClockDay=Now.Day;return D;};
        auto Food=[&](const TCHAR* Id,double Age,int64 Count=1)
        {auto I=Model->CreateItem(Id,Count);ColdSteelFood::Stamp(I,Now,Age);return I;};
        auto SeedAndReload=[&](const FColdSteelSharedInventoryData& Data,const FString& Label)
        {
            Shared->SaveSlot=Slot;
            const bool Wrote=Shared->SaveWorld(Data);Check(Wrote,Label+TEXT(" fixture saved by actual world writer"),Slot);
            if(!Wrote)return false;
            ForgetRuntime(Shared);
            const bool Loaded=Shared->InitializeAuthority();Check(Loaded,Label+TEXT(" actual shared load and settle"),Shared->WorldKey());
            return Loaded;
        };
        auto ReadWorld=[&]()
        {return Cast<UColdSteelSharedInventorySave>(UGameplayStatics::LoadGameFromSlot(Slot,0));};
        FString Reason;

        // A full warehouse page frees enough original cells for all converted units.
        {
            auto D=Snapshot();auto& C=D.Containers.Add(TEXT("FoodAudit.Full"));C.bSeeded=true;C.Pages=1;C.Revision=7;
            auto Meat=Food(TEXT("raw_large_lamb"),3.);Meat.Place=4;Meat.Container=TEXT("FoodAudit.Full");Meat.Cell=0;C.Items.Add(Meat);
            for(int32 Cell=0;Cell<216;++Cell)if(Cell!=0&&Cell!=1&&Cell!=18&&Cell!=19)
            {auto I=Model->CreateItem(TEXT("spoiled_food"),10);I.Place=4;I.Container=Meat.Container;I.Cell=Cell;C.Items.Add(I);}
            if(SeedAndReload(D,TEXT("full shared container")))
            {
                const auto* Result=Shared->Current.Containers.Find(Meat.Container);
                bool Blockers=Result!=nullptr;
                if(Result)for(int32 N=1;N<C.Items.Num();++N)
                {const auto* I=Result->Items.FindByPredicate([&](const auto& V){return V.InstanceId==C.Items[N].InstanceId;});Blockers&=I&&I->Cell==C.Items[N].Cell&&I->Count==10;}
                Check(Result&&Blockers&&Result->Revision==8&&SharedFoodAuditCount(Result->Items,TEXT("spoiled_food"))==2124
                    &&SharedFoodAuditProducts(Result->Items)&&!Result->Items.ContainsByPredicate([&](const auto& I){return I.InstanceId==Meat.InstanceId;}),
                    TEXT("full shared container conversion preserves blockers and exact footprint yield"),Reason);
                const auto* Disk=ReadWorld();const auto* SavedContainer=Disk?Disk->Data.Containers.Find(Meat.Container):nullptr;
                Check(Result&&SavedContainer&&SavedContainer->Revision==Result->Revision&&SharedFoodAuditSameItems(Result->Items,SavedContainer->Items),
                    TEXT("converted shared container is durably saved before publication"),Slot);
                const auto Once=Shared->Current;const bool Again=Shared->SettleFoodSpoilage(Reason);
                const auto* Repeated=Shared->Current.Containers.Find(Meat.Container);
                Check(Again&&Repeated&&Repeated->Revision==8&&SharedFoodAuditSameItems(Once.Containers.FindChecked(Meat.Container).Items,Repeated->Items),
                    TEXT("shared container repeat settlement cannot add output or revision"),Reason);
            }
        }

        // Observe the actual pickup actor replacement, including split output at one location.
        FColdSteelSharedInventoryData FreshGround,ConvertedGround;
        {
            FreshGround=Snapshot();auto Meat=Food(TEXT("raw_large_lamb"),1.,6);Meat.Place=2;
            Meat.Position=FVector(2300,4500,6700);Meat.WorldRotation=FRotator(10,20,30);FreshGround.Drops.Add(Meat);
            if(SeedAndReload(FreshGround,TEXT("shared ground")))
            {
                const auto* ActorEntry=Shared->DropActors.Find(Meat.InstanceId);
                TWeakObjectPtr<AColdSteelPickup> BeforeActor=ActorEntry?*ActorEntry:TWeakObjectPtr<AColdSteelPickup>();
                Check(BeforeActor.IsValid()&&BeforeActor->IsSharedPickup(),TEXT("fresh shared food has an actual registered replicated pickup actor"),Meat.InstanceId);
                ColdSteelFood::Stamp(Shared->Current.Drops[0],Now,3.);
                const bool Converted=Shared->SettleFoodSpoilage(Reason);ConvertedGround=Shared->Current;
                bool Actors=Shared->DropActors.Num()==3;
                for(const auto& I:Shared->Current.Drops)
                {
                    const auto* Found=Shared->DropActors.Find(I.InstanceId);
                    Actors&=Found&&Found->IsValid()&&Found->Get()->IsSharedPickup()
                        &&Found->Get()->GetActorLocation().Equals(Meat.Position,.01)&&I.WorldRotation.Equals(Meat.WorldRotation,.01);
                }
                Check(Converted&&Shared->Current.Drops.Num()==3&&SharedFoodAuditCount(Shared->Current.Drops,TEXT("spoiled_food"))==24
                    &&SharedFoodAuditProducts(Shared->Current.Drops)&&Actors&&!Shared->DropActors.Contains(Meat.InstanceId)
                    &&(!BeforeActor.IsValid()||BeforeActor->IsActorBeingDestroyed()),
                    TEXT("actual ground expiry replaces old actor with complete 10 10 4 output at its transform"),Reason);
                const auto* Disk=ReadWorld();Check(Disk&&SharedFoodAuditSameItems(Disk->Data.Drops,ConvertedGround.Drops),
                    TEXT("shared ground conversion survives actual world save"),Slot);
                ForgetRuntime(Shared);const bool Reloaded=Shared->InitializeAuthority();
                Check(Reloaded&&SharedFoodAuditSameItems(ConvertedGround.Drops,Shared->Current.Drops)&&Shared->DropActors.Num()==3,
                    TEXT("shared ground reload keeps output identities and does not duplicate actors or items"),Reason);
            }
        }
        if(!ConvertedGround.Drops.IsEmpty())
        {
            // Inject an interrupted write, not a fake save result: a valid complete
            // production-generated redo exists while the actual main slot is unreadable.
            auto* Journal=NewObject<UColdSteelSharedFoodJournal>();Journal->WorldKey=Slot;Journal->After=ConvertedGround;
            const FString JournalSlot=Slot+TEXT("_FoodTransaction");
            const bool JournalWritten=UGameplayStatics::SaveGameToSlot(Journal,JournalSlot,0);
            const TArray<uint8> Broken={0x46,0x4f,0x4f,0x44};
            const bool BrokenWritten=JournalWritten&&UGameplayStatics::SaveDataToSlot(Broken,Slot,0);
            Check(JournalWritten&&BrokenWritten,TEXT("isolated interrupted shared write fixture has durable redo and damaged main slot"),Slot);
            if(BrokenWritten)
            {
                ForgetRuntime(Shared);const bool Recovered=Shared->InitializeAuthority();const auto* Disk=ReadWorld();
                Check(Recovered&&Disk&&SharedFoodAuditSameItems(ConvertedGround.Drops,Disk->Data.Drops)
                    &&SharedFoodAuditSameItems(ConvertedGround.Drops,Shared->Current.Drops)
                    &&!UGameplayStatics::DoesSaveGameExist(JournalSlot,0),
                    TEXT("real initialization replays food redo before reading a damaged main slot exactly once"),Reason);
            }
        }

        for(const bool SameDomain:{false,true})
        {
            auto D=Snapshot();const FFoodClockSample Old{SameDomain?Now.Id:FGuid::NewGuid(),Now.Day+50.};
            auto Bread=Model->CreateItem(TEXT("bread"));ColdSteelFood::Stamp(Bread,Old,.75);Bread.Place=4;Bread.Container=TEXT("FoodAudit.Clock");
            D.FoodClockId=Old.Id;D.FoodClockDay=Old.Day+1.25;
            auto& C=D.Containers.Add(Bread.Container);C.bSeeded=true;C.Items.Add(Bread);
            if(SeedAndReload(D,SameDomain?TEXT("same-domain checkpoint rollback"):TEXT("cross-domain checkpoint")))
            {
                const auto* Container=Shared->Current.Containers.Find(Bread.Container);
                const auto* Result=Container&&Container->Items.Num()==1?&Container->Items[0]:nullptr;
                Check(Result&&Result->InstanceId==Bread.InstanceId&&Result->FoodClockId==Now.Id&&SharedFoodAuditNear(ColdSteelFood::AgeDays(*Result,Now),2.),
                    SameDomain?TEXT("shared checkpoint newer than host preserves age through clock rollback"):TEXT("shared cross-domain load materializes prior natural age before rebasing"),Reason);
            }
        }
        {
            auto D=Snapshot();auto Ground=Food(TEXT("raw_large_lamb"),3.);Ground.Place=2;D.Drops.Add(Ground);
            auto& C=D.Containers.Add(TEXT("FoodAudit.NoSpace"));C.bSeeded=true;C.Revision=12;
            auto Oversize=Food(TEXT("raw_large_lamb"),3.,21);Oversize.Place=4;Oversize.Container=TEXT("FoodAudit.NoSpace");C.Items.Add(Oversize);
            for(int32 Cell=0;Cell<216;++Cell)if(Cell!=0&&Cell!=1&&Cell!=18&&Cell!=19)
            {auto I=Model->CreateItem(TEXT("spoiled_food"),10);I.Place=4;I.Container=Oversize.Container;I.Cell=Cell;C.Items.Add(I);}
            Shared->SaveSlot=Slot;const bool Wrote=Shared->SaveWorld(D);ForgetRuntime(Shared);
            const bool Accepted=Wrote&&Shared->InitializeAuthority();const auto* Disk=ReadWorld();
            const auto* Container=Shared->Current.Containers.Find(Oversize.Container);
            Check(Wrote&&!Accepted&&Container&&Container->Revision==12&&SharedFoodAuditSameItems(C.Items,Container->Items)
                &&SharedFoodAuditSameItems(D.Drops,Shared->Current.Drops)&&Disk&&SharedFoodAuditSameItems(D.Drops,Disk->Data.Drops)
                &&!UGameplayStatics::DoesSaveGameExist(Slot+TEXT("_FoodTransaction"),0),
                TEXT("unplaceable legacy shared stack leaves the entire world proposal unchanged including earlier ground conversion"),Reason);
        }
        // Give guest operations a clean shared world; no previous failure fixture
        // may cause unrelated ImportPlayerDrops to block shadow attachment.
        if(!SeedAndReload(Snapshot(),TEXT("guest merge shared world")))return;

        auto MakeGuest=[&]()
        {
            auto* PC=World->SpawnActor<APlayerController>();auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();
            auto* PS=World->SpawnActor<AColdSteelPlayerState>();
            GuestActors.Add(PC);GuestActors.Add(Pawn);GuestActors.Add(PS);
            if(PC&&Pawn&&PS){PS->SetOwner(PC);PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);}
            return PS;
        };
        auto Guest=HostBefore;Guest.NetworkProfileId=FGuid::NewGuid();Guest.Items.Reset();Guest.CampfireInventoryRevision=0;Guest.CampfireWorldReceipts.Reset();
        Guest.ActiveProductionTool.Reset();Guest.ActiveWeaponSlot=6;Guest.Health=100;Guest.ForgeJob={};Guest.GunAssemblyJob={};Guest.WoodworkingJob={};Guest.AlchemyJob={};
        Guest.Hotbar.Init(TEXT(""),4);Guest.HotbarDefinitions.Init(TEXT(""),4);for(auto& B:Guest.QuickBindings)B={};
        Guest.FoodVersion=1;Guest.FoodClockId=Now.Id;Guest.FoodClockDay=Now.Day;
        const FFoodClockSample PreviousHost{FGuid::NewGuid(),10.};
        auto Meat=Food(TEXT("raw_large_lamb"),.25);ColdSteelFood::Stamp(Meat,PreviousHost,.25);
        Guest.Items.Add(Meat);Guest.FoodClockId=PreviousHost.Id;Guest.FoodClockDay=11.25;
        ColdSteelFood::ObserveReplicatedClock(Guest,Now);
        Check(SharedFoodAuditNear(ColdSteelFood::AgeDays(Guest.Items[0],Now),1.5),
            TEXT("new host clock arriving before first guest upload retains old checkpoint age"),FString());
        auto* PS=MakeGuest();const bool Bound=PS&&PS->GetPawn()&&PS->ApplyGuestProfile(Guest);
        Check(Bound&&PS->ShadowModel&&PS->CampfireGuestSlot()==TEXT("ColdSteelMP_Profile_")+Guest.NetworkProfileId.ToString(EGuidFormats::Digits),
            TEXT("actual guest profile initialization binds a unique host-side isolated slot"),PS?PS->CampfireGuestSlot():FString());
        if(!Bound||!PS->ShadowModel)return;
        const auto* InitiallyBound=PS->ShadowModel->FindItem(Meat.InstanceId);
        Check(InitiallyBound&&SharedFoodAuditNear(ColdSteelFood::AgeDays(*InitiallyBound,Now),1.5),
            TEXT("actual first ApplyGuestProfile preserves food age after early cross-host clock"),FString());
        auto EarlyClockUpload=PS->ShadowModel->Snapshot();
        ColdSteelFood::Stamp(EarlyClockUpload.Items[0],PreviousHost,.25);
        EarlyClockUpload.FoodClockId=PreviousHost.Id;EarlyClockUpload.FoodClockDay=10.25;
        ColdSteelFood::ObserveReplicatedClock(EarlyClockUpload,Now);
        const bool EarlyMerged=PS->ApplyGuestProfile(EarlyClockUpload,true);
        const auto* Existing=PS->ShadowModel->FindItem(Meat.InstanceId);
        Check(EarlyMerged&&Existing&&SharedFoodAuditNear(ColdSteelFood::AgeDays(*Existing,Now),1.5),
            TEXT("early cross-host clock upload cannot refresh an older existing authority instance"),FString());
        auto Stale=PS->ShadowModel->Snapshot();ColdSteelFood::Stamp(Stale.Items[0],Now,0.);
        const auto AuthorityFood=PS->ShadowModel->Items()[0];
        const bool Merged=PS->ApplyGuestProfile(Stale);const auto* Kept=PS->ShadowModel->FindItem(Meat.InstanceId);
        Check(Merged&&Kept&&SharedFoodAuditNear(ColdSteelFood::AgeDays(*Kept,Now),1.5)
            &&Kept->FoodVersion==AuthorityFood.FoodVersion&&Kept->FoodClockId==AuthorityFood.FoodClockId
            &&Kept->FoodSampleDay==AuthorityFood.FoodSampleDay&&Kept->FoodAgeDays==AuthorityFood.FoodAgeDays,
            TEXT("real ApplyGuestProfile cannot refresh an existing instance with a younger same-receipt upload"),FString());
        auto Expired=PS->ShadowModel->Snapshot();ColdSteelFood::Stamp(Expired.Items[0],Now,3.);PS->ShadowModel->AdoptNetMirror(Expired);
        const bool Converted=PS->ShadowModel->SettleFoodSpoilage(true);const auto Settled=PS->ShadowModel->Snapshot();
        Check(Converted&&Settled.CampfireInventoryRevision>Stale.CampfireInventoryRevision
            &&SharedFoodAuditCount(Settled.Items,TEXT("spoiled_food"))==4&&!PS->ShadowModel->FindItem(Meat.InstanceId),
            TEXT("actual guest food transaction persists expiry and advances inventory receipt"),PS->ShadowModel->ResultMessage());
        const bool OldUpload=PS->ApplyGuestProfile(Stale);
        Check(OldUpload&&SharedFoodAuditCount(PS->ShadowModel->Items(),TEXT("spoiled_food"))==4&&!PS->ShadowModel->FindItem(Meat.InstanceId)
            &&PS->ShadowModel->InventoryRevision()==Settled.CampfireInventoryRevision,
            TEXT("old guest upload cannot resurrect raw meat after committed expiry"),FString());
        const auto Once=PS->ShadowModel->Snapshot();const bool Again=PS->ApplyGuestProfile(Stale);
        Check(Again&&SharedFoodAuditSameItems(Once.Items,PS->ShadowModel->Items())&&PS->ShadowModel->InventoryRevision()==Once.CampfireInventoryRevision,
            TEXT("repeated stale guest upload cannot duplicate spoiled portions or advance receipt"),FString());
        const bool GuestSaved=PS->SaveShadowToHostDisk();const FString GuestSlot=PS->CampfireGuestSlot();
        const auto* GuestDisk=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(GuestSlot,0));
        Check(GuestSaved&&GuestDisk&&SharedFoodAuditSameItems(Once.Items,GuestDisk->Profile.Items),
            TEXT("actual host guest-slot save and load preserve expiry output"),GuestSlot);
        // Drop the live owner/cache source. The new PlayerState must take the
        // durable guest-slot branch when receiving the same old profile upload.
        PS->ShadowModel=nullptr;PS->BoundProfileId.Invalidate();PS->Destroy();
        auto* Reconnected=MakeGuest();const bool Restored=Reconnected&&Reconnected->ApplyGuestProfile(Stale);
        Check(Restored&&Reconnected->ShadowModel&&SharedFoodAuditCount(Reconnected->ShadowModel->Items(),TEXT("spoiled_food"))==4
            &&!Reconnected->ShadowModel->FindItem(Meat.InstanceId)&&Reconnected->ShadowModel->InventoryRevision()==Once.CampfireInventoryRevision,
            TEXT("guest reconnect loads the durable host receipt and still rejects stale raw inventory"),GuestSlot);
    }
};

void RunSharedFoodSpoilageAudit(UWorld* World,UColdSteelStatusModel* Model,
    TFunctionRef<void(bool,const FString&,const FString&)> Check)
{FSharedFoodSpoilageAuditAccess::Run(World,Model,Check);}
