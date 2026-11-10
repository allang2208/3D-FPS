#include "EnhancementEscrowAuditCommandlet.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelProfileTransfer.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonSerializer.h"

void UEnhancementEscrowAuditCommandlet::Run(UColdSteelStatusModel* M,bool LoadOnly,TFunctionRef<void(bool,const TCHAR*)> Check)
{
    auto* E=M?M->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
    Check(M&&M->IsAudit()&&E,TEXT("isolated audit profile and enhancement catalog"));if(!M||!M->IsAudit()||!E)return;
    ColdSteelAuthority::FScope Context(M);
    const FString Id=TEXT("enhancement-escrow-audit-m1911"),OtherId=TEXT("enhancement-escrow-audit-m4");
    const auto Stored=[&](){return M->EnhancementItem().InstanceId==Id&&!M->FindItem(Id)&&M->EnhancementItem().bRotated
        &&M->EnhancementItem().Width==2&&M->EnhancementItem().Height==3&&M->EnhancementItem().Magazine==5;};
    if(LoadOnly)
    {
        Check(Stored(),TEXT("fresh process restores exactly one rotated escrow pistol and its ammunition"));
        Check(ColdSteelInventory::Number(M->EnhancementItem(),TEXT("enhanceLevel"))==1,TEXT("fresh process restores paid enhancement"));return;
    }
    FString Message;
    auto Seed=M->Snapshot();Seed.Items.Reset();Seed.EnhancementItem={};Seed.ForgeJob={};Seed.GunAssemblyJob={};Seed.WoodworkingJob={};Seed.AlchemyJob={};
    Seed.QuickBindings.Init(FColdSteelQuickBinding(),ColdSteelQuickBar::Count);Seed.QuickBarVersion=ColdSteelQuickBar::Version;Seed.Hotbar.Init(TEXT(""),4);Seed.HotbarDefinitions.Init(TEXT(""),4);Seed.ActiveProductionTool.Reset();Seed.Souls=100000;
    auto Gun=M->CreateItem(TEXT("ue_m1911"));Gun.InstanceId=Id;Gun.Magazine=5;ColdSteelInventory::ApplyOrientation(Gun,1);
    auto Other=M->CreateItem(TEXT("ue_m4a1"));Other.InstanceId=OtherId;
    bool Fits=ColdSteelInventory::Insert(Seed.Items,Gun)&&ColdSteelInventory::Insert(Seed.Items,Other)
        &&ColdSteelInventory::Insert(Seed.Items,M->CreateItem(TEXT("enhancement_stone"),10));
    FString SeedReason; const bool SeedValid=ColdSteelInventory::Validate(Seed,SeedReason); const bool SeedSaved=Fits&&M->CommitState(Seed);
    UE_LOG(LogTemp,Display,TEXT("ENHANCEMENT_ESCROW_SEED fits=%d valid=%d reason=%s saved=%d message=%s"),Fits,SeedValid,*SeedReason,SeedSaved,*M->ResultMessage());
    for(const auto& V:Seed.Items)UE_LOG(LogTemp,Display,TEXT("ENHANCEMENT_ESCROW_SEED_ITEM %s %dx%d cell=%d rotated=%d"),*V.Definition,V.Width,V.Height,V.Cell,V.bRotated);
    Check(SeedSaved,TEXT("seed uses official inventory placement and isolated save"));if(!SeedSaved)return;
    Check(!E->Quote(Id).Valid,TEXT("inventory item cannot be processed before escrow transfer"));
    Check(E->TransferAuthority(Id,FString(),Message)&&Stored(),TEXT("place removes inventory copy and retains rotated footprint and ammunition"));
    const auto Placed=M->Snapshot();
    Check(!E->TransferAuthority(OtherId,FString(),Message)&&M->Snapshot().Generation==Placed.Generation&&Stored(),TEXT("stale expected escrow cannot replace or change generation"));
    const auto Q=E->Quote(Id);const int64 Souls=M->Snapshot().Souls,Stones=M->CountMaterial(TEXT("enhancement_stone"));
    int64 SoulCost=0,StoneCost=0;for(const auto& C:Q.Costs)if(C.Definition==TEXT("enhancement_stone"))StoneCost=C.Need;else SoulCost=C.Need;
    Check(Q.Valid&&M->Snapshot().Generation==Placed.Generation,TEXT("escrow quote is valid and read-only"));
    Check(E->ApplyAuthority(Q,Message)&&Stored()&&ColdSteelInventory::Number(M->EnhancementItem(),TEXT("enhanceLevel"))==1
        &&M->Snapshot().Souls==Souls-SoulCost&&M->CountMaterial(TEXT("enhancement_stone"))==Stones-StoneCost,TEXT("processing modifies escrow and debits exact costs once"));
    const auto Paid=M->Snapshot();
    Check(!E->ApplyAuthority(Q,Message)&&M->Snapshot().Generation==Paid.Generation,TEXT("repeated quote cannot charge twice"));
    M->AuditFailNextSave=true;const auto NextQuote=E->Quote(Id);
    Check(!E->ApplyAuthority(NextQuote,Message)&&M->Snapshot().Generation==Paid.Generation&&M->EnhancementItem().Data==Paid.EnhancementItem.Data
        &&M->Snapshot().Souls==Paid.Souls&&M->CountMaterial(TEXT("enhancement_stone"))==Stones-StoneCost,TEXT("failed processing save rolls back escrow and all costs"));
    M->AuditFailNextSave=true;
    Check(!E->TransferAuthority(OtherId,Id,Message)&&Stored()&&M->FindItem(OtherId)&&M->Snapshot().Generation==Paid.Generation,TEXT("failed replacement save retains both identities at original locations"));
    Check(E->TransferAuthority(OtherId,Id,Message)&&M->FindItem(Id)&&!M->FindItem(OtherId)&&M->EnhancementItem().InstanceId==OtherId,TEXT("replace returns old escrow and removes new inventory copy atomically"));
    Check(E->TransferAuthority(FString(),OtherId,Message)&&M->EnhancementItem().InstanceId.IsEmpty()&&M->FindItem(Id)&&M->FindItem(OtherId),TEXT("retrieve restores one inventory copy and clears escrow"));
    Check(!E->TransferAuthority(FString(),OtherId,Message),TEXT("repeated retrieve rejects without duplication"));
    Check(E->TransferAuthority(Id,FString(),Message)&&Stored(),TEXT("processed rotated pistol can return to escrow"));
    auto WithSpace=M->Snapshot();auto Full=WithSpace;Full.Items.Reset();
    // Single-cell, unstacked material identities fill every actual backpack cell.
    const int32 Cells=ColdSteelInventory::BagRows(Full.Items)*18;
    for(int32 Cell=0;Cell<Cells;++Cell){auto Filler=M->CreateItem(TEXT("enhancement_stone"),1);Filler.InstanceId=FString::Printf(TEXT("escrow-full-%d"),Cell);Filler.Place=0;Filler.Cell=Cell;Full.Items.Add(Filler);}
    auto Equipped=Other;Equipped.Place=1;Equipped.Cell=6;Full.Items.Add(Equipped);
    Check(M->CommitState(Full),TEXT("full-backpack fixture validates and saves"));const auto Blocked=M->Snapshot();
    Check(!E->TransferAuthority(FString(),Id,Message)&&Stored()&&M->Snapshot().Generation==Blocked.Generation,TEXT("full backpack keeps escrow and generation unchanged"));
    Check(!E->TransferAuthority(OtherId,Id,Message)&&Stored()&&M->FindItem(OtherId)&&M->FindItem(OtherId)->Place==1&&M->Snapshot().Generation==Blocked.Generation,TEXT("full backpack rejects replacement atomically and leaves incoming weapon equipped"));
    Check(M->CommitState(WithSpace),TEXT("restore free-space fixture"));
    auto* Save=NewObject<UColdSteelProfileSave>();Save->Profile=M->Snapshot();TArray<uint8> Blob;
    auto* Restored=ColdSteelProfileTransfer::SaveToBlob(Save,Blob)?ColdSteelProfileTransfer::BlobToSave(Blob):nullptr;
    Check(Restored&&FColdSteelItem::StaticStruct()->CompareScriptStruct(&Restored->Profile.EnhancementItem,&Save->Profile.EnhancementItem,0),TEXT("network envelope round trip preserves complete escrow state"));
    if(Restored)
    {
        auto* PS=M->GetWorld()->SpawnActor<AColdSteelPlayerState>();
        auto Upload=Restored->Profile;auto Duplicate=Upload.EnhancementItem;Duplicate.Cell=0;Upload.Items.Add(Duplicate);
        Check(PS&&PS->SanitizeGuestProfile(Upload,Message)&&Upload.EnhancementItem.Width==2&&Upload.EnhancementItem.Height==3
            &&ColdSteelInventory::BaseFootprint(Upload.EnhancementItem)==FIntPoint(3,2)
            &&!Upload.Items.ContainsByPredicate([&](const auto& I){return I.InstanceId==Id;}),TEXT("new host sanitizes rotated escrow without 3x3 expansion or duplicate inventory copy"));
        if(PS)
        {
            PS->ShadowModel=M->CreateShadowModel(Upload);
            Check(PS->ShadowModel!=nullptr,TEXT("sanitized upload creates guest shadow"));
            if(PS->ShadowModel)
            {
                auto Heartbeat=WithSpace;Heartbeat.EnhancementItem={};
                Check(PS->SanitizeGuestProfile(Heartbeat,Message)&&Heartbeat.EnhancementItem.InstanceId==Id,TEXT("stale whole-profile upload cannot erase existing authority escrow"));
                auto* Pawn=M->GetWorld()->SpawnActor<AFPSGAMECharacter>();
                if(Pawn)
                {
                    Pawn->NetShadowProfile=PS->ShadowModel;PS->ShadowModel->AttachPawn(Pawn);
                    const auto HostBefore=M->Snapshot();
                    {
                        ColdSteelAuthority::FScope Guest(PS->ShadowModel);
                        Check(E->TransferAuthority(FString(),Id,Message)&&PS->ShadowModel->FindItem(Id)&&PS->ShadowModel->EnhancementItem().InstanceId.IsEmpty(),TEXT("guest authority retrieves only its own escrow"));
                    }
                    Check(M->Snapshot().Generation==HostBefore.Generation&&Stored(),TEXT("guest transaction leaves host inventory and escrow untouched"));
                    Pawn->NetShadowProfile=nullptr;Pawn->Destroy();
                }
                else Check(false,TEXT("guest authority pawn exists"));
                PS->ShadowModel=nullptr;
            }
            PS->Destroy();
        }
    }
    // Both orientations and repeated sanitization are necessary: the old code
    // passed all unrotated cases and only grew dimensions on a rotated upload.
    for(const TCHAR* Def:{TEXT("ue_m1911"),TEXT("ue_m4a1"),TEXT("ue_kukri"),TEXT("ue_tactical_hatchet")})for(int32 Rotation=0;Rotation<2;++Rotation)
    {
        auto Item=M->CreateItem(Def);ColdSteelInventory::ApplyOrientation(Item,Rotation);const int32 W=Item.Width,H=Item.Height;
        Check(M->SanitizeNetworkItem(Item)&&Item.Width==W&&Item.Height==H&&M->SanitizeNetworkItem(Item)&&Item.Width==W&&Item.Height==H,TEXT("catalog footprint sanitizer is orientation-correct and idempotent"));
    }
    Check(M->ReloadProfile()&&Stored()&&ColdSteelInventory::Number(M->EnhancementItem(),TEXT("enhanceLevel"))==1,TEXT("disk reload restores committed escrow after failed saves and guest operations"));
}

