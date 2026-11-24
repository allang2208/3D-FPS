#include "FPSGAME/Building/WoodworkingAuditCommandlet.h"
#include "FPSGAME/Building/ForgingSystem.h"
#include "FPSGAME/Building/WoodworkingSystem.h"
#include "FPSGAME/Tasks/BlacksmithApprenticeship.h"
#include "FPSGAME/Tasks/CarpenterApprenticeship.h"
#include "FPSGAME/UI/ColdSteelStatusModel.h"
#include "FPSGAME/FPSGAMECharacter.h"
#include "FPSGAME/Weapons/RavenQuillChargeComponent.h"
#include "FPSGAME/Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/StaticMesh.h"
#include "FPSGAME/Weapons/EagleTalonGuardComponent.h"
#include "FPSGAME/Multiplayer/ColdSteelPlayerProtocol.h"
#include "FPSGAME/Skills/ColdSteelSkillTypes.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Misc/ScopeExit.h"
#include "HAL/PlatformProcess.h"

namespace Smith = BlacksmithApprenticeship;
namespace Wood = CarpenterApprenticeship;

int32 UWoodworkingAuditCommandlet::Main(const FString& Params)
{
    FString ReportPath;
    if (!FParse::Param(*Params, TEXT("LessonBranchAudit")) || !FParse::Value(*Params,TEXT("Report="),ReportPath)) return 2;
    const FString Saved = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());
    if (!Saved.Contains(TEXT("/ArtisanLessonBranches/")) || !ReportPath.Contains(TEXT("ArtisanLessonBranches"))) return 2;
    int32 Pass = 0, Fail = 0;
    FString Report;
    auto Check = [&](bool Ok, const TCHAR* Name, const FString& Detail = FString())
    {
        Ok ? ++Pass : ++Fail;
        Report += FString::Printf(TEXT("%s %s %s\n"), Ok ? TEXT("PASS") : TEXT("FAIL"), Name, *Detail);
        FFileHelper::SaveStringToFile(Report,*ReportPath,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        return Ok;
    };
    auto* GI = NewObject<UGameInstance>(GEngine);
    GI->AddToRoot();
    GI->InitializeStandalone(TEXT("LessonBranchAuditWorld"));
    auto* World = GI->GetWorld();
    ON_SCOPE_EXIT {
        GI->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); GI->RemoveFromRoot();
    };
    auto* Model = GI->GetSubsystem<UColdSteelStatusModel>();
    auto* Forge = GI->GetSubsystem<UColdSteelForgingSystem>();
    auto* Shop = GI->GetSubsystem<UWoodworkingSystem>();
    if (!Check(Model && Model->IsAudit() && Forge && Shop && Model->ProfileSlot()==TEXT("ColdSteel_LessonBranchAudit"), TEXT("isolated standalone authority, audit profile and workstations ready"), Saved)) return 2;
    auto Blank = Model->Snapshot();
    Blank.Items.Reset(); Blank.AmmoPouch.Reset(); Blank.ActiveProductionTool.Reset();
    Blank.Hotbar.Init(TEXT(""),4); Blank.HotbarDefinitions.Init(TEXT(""),4);
    for (auto& B : Blank.QuickBindings) B={};
    Blank.ForgeJob={}; Blank.WoodworkingJob={}; Blank.CampfireWorldReceipts.Reset();
    Blank.BlacksmithApprenticeshipStage=0; Blank.CarpenterApprenticeshipStage=0;
    Model->AdoptNetMirror(Blank);
    auto* PC = World->SpawnActor<APlayerController>();
    auto* Pawn = World->SpawnActor<AFPSGAMECharacter>();
    if (!Check(PC && Pawn, TEXT("fixture pawn and controller spawned"))) return 2;
    PC->SetAsLocalPlayerController(); PC->Possess(Pawn); Model->CurrentPawn = Pawn;
    FString Why;
    auto Count = [&](const FString& Definition)
    {
        int64 N=0;
        for (const auto& I : Model->Items()) if (I.Definition==Definition) N+=I.Count;
        return N;
    };
    auto SmithStage = [&]() { return Smith::Stage(Model->ProfileView()); };
    auto WoodStage = [&]() { return Wood::Stage(Model->ProfileView()); };
    if (!Check(Smith::Accept(Model,FString(),Why) && SmithStage()==Smith::EStage::Mining && Count(TEXT("tool_pickaxe"))==1, TEXT("mining lesson grants a pickaxe"),Why)) return 1;
    Check(Smith::Accept(Model,FString(),Why) && Count(TEXT("tool_pickaxe"))==1,TEXT("duplicate accept gives no second pickaxe"));
    auto Mine=Model->Snapshot();
    auto Ore=Model->CreateItem(TEXT("iron_ore"),4);
    Check(Smith::InsertPickup(Mine,Ore)&&Smith::OreCollected(Smith::Stage(Mine))==0,TEXT("ordinary inventory ore grants no mining progress"));
    Mine=Model->Snapshot();
    Ore.bFreshMinedIron=true;
    Check(Smith::InsertPickup(Mine,Ore)&&Smith::OreCollected(Smith::Stage(Mine))==4,TEXT("four freshly mined ore give 4/10"));
    auto MoreOre=Model->CreateItem(TEXT("iron_ore"),6);MoreOre.bFreshMinedIron=true;
    if(!Check(Smith::InsertPickup(Mine,MoreOre)&&Model->CommitState(Mine)&&Model->ReloadProfile()&&SmithStage()==Smith::EStage::ReturnOre,TEXT("fresh pickup and 10/10 delivery stage survive reload")))return 1;
    Model->AuditFailNextSave=true;
    Check(!Smith::Accept(Model,FString(),Why)&&Count(TEXT("iron_ore"))==10&&SmithStage()==Smith::EStage::ReturnOre,TEXT("failed delivery saves neither debit nor grant"));
    if(!Check(Smith::Accept(Model,FString(),Why)&&Count(TEXT("iron_ore"))==3&&Count(TEXT("search_forging_alloy_blank"))==1&&SmithStage()==Smith::EStage::Smelting,TEXT("deliver ten ore and receive the smelting kit"),Why))return 1;
    auto Smelt=Model->Snapshot();
    Smelt.Items.RemoveAll([](const auto& Item){return Item.Definition==TEXT("iron_ore")||Item.Definition==TEXT("wood");});
    // Inject the furnace output at its collection callback; the forge below runs the real workstation.
    Smith::CollectIngots(Smelt,1);
    Check(Smith::IngotsCollected(Smith::Stage(Smelt))==1,TEXT("first furnace output gives one third"));
    Smith::CollectIngots(Smelt,2);
    if(!Check(ColdSteelInventory::Insert(Smelt.Items,Model->CreateItem(TEXT("ironIngot"),3))&&Model->CommitState(Smelt)&&SmithStage()==Smith::EStage::Materials,TEXT("three collected ingots unlock the forge")))return 1;
    if (!Check(Wood::Accept(Model,FString(),Why) && WoodStage()==Wood::EStage::Materials, TEXT("carpenter accepts and grants real staff recipe materials"),Why)) return 1;
    const auto Accepted = Model->Snapshot();
    const auto Rev = Model->InventoryRevision();
    Check(Smith::Accept(Model,FString(),Why) && Wood::Accept(Model,FString(),Why) && Rev==Model->InventoryRevision(), TEXT("reversed duplicate teaching requests do not grant a second material pack"));
    auto SmithStart = [&]()
    {
        Model->AdoptNetMirror(Accepted);
        return Forge->Start(Smith::TargetRecipe,Why) && SmithStage()==Smith::EStage::Hammering && !Forge->Job().PaidMaterials.IsEmpty();
    };
    if (!Check(SmithStart(),TEXT("smith starts paid forged steel greatsword"),Why)) return 1;
    Check(!Forge->Claim(Why),TEXT("smith cannot claim an unfinished job"));
    if (!Check(Forge->Finish(Why) && !Forge->Job().bHammeredBlank && SmithStage()==Smith::EStage::Materials, TEXT("smith finish without any hammer contact remains materials"),Why)) return 1;
    Check(Forge->Claim(Why) && Count(TEXT("ue_forged_steel_greatsword"))==1 && SmithStage()==Smith::EStage::Materials, TEXT("unworked forge output can be collected but grants no lesson credit"),Why);
    if (!Check(SmithStart(),TEXT("smith paid retry for discard"),Why)) return 1;
    auto Strike = [&](bool Hit)
    {
        FPlatformProcess::Sleep(float(UColdSteelForgingSystem::Preparation+.10));
        Forge->Tick(0);
        FVector2D UV; float Life=0;
        if (!Forge->Target(UV,Life)) return false;
        const auto Index=Forge->TargetIndex();
        const FVector2D Contact = Hit ? UV : FVector2D(UV.X<.5 ? 1. : 0.,UV.Y<.5 ? 1. : 0.);
        if (!Forge->BeginStrike(Index,0,0,Contact)) return false;
        const bool DidHit=Forge->Strike(Index,Contact,FVector2D(.02,.02));
        return DidHit==Hit && Forge->Job().bHammeredBlank && Forge->Job().Hits==(Hit?1:0);
    };
    Check(Strike(false),TEXT("manual off-target blank contact recorded without an accuracy hit"));
    Check(Forge->Finish(Why) && SmithStage()==Smith::EStage::Finish,TEXT("manual contact is enough to reach smith claim stage"),Why);
    Check(Forge->Discard(Why) && SmithStage()==Smith::EStage::Materials && Count(TEXT("ue_forged_steel_greatsword"))==0, TEXT("discarding finished hammer-work resets the lesson with no product"),Why);
    if (!Check(SmithStart(),TEXT("smith paid retry for final product"),Why)) return 1;
    Check(Strike(true) && Forge->Finish(Why) && SmithStage()==Smith::EStage::Finish, TEXT("accurate hammer contact and successful settlement"),Why);
    const auto ReadySmith=Model->Snapshot();
    Model->AuditFailNextSave=true;
    Check(!Forge->Claim(Why) && SmithStage()==Smith::EStage::Finish && !Forge->Job().Id.IsEmpty() && Count(TEXT("ue_forged_steel_greatsword"))==0,TEXT("smith claim save failure preserves job and inventory"),Why);
    Check(Forge->Claim(Why) && Count(TEXT("ue_forged_steel_greatsword"))==1 && SmithStage()==Smith::EStage::Complete && Forge->Job().Id.IsEmpty(),TEXT("smith claim atomically delivers exactly one forged steel greatsword and completes"),Why);
    Check(!Forge->Claim(Why) && Model->ReloadProfile() && Count(TEXT("ue_forged_steel_greatsword"))==1 && SmithStage()==Smith::EStage::Complete, TEXT("smith duplicate claim rejected and completed product survives checked save reload"),Why);
    const auto WoodSeed=Model->Snapshot();
    auto WoodStart = [&]()
    {
        Shop->Close();
        Model->AdoptNetMirror(WoodSeed);
        return Shop->Open(false) && Shop->Select(TEXT("staff_core")) && Shop->Start(false) && !Shop->Job().PaidMaterials.IsEmpty() && WoodStage()==Wood::EStage::Working;
    };
    if (!Check(WoodStart(),TEXT("carpenter starts paid staff using ordinary wood core"),Shop->Message())) return 1;
    Check(!Shop->Claim(),TEXT("carpenter cannot claim before settling"));
    Check(Shop->Settle() && Shop->Job().bFinished && !Shop->Job().bPassed && WoodStage()==Wood::EStage::Materials,TEXT("uncut board fails real production scoring"),Shop->Message());
    Check(!Shop->Claim() && Count(TEXT("ue_apprentice_staff"))==0,TEXT("failed staff cannot be claimed"));
    Check(Shop->Discard() && Shop->Job().Id.IsEmpty() && WoodStage()==Wood::EStage::Materials,TEXT("discard of failed staff allows retry"),Shop->Message());
    auto CutStaff = [&]()
    {
        // Generate accurate saw sweeps outside the target polygon. Settlement, clearance,
        // integrity, connectivity and delivery still run through the real workstation.
        auto& Board=Shop->Board;
        const int32 Width=Shop->Settings().Width, Height=Shop->Settings().Height;
        const auto& Target=Board.Target();
        Board.BeginStroke();
        for (int32 Y=0;Y<Height;++Y)
        {
            for (int32 X=0;X<Width;)
            {
                if (Target[Y*Width+X]) {++X;continue;}
                const int32 Start=X;
                while (X<Width && !Target[Y*Width+X]) ++X;
                const FVector2D A(Start+.5,Y+.5), B(X-.5,Y+.5);
                Board.CutSawSweep(A,B,A,B,.51);
            }
        }
        Board.EndStroke();
        return Shop->Finish() && Shop->Job().bFinished && Shop->Job().bPassed && WoodStage()==Wood::EStage::Finish;
    };
    if (!Check(WoodStart() && CutStaff(),TEXT("target-guided mask saw cuts pass staff scoring and yield a pending result"),Shop->Message())) return 1;
    const auto ReadyWood=Model->Snapshot();
    Check(Shop->Discard() && WoodStage()==Wood::EStage::Materials && Count(TEXT("ue_apprentice_staff"))==0,TEXT("discard of qualified staff gives no completion or product"),Shop->Message());
    if (!Check(WoodStart() && CutStaff(),TEXT("carpenter can craft again after discarding the qualified staff"),Shop->Message())) return 1;
    Model->AuditFailNextSave=true;
    Check(!Shop->Claim() && !Shop->Job().Id.IsEmpty() && WoodStage()==Wood::EStage::Finish && Count(TEXT("ue_apprentice_staff"))==0,TEXT("carpenter claim save failure preserves the qualified workpiece"),Shop->Message());
    Check(Shop->Claim() && WoodStage()==Wood::EStage::Complete && Count(TEXT("ue_apprentice_staff"))==1 && Shop->Job().Id.IsEmpty(),TEXT("carpenter claim atomically delivers exactly one staff and completes"),Shop->Message());
    Check(!Shop->Claim() && Model->ReloadProfile() && Count(TEXT("ue_apprentice_staff"))==1 && Count(TEXT("ue_forged_steel_greatsword"))==1 && WoodStage()==Wood::EStage::Complete && SmithStage()==Smith::EStage::Complete,TEXT("duplicate staff claim rejected and both unique products and completions survive checked save reload"));
    for (bool BadRecipe : {false,true})
    {
        auto P=ReadySmith;
        if (BadRecipe) P.ForgeJob.Recipe=TEXT("forge_other"); else P.ForgeJob.Item.Definition=TEXT("ue_apprentice_staff");
        Smith::WorkpieceUpdated(P); Smith::WorkpieceRemoved(P,true);
        Check(Smith::Stage(P)==Smith::EStage::Materials,BadRecipe?TEXT("smith rejects different recipe with correct item"):TEXT("smith rejects correct recipe with wrong output"));
        auto Q=ReadyWood;
        if (BadRecipe) Q.WoodworkingJob.Recipe=TEXT("woodwork_bow"); else Q.WoodworkingJob.Item.Definition=TEXT("ue_tang_dao");
        Wood::WorkpieceUpdated(Q); Wood::WorkpieceRemoved(Q,true);
        Check(Wood::Stage(Q)==Wood::EStage::Materials,BadRecipe?TEXT("carpenter rejects different recipe with correct item"):TEXT("carpenter rejects correct recipe with wrong output"));
    }
    auto Legacy=ReadySmith;
    Legacy.ForgeJob.bHammeredBlank=false; Legacy.ForgeJob.Hits=1;
    Legacy.WoodworkingJob=ReadyWood.WoodworkingJob;
    Legacy.BlacksmithApprenticeshipStage=1; Legacy.CarpenterApprenticeshipStage=2;
    Legacy.CampfireWorldReceipts.Reset();
    auto* LegacySave=NewObject<UColdSteelProfileSave>(); LegacySave->Profile=Legacy;
    const FString LegacySlot=TEXT("LessonBranchAudit_LegacyFixture");
    if (!Check(UGameplayStatics::SaveGameToSlot(LegacySave,LegacySlot,0),TEXT("write tagged legacy-state fixture to isolated physical slot"))) return 1;
    auto* Loaded=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(LegacySlot,0));
    if (!Check(Loaded!=nullptr,TEXT("load tagged legacy-state fixture from physical slot"))) return 1;
    auto P=Loaded->Profile;
    Smith::NormalizeImportedProfile(P); Wood::NormalizeImportedProfile(P);
    Check(P.BlacksmithApprenticeshipStage==uint8(Smith::EStage::Finish) && !Smith::NeedsSupplies(P),TEXT("legacy accurate hit with no contact field or material receipt restores claim stage"));
    Check(P.CarpenterApprenticeshipStage==uint8(Wood::EStage::Finish) && Wood::NeedsSupplies(P),TEXT("legacy qualified staff with old stage and no receipt restores claim stage"));
    P.ForgeJob={};P.WoodworkingJob={};
    Smith::NormalizeImportedProfile(P);Wood::NormalizeImportedProfile(P);
    Check(Smith::Stage(P)==Smith::EStage::Smelting && Wood::Stage(P)==Wood::EStage::Materials,TEXT("two abandoned legacy jobs return to material collection"));
    auto Orphan=Accepted;Orphan.BlacksmithApprenticeshipStage=0;Orphan.CarpenterApprenticeshipStage=0;
    Smith::NormalizeImportedProfile(Orphan);Wood::NormalizeImportedProfile(Orphan);
    Check(Smith::Stage(Orphan)==Smith::EStage::Smelting && Wood::Stage(Orphan)==Wood::EStage::Materials && !Smith::NeedsSupplies(Orphan) && !Wood::NeedsSupplies(Orphan),TEXT("material receipts recover both missing stages without granting new packs"));
    auto Sword=Model->CreateItem(TEXT("ue_forged_steel_greatsword"));
    TSharedPtr<FJsonObject> SwordData;
    if(!Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Sword.Data),SwordData)&&SwordData.IsValid(),TEXT("guard fixture uses the shipped sword definition")))return 1;
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("guard"),TEXT("raven_quill_guard"));SwordData->SetObjectField(TEXT("gunsmith_parts"),Parts);
    Sword.Data.Reset();FJsonSerializer::Serialize(SwordData.ToSharedRef(),TJsonWriterFactory<>::Create(&Sword.Data));
    auto* Raven=Pawn->FindComponentByClass<URavenQuillChargeComponent>();
    const auto* ChargeField=FindFProperty<FStructProperty>(URavenQuillChargeComponent::StaticClass(),TEXT("Charge"));
    if(!Check(Raven&&ChargeField,TEXT("raven component and replicated charge state exist")))return 1;
    Raven->Equip(&Sword);
    auto* Charge=ChargeField->ContainerPtrToValuePtr<FRavenQuillCharge>(Raven);
    const auto* Sprint=FindFProperty<FBoolProperty>(AFPSGAMECharacter::StaticClass(),TEXT("bIsSprinting"));
    if(!Check(Sprint!=nullptr,TEXT("sprint fixture can drive the pawn intent")))return 1;
    Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    Pawn->GetCharacterMovement()->Velocity={400,0,0};
    World->TimeSeconds=10.;
    Sprint->SetPropertyValue_InContainer(Pawn,true);
    Raven->TickComponent(0.f,LEVELTICK_All,nullptr);
    World->TimeSeconds=11.;
    Sprint->SetPropertyValue_InContainer(Pawn,false);
    Raven->TickComponent(0.f,LEVELTICK_All,nullptr);
    Check(FMath::IsNearlyEqual(Charge->BankedSeconds,1.f),TEXT("one second of running banks one second when stopping"));
    World->TimeSeconds=14.;
    Sprint->SetPropertyValue_InContainer(Pawn,true);Raven->TickComponent(0.f,LEVELTICK_All,nullptr);
    World->TimeSeconds=15.9;Raven->TickComponent(0.f,LEVELTICK_All,nullptr);
    Check(Charge->ReadyUntil<0.,TEXT("pause time does not fill raven charge"));
    World->TimeSeconds=16.;Raven->TickComponent(0.f,LEVELTICK_All,nullptr);
    Check(FMath::IsNearlyEqual(Charge->ReadyUntil,21.),TEXT("three cumulative moving seconds open a five second hit window"));
    Sprint->SetPropertyValue_InContainer(Pawn,false);

    FColdSteelNetHitReport NetHit;
    NetHit.ItemDefinition=Sword.Definition;NetHit.AttackMeta=0x20;NetHit.WhirlwindSerial=19;
    FColdSteelSkillShot Shot;Shot.bMelee=true;Shot.ItemDefinition=Sword.Definition;Shot.ItemInstance=Sword.InstanceId;
    Shot.ForgedGuardAttackKey=UEagleTalonGuardComponent::ReportAttackKey(NetHit);
    Check(Raven->ContactBonus(Shot)==25.f,TEXT("first accepted whirlwind target consumes raven charge"));
    auto Later=Shot;Later.ForgedGuardAttackKey=UEagleTalonGuardComponent::AttackKey(EEagleStrike::Quick,19);
    Check(Raven->ContactBonus(Later)==0.f,TEXT("overlapping skill serials from distinct channels cannot share a bonus"));
    ++Shot.MasteryAttackSerial;
    Check(Raven->ContactBonus(Shot)==25.f,TEXT("second target on the original cast keeps the bonus after interleaved contact"));
    Raven->Equip(nullptr);Raven->Equip(&Sword);
    Charge->ReadyUntil=World->GetTimeSeconds();
    Check(Raven->ContactBonus(Shot)==0.f,TEXT("unequip cancels attack receipts and an expired ready window grants no bonus"));
    auto Reset=ReadySmith;
    Check(Smith::Reset(Reset)&&Smith::Stage(Reset)==Smith::EStage::NotStarted&&!Reset.ForgeJob.Id.IsEmpty(),TEXT("F6 reset leaves the paid blade collectible"));
    Check(!Smith::Reset(Reset),TEXT("duplicate F6 reset has no effect"));
    auto* Shared=World->GetSubsystem<UColdSteelSharedInventorySubsystem>();
    if(!Check(Shared!=nullptr,TEXT("world has a harvest mirror")))return 1;
    auto* RockOwner=World->SpawnActor<AActor>();
    auto* Rocks=NewObject<UInstancedStaticMeshComponent>(RockOwner);
    auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    Rocks->SetStaticMesh(Cube);RockOwner->SetRootComponent(Rocks);Rocks->RegisterComponent();
    for(int32 X:{255,900,1500})Rocks->AddInstance(FTransform(FVector(X,0,0)));
    TArray<FColdSteelHarvestRemoval> Removed;
    for(int32 X:{256,900})
    {
        auto& R=Removed.AddDefaulted_GetRef();R.Layer=1;R.Id=FString::FromInt(X);R.Mesh=FSoftObjectPath(Cube);R.Location={double(X),0.,300.};
    }
    auto StateBeforeMirror=Model->Snapshot();
    Shared->ApplyHarvestMirror(StateBeforeMirror,Removed);
    FTransform Remaining;
    Check(Rocks->GetInstanceCount()==1&&Rocks->GetInstanceTransform(0,Remaining,true)&&Remaining.GetLocation().X==1500.,
        TEXT("streamed rocks batch removal respects the 2 cm XY tolerance including a grid boundary"));
    Shared->ApplyHarvestMirror(StateBeforeMirror,Removed);
    Check(Rocks->GetInstanceCount()==1,TEXT("replayed harvest snapshot does not remove more rocks"));
    Model->AdoptNetMirror(StateBeforeMirror);
    Report+=FString::Printf(TEXT("checks=%d passed=%d failed=%d\n"),Pass+Fail,Pass,Fail);
    FFileHelper::SaveStringToFile(Report,*ReportPath,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    return Fail ? 1 : 0;
}
