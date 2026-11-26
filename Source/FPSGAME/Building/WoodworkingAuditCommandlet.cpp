#include "WoodworkingAuditCommandlet.h"
#include "WoodworkingSystem.h"
#include "WoodworkingQuality.h"
#include "../Weapons/WeaponDamagePanel.h"
#include "../Combat/CoreCombatFormula.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "../Multiplayer/ColdSteelStationNetwork.h"
#include "../Multiplayer/ColdSteelProfileTransfer.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../FPSGAMECharacter.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "PhysicsEngine/BodySetup.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"

int32 UWoodworkingAuditCommandlet::Main(const FString& Params)
{
    FString Root;if(!FParse::Value(*Params,TEXT("WoodAuditRoot="),Root))return 2;
    Root=FPaths::ConvertRelativePathToFull(Root);FPaths::NormalizeDirectoryName(Root);
    FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());FPaths::NormalizeDirectoryName(Saved);
    const FString Allowed=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("SourceAssets/WoodCoreAudit20261026"));
    if(!Root.StartsWith(Allowed+TEXT("/"))||!Saved.StartsWith(Root+TEXT("/")))return 2;
    const FString Original=FCommandLine::Get(),Suffix=FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=WoodAudit_")+Suffix));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("WoodAuditFixture"));
    auto* World=GI->GetWorld();
    ON_SCOPE_EXIT {GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);};
    auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();auto* Catalog=GI->GetSubsystem<UWoodworkingSystem>();
    if(!Host||!Host->IsAudit()||!Host->ProfileSlot().StartsWith(TEXT("ColdSteel_WoodAudit_"))||!Catalog)return 2;
    int32 Checks=0,Failures=0;FString Report;
    auto Check=[&](bool Pass,const FString& Label)
    {++Checks;if(!Pass)++Failures;const FString Line=(Pass?TEXT("PASS "):TEXT("FAIL "))+Label;Report+=Line+TEXT("\n");UE_LOG(LogTemp,Display,TEXT("WOOD_AUDIT %s"),*Line);return Pass;};
    ON_SCOPE_EXIT
    {
        Report+=FString::Printf(TEXT("checks=%d failures=%d\ncoverage=isolated authority sessions, real catalogs/assets, persistence and network serialization; no NetDriver/socket clients\nsaved_root=%s\n"),Checks,Failures,*Saved);
        FFileHelper::SaveStringToFile(Report,*(Root/TEXT("report.txt")));
        UE_LOG(LogTemp,Display,TEXT("WOOD_AUDIT_COMPLETE checks=%d failures=%d"),Checks,Failures);
    };
    if(!Check(Catalog->Cores().Num()==6&&Catalog->Patterns().Num()==2,TEXT("six cores and both current woodworking recipes")))return 1;
    auto Blank=Host->Snapshot();Blank.Items.Reset();Blank.AmmoPouch.Reset();Blank.ActiveProductionTool.Reset();
    Blank.Hotbar.Init(TEXT(""),4);Blank.HotbarDefinitions.Init(TEXT(""),4);for(auto& B:Blank.QuickBindings)B={};
    Blank.ForgeJob={};Blank.GunAssemblyJob={};Blank.WoodworkingJob={};Blank.AlchemyJob={};
    Blank.CampfireInventoryRevision=0;Blank.CampfireWorldReceipts.Reset();Host->AdoptNetMirror(Blank);
    auto GuestBlank=Blank;GuestBlank.NetworkProfileId=FGuid::NewGuid();
    auto* Guest=Host->CreateShadowModel(GuestBlank);if(!Guest)return 2;
    Guest->AddToRoot();ON_SCOPE_EXIT {Guest->RemoveFromRoot();};
    Guest->CurrentPawn=World->SpawnActor<AFPSGAMECharacter>();Guest->bAudit=true;
    auto OtherBlank=Blank;OtherBlank.NetworkProfileId=FGuid::NewGuid();
    auto* Other=Host->CreateShadowModel(OtherBlank);Other->AddToRoot();ON_SCOPE_EXIT {Other->RemoveFromRoot();};
    auto* Session=Catalog->CreateNetworkSession(Guest);Session->AddToRoot();ON_SCOPE_EXIT {Session->RemoveFromRoot();};
    FString Why;
    auto Seed=[&](FName Pattern,FName Core)
    {
        Session->Close();Guest->AdoptNetMirror(GuestBlank);Session->Open(false);Session->Select(Pattern);Session->SelectCore(Core);
        TArray<FColdSteelCraftingInput> Inputs;Session->InputsFor(Inputs);auto State=Guest->Snapshot();
        for(const auto& Input:Inputs)if(!ColdSteelInventory::Insert(State.Items,Guest->CreateItem(Input.Item,Input.Count*2)))return false;
        return Guest->CommitState(State);
    };
    FColdSteelProfile PaidFixture;
    for(const auto& Core:Catalog->Cores())
    {
        const FString Tag=Core.Id.ToString();const auto Item=Host->CreateItem(Tag);
        Check(!Item.Data.IsEmpty()&&ColdSteelInventory::Text(Item,TEXT("name"))==Core.Name,Tag+TEXT(" item definition"));
        auto* Mesh=LoadObject<UStaticMesh>(nullptr,*ColdSteelInventory::Text(Item,TEXT("world_mesh")));
        Check(Mesh&&Mesh->GetBodySetup()&&Mesh->GetBodySetup()->AggGeom.GetElementCount()>0,Tag+TEXT(" saved mesh and pickup collision"));
        Check(Cast<UMaterialInterface>(Core.Material.TryLoad())!=nullptr,Tag+TEXT(" saved workpiece material"));
        for(const auto& Pattern:Catalog->Patterns())
        {
            const FString Label=Tag+TEXT(" / ")+Pattern.Id.ToString();
            if(!Check(Seed(Pattern.Id,Core.Id),Label+TEXT(" material fixture")))continue;
            TArray<FColdSteelCraftingInput> Inputs;Session->InputsFor(Inputs);
            Guest->AuditFailNextSave=true;
            Check(!Session->Start(false)&&!Session->HasPendingJob()&&Guest->CountMaterial(Tag)==2,Label+TEXT(" failed payment preserves inventory"));
            if(!Check(Session->Start(false),Label+TEXT(" authority starts paid workpiece")))continue;
            bool Exact=true;for(const auto& Input:Inputs)Exact&=Guest->CountMaterial(Input.Item)==Input.Count&&Session->Job().PaidMaterials.FindRef(Input.Item)==Input.Count;
            Check(Exact&&Session->Job().Core==Core.Id&&Session->Job().MaterialBonus==Core.Bonus&&Session->Job().QualityVersion==2,
                Label+TEXT(" one core plus fixed materials; authority bonus"));
            Check(Session->ProcessingBonus()==0&&Session->MaterialBonus()==Core.Bonus,Label+TEXT(" fresh job starts at material floor"));
            Check(!Session->SelectCore(TEXT("wood_core_plain"))&&!Session->Start(false),Label+TEXT(" locked core and duplicate start rejected"));
            const auto Paid=Guest->Snapshot();PaidFixture=Paid;
            Check(Session->Suspend()&&Session->CanResume()&&Session->Resume()&&Guest->CountMaterial(Tag)==1&&Session->Job().Id==Paid.WoodworkingJob.Id,
                Label+TEXT(" pause and resume do not repay"));
            auto* Net=Session->NetworkState();TArray<uint8> Blob;auto* Copy=NewObject<UColdSteelWoodNetState>();
            Check(ColdSteelProfileTransfer::SaveToBlob(Net,Blob)&&ColdSteelProfileTransfer::BlobToSaveObject(Blob,Copy)
                &&Copy->Job.Core==Core.Id&&Copy->Job.MaterialBonus==Core.Bonus&&Copy->Job.QualityVersion==2&&Copy->Job.PaidMaterials.OrderIndependentCompareEqual(Net->Job.PaidMaterials),
                Label+TEXT(" actual compressed network envelope preserves payment and quality"));
            for(double Score:{0.,50.,100.})
            {
                auto Product=Session->Job().Item;const auto Channel=ColdSteelWoodQuality::Channel(Product);
                const double Expected=1.+Core.Bonus+.15*Score/100.;
                Check(ColdSteelWoodQuality::Apply(Product,Score,Core.Bonus,Core.Id,2)
                    &&FMath::IsNearlyEqual(ColdSteelWoodQuality::Multiplier(Product,Channel),Expected,1.e-9),
                    Label+FString::Printf(TEXT(" score %.0f multiplier %.3f"),Score,Expected));
                if(Channel==ColdSteelWoodQuality::EChannel::Physical)
                {
                    const auto Base=ColdSteelWeaponDamage::Evaluate(Session->Job().Item,Host,100.);
                    const auto Damage=ColdSteelWeaponDamage::Evaluate(Product,Host,100.);
                    Check(FMath::IsNearlyEqual(Damage.BasePhysical,Base.BasePhysical*Expected,1.e-9)
                        &&FMath::IsNearlyEqual(Damage.AddedPhysical,Base.AddedPhysical*Expected,1.e-9)
                        &&Damage.AddedMagic==Base.AddedMagic,Label+TEXT(" combat formula scales only bow physical channels"));
                }
                else Check(Host->ItemMagicAttack(Product)==CoreCombatFormula::Round(Host->ItemMagicAttack(Session->Job().Item)*Expected),
                    Label+TEXT(" real staff magic-attack formula uses material and score"));
                const auto Trusted=Product;ColdSteelWoodQuality::Apply(Product,100,.10,TEXT("wood_core_spirit"),2);
                TArray<FColdSteelItem> Upload{Product},Authority{Trusted};ColdSteelWoodQuality::PreserveAuthoritative(Upload,Authority);
                Check(Upload[0].Data==Trusted.Data,Label+TEXT(" client cannot overwrite known quality metadata"));
            }
            Session->Suspend();auto Finished=Guest->Snapshot();Finished.WoodworkingJob.bFinished=true;Finished.WoodworkingJob.bPassed=true;Finished.WoodworkingJob.Quality=80;
            Guest->AdoptNetMirror(Finished);Session->Open(false);Guest->AuditFailNextSave=true;
            Check(!Session->Claim()&&Session->HasPendingJob(),Label+TEXT(" failed delivery retains workpiece"));
            Check(Session->Claim()&&!Session->HasPendingJob()&&!Session->Claim(),Label+TEXT(" exactly one successful delivery"));
            const auto* Product=Guest->FindItem(Finished.WoodworkingJob.Item.InstanceId);
            Check(Product&&FMath::IsNearlyEqual(ColdSteelWoodQuality::Multiplier(*Product,ColdSteelWoodQuality::Channel(*Product)),1.+Core.Bonus+.12,1.e-9),Label+TEXT(" delivered item uses saved material and score"));
        }
    }
    Check(Host->Items().IsEmpty()&&Other->Items().IsEmpty()&&Host->WoodworkingJob().Id.IsEmpty()&&Other->WoodworkingJob().Id.IsEmpty(),TEXT("guest payments and rewards never mutate host or second guest"));
    Guest->AdoptNetMirror(PaidFixture);Session->Open(false);Session->Resume();
    Session->Board.BeginStroke();Session->Board.CutSawSweep(FVector2D(2,0),FVector2D(2,256),FVector2D(5,0),FVector2D(5,256),2.);Session->Board.EndStroke();
    Check(Session->Board.Revision()>0&&Session->Suspend(),TEXT("real cut mask checkpoint saved"));
    const auto Checkpoint=Guest->Snapshot();
    auto* Restored=Catalog->CreateNetworkSession(Guest);Restored->AddToRoot();ON_SCOPE_EXIT {Restored->RemoveFromRoot();};
    Check(Restored->Open(false)&&Restored->Mask().Wood()==Session->Mask().Wood()&&Restored->Core()==Session->Core()&&Restored->CanResume(),TEXT("reconnect session restores cut mask and chosen core"));
    auto* Disk=NewObject<UColdSteelProfileSave>();Disk->Profile=Checkpoint;TArray<uint8> DiskBlob;
    Check(ColdSteelProfileTransfer::SaveToBlob(Disk,DiskBlob),TEXT("profile save serializes woodworking fields"));
    auto* Reloaded=ColdSteelProfileTransfer::BlobToSave(DiskBlob);
    Check(Reloaded&&Reloaded->Profile.WoodworkingJob.Mask==Checkpoint.WoodworkingJob.Mask&&Reloaded->Profile.WoodworkingJob.Core==Checkpoint.WoodworkingJob.Core,
        TEXT("profile roundtrip preserves checkpoint and material"));
    auto Legacy=Checkpoint;Legacy.WoodworkingJob.QualityVersion=1;Legacy.WoodworkingJob.Core=NAME_None;Legacy.WoodworkingJob.MaterialBonus=0;
    Guest->AdoptNetMirror(Legacy);Restored->Open(false);
    Check(Restored->CanResume()&&Restored->Resume(),TEXT("legacy paid job resumes without new core requirement"));
    for(double Score:{0.,50.,100.})
    {auto Product=Legacy.WoodworkingJob.Item;Check(ColdSteelWoodQuality::Apply(Product,Score)&&FMath::IsNearlyEqual(ColdSteelWoodQuality::Multiplier(Product,ColdSteelWoodQuality::Channel(Product)),.75+.005*Score,1.e-9),TEXT("legacy item keeps original curve"));}
    Restored->Suspend();Guest->AdoptNetMirror(PaidFixture);Session->Open(false);TArray<FColdSteelCraftingInput> Refund;
    Check(Session->GetDiscardRefund(Refund,Why)&&!Refund.ContainsByPredicate([](const auto& I){return I.Item.StartsWith(TEXT("wood_core_"));}),TEXT("one paid core refunds zero after floor division"));
    const int64 WoodBefore=Guest->CountMaterial(TEXT("wood"));
    Check(Session->Discard()&&!Session->HasPendingJob()&&Guest->CountMaterial(TEXT("wood"))==WoodBefore+1,TEXT("discard returns half the two paid wood"));

    // Outer network transaction can fail after the subsystem's staged commit.
    Seed(Catalog->Patterns()[0].Id,TEXT("wood_core_spirit"));const auto BeforeStart=Guest->Snapshot();Session->Start(false);
    Guest->AdoptNetMirror(BeforeStart);Session->AuthorityTransactionFinished(TEXT("wood.start"),false,TEXT("injected outer commit failure"));
    Check(Session->State()==EWoodworkingPhase::Preview&&!Session->HasPendingJob()&&Session->CanStart(false,Why),TEXT("outer start rollback restores retryable preview"));
    auto Ready=PaidFixture;Ready.WoodworkingJob.bFinished=true;Ready.WoodworkingJob.bPassed=true;Ready.WoodworkingJob.Quality=90;
    Guest->AdoptNetMirror(Ready);Session->Open(false);Session->Claim();Guest->AdoptNetMirror(Ready);
    Session->AuthorityTransactionFinished(TEXT("wood.claim"),false,TEXT("injected outer commit failure"));
    Check(Session->State()==EWoodworkingPhase::Complete&&Session->HasPendingJob()&&Session->Claim(),TEXT("outer delivery rollback restores claimable workpiece"));

    // Run the real receipt consumer with an older same-job checkpoint.
    auto Newer=PaidFixture;Newer.WoodworkingJob.Elapsed=20;Host->AdoptNetMirror(Newer);
    auto* Reply=NewObject<UColdSteelInventoryReply>();Reply->bSuccess=true;Reply->bWorldAction=true;Reply->Revision=Host->InventoryRevision();
    Reply->WoodworkingJob=PaidFixture.WoodworkingJob;Reply->WoodworkingJob.Elapsed=5;
    Check(Host->ApplyNetworkInventoryReply(Reply,nullptr)&&Host->WoodworkingJob().Elapsed==20,TEXT("late inventory receipt cannot rewind newer woodworking checkpoint"));
    auto Complete=Host->Snapshot();Complete.WoodworkingJob.bFinished=true;Complete.WoodworkingJob.bPassed=true;Host->AdoptNetMirror(Complete);
    Check(Host->ApplyNetworkInventoryReply(Reply,nullptr)&&Host->WoodworkingJob().bFinished,TEXT("late receipt cannot undo finished workpiece"));
    Reply->Revision++;Reply->WoodworkingJob={};
    Check(Host->ApplyNetworkInventoryReply(Reply,nullptr)&&Host->WoodworkingJob().Id.IsEmpty(),TEXT("real claim receipt clears job despite progress merge"));
    Host->AdoptNetMirror(PaidFixture);Catalog->Open(false);Catalog->bClaiming=true;
    Catalog->NetworkTransactionFinished(TEXT("wood.start"),true,TEXT("late receipt for replaced pawn"),false);
    Check(!Catalog->TransactionPending()&&!Catalog->NetworkOpen()&&Catalog->State()==EWoodworkingPhase::Abandoned&&Catalog->HasPendingJob(),
        TEXT("old pawn receipt releases wait without restarting new pawn session or deleting workpiece"));

    auto Logs=Blank;ColdSteelInventory::Insert(Logs.Items,Host->CreateItem(TEXT("wood"),2));Host->AdoptNetMirror(Logs);
    Check(GI->GetSubsystem<UColdSteelCraftingSystem>()->Craft(TEXT("craft_wood_core_plain"),1,Why)
        &&Host->CountMaterial(TEXT("wood"))==0&&Host->CountMaterial(TEXT("wood_core_plain"))==1,TEXT("ordinary workbench converts two wood into one plain core"));

    // F6 belongs only to the local authority; remote shadow models still pay.
    Host->AdoptNetMirror(Blank);auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();PC->Possess(World->SpawnActor<AFPSGAMECharacter>());
    auto* Tuning=GI->GetSubsystem<UDevelopmentTuningSubsystem>();
    Check(Tuning->SetEnabled(EDevelopmentTuningOption::FreeCrafting,true,PC)&&UDevelopmentTuningSubsystem::IsFreeCrafting(Host)&&!UDevelopmentTuningSubsystem::IsFreeCrafting(Guest),TEXT("F6 override cannot leak into remote profile"));
    Guest->AdoptNetMirror(GuestBlank);Session->Open(false);Session->Select(Catalog->Patterns()[0].Id);
    Check(!Session->SelectCore(TEXT("invalid_core"))&&!Session->Start(false)&&!Session->HasPendingJob(),TEXT("remote authority rejects invalid core and insufficient materials even when host F6 is on"));
    Catalog->Open(false);Catalog->Select(Catalog->Patterns()[0].Id);Catalog->SelectCore(TEXT("wood_core_spirit"));
    Check(Catalog->Start(false)&&Catalog->Job().bMaterialsWaived&&Catalog->Job().PaidMaterials.IsEmpty()&&Catalog->MaterialBonus()==.10,TEXT("F6 free work retains material floor without paid inputs"));
    Catalog->Suspend();Check(Catalog->Discard()&&Host->Items().IsEmpty(),TEXT("free workpiece cannot generate refunded materials"));
    Tuning->DisableAll(PC);
    return Failures?1:0;
}