int32 UEnhancementEscrowAuditCommandlet::Main(const FString& Params)
{
    const FString Original=FCommandLine::Get();FString Slot;
    if(!FParse::Value(*Params,TEXT("Profile="),Slot))Slot=TEXT("EnhancementEscrowAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    if(!Slot.StartsWith(TEXT("EnhancementEscrowAudit_")))return 2;
    FCommandLine::Set(*(TEXT("EnhancementEscrowAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("EnhancementEscrowAuditWorld"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    ON_SCOPE_EXIT {GI->Shutdown();if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}GI->RemoveFromRoot();FCommandLine::Set(*Original);};
    if(!World||!Model||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    Run(Model,FParse::Param(*Params,TEXT("LoadOnly")),[&](bool Passed,const TCHAR* Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),Passed);Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!Passed;
        UE_LOG(LogTemp,Display,TEXT("ENHANCEMENT_ESCROW %s %s"),Passed?TEXT("PASS"):TEXT("FAIL"),Name);
    });
    FString Output;if(!FParse::Value(*Params,TEXT("Output="),Output))return 3;
    auto Result=MakeShared<FJsonObject>();Result->SetArrayField(TEXT("checks"),Rows);Result->SetNumberField(TEXT("failures"),Failures);
    Result->SetStringField(TEXT("profile"),Slot);Result->SetBoolField(TEXT("udp_or_multiplayer_runtime"),false);Result->SetBoolField(TEXT("visuals_tested"),false);
    FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    return FFileHelper::SaveStringToFile(Json,*Output)?(Failures?1:0):3;
}
