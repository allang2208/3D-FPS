#include "ColdSteelIncineratorAuditCommandlet.h"
#include "ColdSteelIncineration.h"
#include "ColdSteelIncineratorStorage.h"
#include "../Building/VoxelBuildPersistence.h"
#include "../Building/VoxelBuildWorld.h"
#include "ColdSteelStatusModel.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

int32 UColdSteelIncineratorAuditCommandlet::Main(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    FString Root;FParse::Value(*Original,TEXT("IncineratorAuditRoot="),Root);
    if(Root.IsEmpty())return 2;
    Root=FPaths::ConvertRelativePathToFull(Root);FPaths::NormalizeDirectoryName(Root);
    FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());FPaths::NormalizeDirectoryName(Saved);
    if(!Saved.StartsWith(Root+TEXT("/"))){UE_LOG(LogTemp,Error,TEXT("INCINERATOR_TEST ABORT: Saved directory is not isolated"));return 2;}
    const FString Name=TEXT("IncineratorAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("IncineratorAudit -ColdSteelProfile=")+Name+TEXT(" -UserDir=\"")+FPaths::ProjectUserDir()+TEXT("\"")));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("IncineratorAuditWorld"));
    auto* M=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!M||!M->IsAudit()||M->ProfileSlot()!=TEXT("ColdSteel_")+Name)return 2;
    FString Report=TEXT("PROFILE ")+M->ProfileSlot()+TEXT("\n");int32 Checks=0,Failed=0;
    auto Check=[&](bool OK,const FString& Label){++Checks;if(!OK)++Failed;const FString Line=(OK?TEXT("PASS "):TEXT("FAIL "))+Label;Report+=Line+TEXT("\n");UE_LOG(LogTemp,Display,TEXT("INCINERATOR_TEST %s"),*Line);return OK;};
    auto Blank=M->Snapshot();Blank.Items.Reset();Blank.AmmoPouch.Reset();Blank.Hotbar.Init(TEXT(""),4);Blank.HotbarDefinitions.Init(TEXT(""),4);
    for(auto& B:Blank.QuickBindings)B=FColdSteelQuickBinding();Blank.ActiveProductionTool.Reset();Blank.ForgeJob=FColdSteelForgeJob();Blank.GunAssemblyJob=FColdSteelGunAssemblyJob();
    auto Seed=[&](TArray<FColdSteelItem> Items){auto State=Blank;State.Items=MoveTemp(Items);return Check(M->CommitState(State),TEXT("isolated fixture save: ")+M->ResultMessage());};
    using namespace ColdSteelIncineratorStorage;
    const FString Box=TEXT("incinerator.audit.first"),OtherBox=TEXT("incinerator.audit.second");
    const auto EmptyRules=ParseRules(TEXT("{\"version\":1,\"allowUnconfiguredDestruction\":true,\"recipes\":[]}"));
    const auto Production=LoadRules();
    Check(Production.bValid&&Production.Recipes.IsEmpty(),TEXT("GRID production rules are empty; no invented rewards"));
    Blank.StoragePages.Add(Box,1);Blank.StoragePages.Add(OtherBox,1);
    auto Open=[&](){M->bIncineratorOpen=true;M->BeginStorageSession(Box,1,TEXT("焚化投入"));};
    auto Potion=M->CreateItem(TEXT("hp_potion"),9);Potion.Cell=0;
    FString Why;FSession Session;
    Check(Seed({Potion}),TEXT("GRID ordinary stack fixture"));Open();
    Check(M->DefaultAction(Potion.InstanceId)&&M->FindItem(Potion.InstanceId)->Place==4&&M->FindItem(Potion.InstanceId)->Count==9,TEXT("GRID default action deposits consumable intact"));
    Check(M->FindItem(Potion.InstanceId)->Container==Box&&M->CountMaterial(Potion.Definition)==0,TEXT("GRID escrow has single ownership and is excluded from crafting"));
    Check(M->Split(Potion.InstanceId,4),TEXT("GRID existing split operates in input container"));
    Check(M->Items().Num()==2&&M->FindItem(Potion.InstanceId)->Count==5,TEXT("GRID split conserves total and distinct identity"));
    Check(M->DefaultAction(Potion.InstanceId)&&M->FindItem(Potion.InstanceId)->Place==0,TEXT("GRID right-action withdraws to backpack"));
    Check(M->TransferWarehouse(Potion.InstanceId,4),TEXT("GRID automatic deposit merges compatible input stacks"));
    Check(M->Items().Num()==1&&M->Items()[0].Count==9,TEXT("GRID merging conserves exact stack count"));
    const FString Merged=M->Items()[0].InstanceId;
    M->bIncineratorOpen=false;M->EndStorageSession();
    Check(M->FindItem(Merged)&&M->FindItem(Merged)->Container==Box,TEXT("GRID closing keeps persisted input"));
    Check(M->ReloadProfile()&&M->FindItem(Merged)&&M->FindItem(Merged)->Count==9,TEXT("GRID input survives real isolated profile reload"));Open();
    Check(M->FindItem(Merged)->Container==Box,TEXT("GRID reopen resolves same container"));
    const auto Before=M->Snapshot();auto Q=Quote(Before,Box,EmptyRules);
    Check(Q.bValid&&Q.Products.IsEmpty()&&Q.Unconfigured.Num()==1,TEXT("GRID empty rules distinguish unconfigured from known zero yield"));
    Check(Describe(Q,*M,true).Contains(TEXT("本次不获得物品")),TEXT("GRID confirmation explicitly says no items received"));
    Check(M->Snapshot().Generation==Before.Generation&&M->FindItem(Merged)->Count==9,TEXT("GRID preview never saves or consumes"));
    Check(Session.Review(*M,Box,EmptyRules),TEXT("GRID review all actual input contents"));Session.Cancel();
    Check(!Session.Confirm(*M,EmptyRules,Why)&&M->FindItem(Merged),TEXT("GRID cancelled confirmation cannot consume"));
    Check(Session.Review(*M,Box,EmptyRules),TEXT("GRID prepare failure confirmation"));M->AuditFailNextSave=true;
    Check(!Session.Confirm(*M,EmptyRules,Why)&&M->FindItem(Merged)&&M->Snapshot().Generation==Before.Generation,TEXT("GRID failed save leaves full input intact"));
    Check(!Session.Confirm(*M,EmptyRules,Why),TEXT("GRID failed commit consumes confirmation token"));
    Check(Session.Review(*M,Box,EmptyRules),TEXT("GRID stale generation review"));M->CommitState(M->Snapshot());
    Check(!Session.Confirm(*M,EmptyRules,Why)&&M->FindItem(Merged),TEXT("GRID stale generation aborts entire transaction"));
    Check(Session.Review(*M,Box,EmptyRules),TEXT("GRID same-generation payload review"));auto Changed=M->Snapshot();Changed.Items[0].Data+=TEXT(" ");M->AdoptNetMirror(Changed);
    Check(!Session.Confirm(*M,EmptyRules,Why),TEXT("GRID changed instance payload aborts without relying on generation"));
    Check(Session.Review(*M,Box,EmptyRules),TEXT("GRID rule change review"));auto ChangedRules=EmptyRules;ChangedRules.Signature=TEXT("changed");
    Check(!Session.Confirm(*M,ChangedRules,Why)&&M->FindItem(Merged),TEXT("GRID changed rules require fresh confirmation"));
    Check(Session.Review(*M,Box,EmptyRules),TEXT("GRID close invalidation review"));M->bIncineratorOpen=false;M->EndStorageSession();
    Check(!Session.Confirm(*M,EmptyRules,Why)&&M->FindItem(Merged),TEXT("GRID closed session cannot confirm old contents"));Open();
    Check(Session.Review(*M,Box,EmptyRules),TEXT("GRID no-output burn review"));const int64 G=M->Snapshot().Generation;
    Check(Session.Confirm(*M,EmptyRules,Why)&&!HasInputs(M->Snapshot(),Box)&&M->Snapshot().Generation==G+1,TEXT("GRID no-output burn consumes exactly one saved generation"));
    Check(!Session.Confirm(*M,EmptyRules,Why)&&M->Items().IsEmpty(),TEXT("GRID duplicate confirmation has no effect"));
    Check(M->ReloadProfile()&&!HasInputs(M->Snapshot(),Box),TEXT("GRID burned input stays removed after reload"));Open();
    auto Gun=M->CreateItem(TEXT("ue_m4a1"));Gun.Cell=0;Gun.Magazine=17;Gun.VirtualMagazineAmmo=0;
    Check(Seed({Gun}),TEXT("GRID unique loaded weapon fixture"));Open();
    Check(M->MoveItem(Gun.InstanceId,4,18,1),TEXT("GRID weapon rotates while entering real storage grid"));
    Check(M->FindItem(Gun.InstanceId)->Width==Gun.Height&&M->FindItem(Gun.InstanceId)->Height==Gun.Width,TEXT("GRID actual rotated footprint stored"));
    Check(M->MoveItem(Gun.InstanceId,0,0,0),TEXT("GRID weapon returns with explicit orientation"));
    const auto* Returned=M->FindItem(Gun.InstanceId);
    Check(Returned&&Returned->Data==Gun.Data&&Returned->Magazine==17&&Returned->InstanceId==Gun.InstanceId,TEXT("GRID unique payload and loaded rounds survive round trip"));
    Check(M->TransferWarehouse(Gun.InstanceId,4),TEXT("GRID retrieve failure fixture deposit"));
    auto Full=M->Snapshot();for(int32 Cell=0;Cell<72;++Cell){auto Fill=M->CreateItem(TEXT("hp_potion"),Potion.StackMax);Fill.Cell=Cell;Full.Items.Add(Fill);}
    Check(M->CommitState(Full),TEXT("GRID fill backpack without touching escrow"));const auto FullGeneration=M->Snapshot().Generation;
    Check(!Retrieve(*M,Box,Why)&&M->FindItem(Gun.InstanceId)->Container==Box&&M->Snapshot().Generation==FullGeneration,TEXT("GRID full backpack retains entire blocked input"));
    auto Bag=M->CreateItem(TEXT("ue_portable_backpack"));Bag.Place=1;Bag.Cell=14;auto Nested=Potion;Nested.Place=5;Nested.Cell=0;
    Check(Seed({Bag,Nested}),TEXT("GRID occupied backpack fixture"));Open();
    Check(!M->TransferWarehouse(Bag.InstanceId,4)&&M->FindItem(Bag.InstanceId)->Place==1,TEXT("GRID occupied bag cannot orphan compartment contents"));
    const FString Ammo=M->AmmoCatalog()[0].Id;
    auto AmmoState=Blank;AmmoState.AmmoPouch.Add(Ammo,100);Check(M->CommitState(AmmoState),TEXT("GRID pouch fixture"));Open();
    Check(DepositAmmo(*M,Ammo,37,Why),TEXT("GRID pouch deposit atomic"));
    Check(M->PouchCount(Ammo)==63&&M->Items().Num()==1&&M->Items()[0].bIncineratorAmmo&&M->Items()[0].Count==37,TEXT("GRID dedicated escrow is not normalized back into pouch"));
    FString AmmoId=M->Items()[0].InstanceId;
    Check(M->ReloadProfile()&&M->PouchCount(Ammo)==63&&M->FindItem(AmmoId)->Count==37,TEXT("GRID escrow and pouch survive reload without duplication"));Open();
    Check(M->Split(AmmoId,12),TEXT("GRID escrow split preserves dedicated type"));
    int64 Escrow=0;for(const auto& I:M->Items())if(I.bIncineratorAmmo)Escrow+=I.Count;
    Check(Escrow==37&&M->PouchCount(Ammo)==63,TEXT("GRID escrow splitting conserves owned ammunition"));
    Check(M->DefaultAction(AmmoId)&&M->PouchCount(Ammo)==88,TEXT("GRID escrow right-action returns exact rounds to pouch"));
    Check(Retrieve(*M,Box,Why)&&M->PouchCount(Ammo)==100&&!HasInputs(M->Snapshot(),Box),TEXT("GRID retrieve all returns remaining escrow atomically"));
    M->AuditFailNextSave=true;Check(!DepositAmmo(*M,Ammo,20,Why)&&M->PouchCount(Ammo)==100&&M->Items().IsEmpty(),TEXT("GRID pouch deposit save failure conserves rounds"));
    Check(!DepositAmmo(*M,Ammo,101,Why)&&M->PouchCount(Ammo)==100,TEXT("GRID excess pouch deposit rejected"));
    Check(DepositAmmo(*M,Ammo,10,Why),TEXT("GRID escrow capacity fixture"));AmmoId=M->Items()[0].InstanceId;
    auto MaxAmmo=M->Snapshot();MaxAmmo.AmmoPouch[Ammo]=9007199254740991ll;Check(M->CommitState(MaxAmmo),TEXT("GRID fill pouch to exact supported maximum"));
    Check(!M->DefaultAction(AmmoId)&&M->FindItem(AmmoId)->Count==10,TEXT("GRID full pouch leaves escrow unchanged"));
    // Test-only recipes below never touch Content/ColdSteelData or production rule objects.
    const auto TestRules=ParseRules(TEXT("{\"version\":1,\"allowUnconfiguredDestruction\":false,\"recipes\":[{\"input\":\"hp_potion\",\"inputCount\":1,\"outputs\":[{\"item\":\"wood\",\"count\":2},{\"item\":\"wood\",\"count\":1}]}]}"));
    Potion.Place=4;Potion.Container=Box;Potion.Count=3;Potion.Cell=0;
    auto Second=Potion;Second.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);Second.Count=2;Second.Cell=1;
    Check(Seed({Potion,Second}),TEXT("GRID test-only output fixture"));Open();Q=Quote(M->Snapshot(),Box,TestRules);
    Check(Q.bValid&&Q.Products.Num()==1&&Q.Products[0].Count==15,TEXT("GRID calculator merges input stacks and repeated output definitions"));
    const auto PreYield=M->Snapshot();FColdSteelProfile Proposed;
    Check(Prepare(*M,Q,TestRules,Proposed,Why)&&M->Snapshot().Generation==PreYield.Generation&&HasInputs(M->Snapshot(),Box),TEXT("GRID yield simulation stays read-only"));
    Check(Session.Review(*M,Box,TestRules),TEXT("GRID configured output review"));M->AuditFailNextSave=true;
    Check(!Session.Confirm(*M,TestRules,Why)&&M->CountMaterial(TEXT("wood"))==0&&HasInputs(M->Snapshot(),Box),TEXT("GRID output save failure creates no rewards or consumption"));
    const int64 YieldGen=M->Snapshot().Generation;
    Check(Session.Review(*M,Box,TestRules)&&Session.Confirm(*M,TestRules,Why)&&M->CountMaterial(TEXT("wood"))==15&&!HasInputs(M->Snapshot(),Box)&&M->Snapshot().Generation==YieldGen+1,TEXT("GRID configured consume and grant share one atomic commit"));
    Check(!Session.Confirm(*M,TestRules,Why)&&M->CountMaterial(TEXT("wood"))==15,TEXT("GRID reward cannot be claimed twice"));
    Check(Seed({Potion}),TEXT("GRID insufficient output capacity fixture"));Open();Full=M->Snapshot();for(int32 Cell=0;Cell<72;++Cell){auto Fill=M->CreateItem(TEXT("hp_potion"),Potion.StackMax);Fill.Cell=Cell;Full.Items.Add(Fill);}Check(M->CommitState(Full),TEXT("GRID output full backpack"));
    Check(Session.Review(*M,Box,TestRules)&&!Session.Confirm(*M,TestRules,Why)&&M->FindItem(Potion.InstanceId)->Container==Box,TEXT("GRID output capacity failure does not burn any input"));
    auto NoPermission=EmptyRules;NoPermission.bAllowUnconfigured=false;NoPermission.Signature=TEXT("deny");
    Check(!Quote(M->Snapshot(),Box,NoPermission).bValid,TEXT("GRID unconfigured destruction can be disabled explicitly"));
    for(const FString Bad:{TEXT("{}"),TEXT("{\"version\":2,\"allowUnconfiguredDestruction\":true,\"recipes\":[]}"),TEXT("{\"version\":1,\"allowUnconfiguredDestruction\":true,\"recipes\":[{\"input\":\"wood\",\"inputCount\":0,\"outputs\":[]}]}"),TEXT("{\"version\":1,\"allowUnconfiguredDestruction\":true,\"recipes\":[{\"input\":\"wood\",\"inputCount\":1,\"outputs\":[{\"item\":\"stone\",\"count\":1.5}]}]}")})
        Check(!ParseRules(Bad).bValid,TEXT("GRID malformed rules rejected"));
    Potion.Container=OtherBox;Check(Seed({Potion}),TEXT("GRID other or unloaded station recovery fixture"));M->bIncineratorOpen=false;M->EndStorageSession();
    Check(Retrieve(*M,FString(),Why)&&M->FindItem(Potion.InstanceId)->Place==0,TEXT("GRID owner can recover escrow without loaded station and without classifying it as destroyed"));
    // Exact v10 -> v11 disk roundtrip under redirected Saved; the original bytes are preserved.
    FVoxelDiskSnapshot Legacy;Legacy.Version=10;Legacy.WorldKey=TEXT("IncineratorAuditIdentityWorld");
    FVoxelBuildPrefabInstance Piece;Piece.Id=VoxelIncineratorId;Piece.Cell=FIntVector(3,4,0);Piece.Footprint=FIntVector(6,6,11);Legacy.Prefabs.Add(Piece);
    const FString Slot=TEXT("IncineratorAuditIdentity_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    Check(VoxelPersistence::Write(Slot,Legacy),TEXT("GRID write isolated legacy v10 building fixture"));
    VoxelPersistence::ELoadResult Result;auto* Loaded=VoxelPersistence::Load(Slot,Result);
    Check(Loaded&&Loaded->Version==10&&Loaded->Prefabs.Num()==1,TEXT("GRID legacy building file still loads"));
    if(Loaded&&Loaded->Prefabs.Num()==1)
    {
        const auto Identity=VoxelPersistence::StablePrefabId(Loaded->Prefabs[0],Loaded->WorldKey);
        Check(Identity.IsValid()&&Identity==VoxelPersistence::StablePrefabId(Piece,Legacy.WorldKey),TEXT("GRID old station identity is deterministic before first upgraded save"));
        Loaded->Prefabs[0].InstanceId=Identity;Loaded->Version=GVoxelBuildSaveVersion;
        TArray<uint8> BeforeBytes,BackupBytes;const FString File=Saved/TEXT("SaveGames")/(Slot+TEXT(".sav"));FFileHelper::LoadFileToArray(BeforeBytes,*File);
        Check(VoxelPersistence::Write(Slot,VoxelPersistence::Take(Loaded)),TEXT("GRID write migrated v11 isolated building"));
        auto* Reloaded=VoxelPersistence::Load(Slot,Result);
        Check(Reloaded&&Reloaded->Version==11&&Reloaded->Prefabs[0].InstanceId==Identity&&Reloaded->Prefabs[0].Cell==Piece.Cell,TEXT("GRID stable identity and legacy placement survive v11 roundtrip"));
        Check(FFileHelper::LoadFileToArray(BackupBytes,*(File+TEXT(".pre-incinerator-v11")))&&BeforeBytes==BackupBytes,TEXT("GRID migration retains byte-exact preceding old building save"));
        auto Replacement=Piece;Replacement.InstanceId=FGuid::NewGuid();Check(VoxelPersistence::StablePrefabId(Replacement,Legacy.WorldKey)!=Identity,TEXT("GRID same-position replacement cannot inherit old station identity"));
    }
    Check(ColdSteelInventory::Validate(M->Snapshot(),Why),TEXT("GRID final profile passes existing validator"));

    const FString Dir=Saved/TEXT("IncineratorAudit");IFileManager::Get().MakeDirectory(*Dir,true);
    Report+=FString::Printf(TEXT("RESULT checks=%d failures=%d\n"),Checks,Failed);
    FFileHelper::SaveStringToFile(Report,*(Dir/TEXT("transactions.txt")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    GI->Shutdown();GI->RemoveFromRoot();FCommandLine::Set(*Original);return Failed?1:0;
}
