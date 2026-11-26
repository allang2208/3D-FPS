#include "ColdSteelAcquisitionAuditCommandlet.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelAcquisitionTimeline.h"
#include "ColdSteelShopModel.h"
#include "ColdSteelUIStyle.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelProfileTransfer.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Building/ForgingSystem.h"
#include "Serialization/JsonSerializer.h"
#include "../FPSGAMECharacter.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"

int32 UColdSteelAcquisitionAuditCommandlet::Main(const FString& Params)
{
    FString Root;FParse::Value(*Params,TEXT("AcquisitionAuditRoot="),Root);
    Root=FPaths::ConvertRelativePathToFull(Root);FPaths::NormalizeDirectoryName(Root);
    FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());FPaths::NormalizeDirectoryName(Saved);
    if(Root.IsEmpty()||!Saved.StartsWith(Root+TEXT("/")))return 2;
    const FString Original=FCommandLine::Get(),Suffix=FGuid::NewGuid().ToString(EGuidFormats::Digits);
    const FString Profile=TEXT("AcquisitionAudit_")+Suffix;
    FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=")+Profile));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("AcquisitionAuditWorld"));
    auto* Client=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!Client||!Client->IsAudit()||Client->ProfileSlot()!=TEXT("ColdSteel_")+Profile)return 2;
    int32 Checks=0,Failures=0;FString Report;
    auto Check=[&](bool Pass,const FString& Label)
    {++Checks;if(!Pass)++Failures;const FString Line=(Pass?TEXT("PASS "):TEXT("FAIL "))+Label;Report+=Line+TEXT("\n");UE_LOG(LogTemp,Display,TEXT("ACQUISITION_AUDIT %s"),*Line);return Pass;};
    auto Blank=Client->Snapshot();Blank.Items.Reset();Blank.AmmoPouch.Reset();Blank.Souls=100000;
    Blank.ServerSoulCredits=Blank.ServerSoulDebits=0;Blank.CampfireInventoryRevision=0;Blank.CampfireWorldReceipts.Reset();
    Blank.Hotbar.Init(TEXT(""),4);Blank.HotbarDefinitions.Init(TEXT(""),4);
    for(auto& Binding:Blank.QuickBindings)Binding=FColdSteelQuickBinding();
    Blank.ActiveProductionTool.Reset();Blank.ForgeJob={};Blank.GunAssemblyJob={};Blank.WoodworkingJob={};
    Client->AdoptNetMirror(Blank);Client->bAudit=false;Client->SetAcquisitionFeedEnabled(true);
    auto HostBlank=Blank;HostBlank.NetworkProfileId=FGuid::NewGuid();
    auto* Host=Client->CreateShadowModel(HostBlank);
    Host->bNetShadowProfile=false;Host->bPersistenceBlocked=false;Host->SaveSlot=TEXT("ColdSteel_AcqHost_")+Suffix;
    Host->SetAcquisitionFeedEnabled(true);
    auto* World=GI->GetWorld();
    auto* Server=Client->CreateShadowModel(Blank);
    Server->CurrentPawn=World->SpawnActor<AFPSGAMECharacter>();
    Server->SetAcquisitionFeedEnabled(true); // even an accidental subscriber must not leak guest gains
    const FString GuestSlot=TEXT("ColdSteel_AcqGuest_")+Suffix;
    auto* Sender=World->SpawnActor<AColdSteelPlayerState>();
    auto* Receiver=World->SpawnActor<AColdSteelPlayerState>();
    auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();Receiver->SetOwner(PC);PC->SetPlayerState(Receiver);
    auto* ClientPawn=World->SpawnActor<AFPSGAMECharacter>();PC->Possess(ClientPawn);ClientPawn->SetPlayerState(Receiver);Client->CurrentPawn=ClientPawn;
    Check(Receiver->GetPawn()==ClientPawn&&Client->RuntimePawn()==ClientPawn,TEXT("mirror fixture binds the receiving player's current pawn"));
    auto Drain=[&](UColdSteelStatusModel* Model)
    {TMap<FString,int64> Counts;FColdSteelAcquisitionNotice N;while(Model->PopAcquisitionNotice(N))Counts.FindOrAdd(N.Key)+=N.Count;return Counts;};
    auto Exact=[&](UColdSteelStatusModel* Model,const FString& Definition,int64 Count,const FString& Label)
    {
        const auto Counts=Drain(Model);int64 Sum=0;for(const auto& P:Counts)if(P.Key.StartsWith(Definition+TEXT("|")))Sum+=P.Value;
        Check(Sum==Count&&Counts.Num()==(Count?1:0),Label+FString::Printf(TEXT(" expected=%lld actual=%lld rows=%d"),Count,Sum,Counts.Num()));
    };
    auto NoGain=[&](UColdSteelStatusModel* Model,const FString& Label){Check(Drain(Model).IsEmpty(),Label);};
    auto Pickup=[&](UColdSteelStatusModel* Model,const FString& Id,int64 Count,const FString& Slot)
    {
        auto Next=Model->Snapshot();const bool Added=Model->AmmoType(Id)?Model->AddAmmoToState(Next,Id,Count)
            :ColdSteelInventory::Insert(Next.Items,Model->CreateItem(Id,Count));
        // The same insert and confirmed-commit path used by shared world pickup.
        return Added&&Model->CommitCampfireState(MoveTemp(Next),TEXT("AcquisitionAuditWorld"),Slot);
    };
    FColdSteelInventoryRequest Request;Request.Action=EColdSteelInventoryAction::Shop;Request.Mode=TEXT("shop.buy");Request.Definition=TEXT("bread");Request.Count=2;
    FString Reason;
    Check(UColdSteelShopModel::ExecuteNetworkTrade(Host,Request,FString(),Reason),TEXT("host real network shop transaction"));
    Exact(Host,TEXT("bread"),2,TEXT("host purchase gain"));NoGain(Client,TEXT("host purchase never enters client feed"));
    Check(Pickup(Host,TEXT("bread"),3,FString())&&Pickup(Host,TEXT("bread"),4,FString()),TEXT("host consecutive confirmed pickups"));
    Exact(Host,TEXT("bread"),7,TEXT("host pickup stack merge counts only newly acquired units"));NoGain(Client,TEXT("host pickups remain private"));
    // Server builds the real compressed reply. Client processes the real chunk
    // handler, sequence guard, revision guard, publish and local persistence.
    uint32 Sequence=0;
    auto Reply=[&](const FColdSteelProfile& Before,const FColdSteelProfile& After,bool Success=true)
    {
        Request.Sequence=++Sequence;Sender->QueueInventoryReply(Request,Success,Success?TEXT("audit accepted"):TEXT("audit rejected"),Before,After);
        Check(!Sender->InventoryReplyOutgoing.IsEmpty(),TEXT("server receipt serialized"));return Sender->InventoryReplyOutgoing;
    };
    auto Arm=[&]()
    {Receiver->InventoryRequestSequence=Sequence;Receiver->bInventoryRequestPending=true;Receiver->PendingInventoryRequest=Request;Receiver->InventoryRequestPawn.Reset();Client->SetCampfireInventoryPending(true);};
    auto Deliver=[&](const TArray<uint8>& Blob,uint32 WireSequence=0)
    {
        const int32 Total=FMath::DivideAndRoundUp(Blob.Num(),ColdSteelProfileTransfer::ChunkSize);
        for(int32 I=0;I<Total;++I)
        {
            TArray<uint8> Chunk;const int32 Start=I*ColdSteelProfileTransfer::ChunkSize;
            Chunk.Append(Blob.GetData()+Start,FMath::Min(ColdSteelProfileTransfer::ChunkSize,Blob.Num()-Start));
            Receiver->ClientInventoryReplyChunk_Implementation(WireSequence?WireSequence:Sequence,I,Total,Chunk);
        }
    };
    uint32 MirrorSequence=0;
    auto Mirror=[&](const FColdSteelProfile& State,uint32 GunsmithSequence=0)
    {
        auto* Save=NewObject<UColdSteelProfileSave>();Save->Profile=State;
        TArray<uint8> Bytes;Check(ColdSteelProfileTransfer::SaveToBlob(Save,Bytes),TEXT("profile mirror serialized"));
        const int32 Total=FMath::DivideAndRoundUp(Bytes.Num(),ColdSteelProfileTransfer::ChunkSize);++MirrorSequence;
        for(int32 I=0;I<Total;++I)
        {
            TArray<uint8> Chunk;const int32 Start=I*ColdSteelProfileTransfer::ChunkSize;
            Chunk.Append(Bytes.GetData()+Start,FMath::Min(ColdSteelProfileTransfer::ChunkSize,Bytes.Num()-Start));
            Receiver->ClientReceiveProfileChunk_Implementation(MirrorSequence,I,Total,Chunk,ClientPawn,0,ClientPawn->GetWorld()->GetTimeSeconds(),GunsmithSequence);
        }
        Check(!Receiver->bMirrorReady,TEXT("mirror consumed after pawn binding through actual chunk handler"));
    };
    auto Before=Server->Snapshot();
    Check(UColdSteelShopModel::ExecuteNetworkTrade(Server,Request,GuestSlot,Reason),TEXT("guest server-shadow purchase"));
    auto After=Server->Snapshot();auto Blob=Reply(Before,After);Arm();Deliver(Blob);
    Exact(Client,TEXT("bread"),2,TEXT("client purchase receipt"));NoGain(Host,TEXT("guest purchase never enters host feed"));NoGain(Server,TEXT("shadow suppresses even enabled feed"));
    Deliver(Blob);Mirror(After);NoGain(Client,TEXT("repeated chunks plus later mirror do not duplicate purchase"));
    Mirror(Before);NoGain(Client,TEXT("stale mirror cannot replay or undo purchase"));
    Check(Client->Snapshot().CampfireInventoryRevision==After.CampfireInventoryRevision,TEXT("stale mirror preserves accepted revision"));

    const auto OldBlob=Blob;const uint32 OldSequence=Sequence;Request.Action=EColdSteelInventoryAction::Pickup;
    Before=Server->Snapshot();Check(Pickup(Server,TEXT("bread"),3,GuestSlot),TEXT("guest pickup authority commit"));After=Server->Snapshot();Blob=Reply(Before,After);
    Arm();Deliver(OldBlob,OldSequence);Check(Receiver->bInventoryRequestPending,TEXT("old receipt cannot unlock a newer pending pickup"));
    Mirror(After);NoGain(Client,TEXT("mirror during pending receipt defers inventory gain"));Deliver(Blob);
    Exact(Client,TEXT("bread"),3,TEXT("pending mirror then receipt reports pickup once"));
    Before=Server->Snapshot();Check(Pickup(Server,TEXT("bread"),4,GuestSlot),TEXT("next guest pickup"));After=Server->Snapshot();Blob=Reply(Before,After);
    Mirror(After);Exact(Client,TEXT("bread"),4,TEXT("mirror fallback reports gain"));Arm();Deliver(Blob);NoGain(Client,TEXT("mirror-first then equal-revision receipt stays silent"));
    int64 BurstTotal=0;
    for(int32 I=1;I<=8;++I)
    {Before=Server->Snapshot();Check(Pickup(Server,TEXT("bread"),I,GuestSlot),TEXT("sequential guest pickup commit"));After=Server->Snapshot();Blob=Reply(Before,After);Arm();Deliver(Blob);Mirror(After);BurstTotal+=I;}
    Exact(Client,TEXT("bread"),BurstTotal,TEXT("eight pickups plus eight mirrors coalesce exact delta"));NoGain(Host,TEXT("guest pickup burst remains private"));
    Request.Action=EColdSteelInventoryAction::Shop;
    auto FailedState=Server->Snapshot();FailedState.Souls=0;Server->AdoptNetMirror(FailedState);Before=Server->Snapshot();
    Check(!UColdSteelShopModel::ExecuteNetworkTrade(Server,Request,GuestSlot,Reason),TEXT("insufficient souls rejected"));
    Blob=Reply(Before,Server->Snapshot(),false);Arm();Deliver(Blob);NoGain(Client,TEXT("failed purchase produces no gain"));
    // Failure of local receipt persistence must not repeat the already published gain.
    Before=Server->Snapshot();Check(Pickup(Server,TEXT("mineral_water"),2,GuestSlot),TEXT("receipt save failure fixture"));After=Server->Snapshot();Blob=Reply(Before,After);
    Client->bPersistenceBlocked=true;Arm();Deliver(Blob);Client->bPersistenceBlocked=false;
    Exact(Client,TEXT("mineral_water"),2,TEXT("accepted receipt remains visible despite local disk failure"));Mirror(After);NoGain(Client,TEXT("mirror after disk failure does not duplicate"));

    Request.Action=EColdSteelInventoryAction::Pickup;
    const FString NetAmmoId=Client->AmmoDefinitionFor(Client->CreateItem(TEXT("ue_m4a1")));
    for(int64 Count:{5ll,7ll})
    {Before=Server->Snapshot();Check(Pickup(Server,NetAmmoId,Count,GuestSlot),TEXT("guest ammo pickup commit"));After=Server->Snapshot();Blob=Reply(Before,After);Arm();Deliver(Blob);Deliver(Blob);Mirror(After);}
    Exact(Client,TEXT("ammo"),12,TEXT("two ammo receipts and repeated mirrors produce exactly twelve rounds"));NoGain(Host,TEXT("guest ammo pickups remain private"));

    auto State=Client->Snapshot();auto Stack=Client->CreateItem(TEXT("bread"),5);Stack.Cell=0;State.Items={Stack};State.AmmoPouch.Reset();
    Client->AdoptNetMirror(State);Client->ResetAcquisitionNotices();auto Split=State;
    Split.Items[0].Count=2;auto Piece=Stack;Piece.InstanceId=FGuid::NewGuid().ToString();Piece.Count=3;Piece.Cell=1;Split.Items.Add(Piece);
    Client->AdoptNetMirror(Split,true);Client->AdoptNetMirror(State,true);NoGain(Client,TEXT("split and merge existing stacks are not acquisitions"));
    auto Stored=State;Stored.Items[0].Place=4;Stored.Items[0].Container.Reset();Client->AdoptNetMirror(Stored,true);Client->AdoptNetMirror(State,true);
    NoGain(Client,TEXT("personal warehouse round trip is silent"));
    auto View=State;auto Preview=Stack;Preview.InstanceId=TEXT("view-only");Preview.Place=4;Preview.Container=TEXT("NetView.audit");View.Items.Add(Preview);
    Client->AdoptNetMirror(View,true);NoGain(Client,TEXT("container preview does not grant items"));
    auto VariantBefore=State;VariantBefore.Items[0].Data=TEXT("{\"name\":\"同名物品\",\"category\":\"material\",\"rarity\":\"common\"}");VariantBefore.Items[0].Count=1;
    auto VariantAfter=VariantBefore;VariantAfter.Items[0].Data=TEXT("{\"name\":\"同名物品\",\"category\":\"material\",\"rarity\":\"rare\"}");
    Client->AdoptNetMirror(VariantBefore);Client->AdoptNetMirror(VariantAfter,true);
    FColdSteelAcquisitionNotice Notice;Check(Client->PopAcquisitionNotice(Notice)&&Notice.Key==TEXT("bread|rare")&&Notice.Count==1&&Notice.Color==ColdSteelUI::RarityColor(TEXT("rare")),TEXT("equal-total rarity exchange retains newly acquired variant and color"));
    NoGain(Client,TEXT("rarity exchange emits only one positive variant"));
    auto AmmoBefore=Blank;auto Gun=Client->CreateItem(TEXT("ue_m4a1"));Gun.Place=0;Gun.Cell=0;Gun.Magazine=10;Gun.VirtualMagazineAmmo=0;AmmoBefore.Items={Gun};
    const FString AmmoId=Client->AmmoDefinitionFor(Gun);AmmoBefore.AmmoPouch.Add(AmmoId,20);
    auto Unloaded=AmmoBefore;Unloaded.Items[0].Magazine=0;Unloaded.AmmoPouch[AmmoId]=30;
    Client->AdoptNetMirror(AmmoBefore);Client->AdoptNetMirror(Unloaded,true);NoGain(Client,TEXT("unloading real rounds is not a pickup"));
    Unloaded.AmmoPouch[AmmoId]+=9;Client->AdoptNetMirror(Unloaded,true);
    Exact(Client,TEXT("ammo"),9,TEXT("ammo pickup counts only nine new rounds"));
    // Exercise the exact timeline used by the widget, without rendering Slate.
    Client->ResetAcquisitionNotices();FColdSteelAcquisitionTimeline Timeline;
    auto Tick=[&](float Delta,int32 Capacity=5){Timeline.Advance(Delta,Capacity,[&](auto& N,const auto& Key){return Client->PopAcquisitionNotice(N,Key);});};
    auto Queue=[&](const FString& Key,int64 Count){Client->EnqueueAcquisition({Key,Key,Count,FLinearColor::White});};
    Queue(TEXT("bread|common"),2);Tick(0);Tick(1.2f);Queue(TEXT("bread|common"),3);Tick(.01f);
    Check(Timeline.Lines.Num()==1&&Timeline.Lines[0].Notice.Count==5,TEXT("visible same-item gain after 1.2 seconds merges into one exact row"));
    Queue(TEXT("bread|rare"),1);Tick(.35f);Check(Timeline.Lines.Num()==2,TEXT("same name different rarity remains separate"));
    Tick(FColdSteelAcquisitionTimeline::Life+1.f);Queue(TEXT("bread|common"),1);Tick(.35f);Check(Timeline.Lines.Num()==1&&Timeline.Lines[0].Notice.Count==1,TEXT("after expiry next pickup begins a fresh count"));
    Timeline.Reset();Client->ResetAcquisitionNotices();for(int32 I=0;I<70;++I)Queue(FString::Printf(TEXT("burst.%d"),I),I+1);
    int64 SeenTotal=0;TSet<FString> Seen;
    const int32 BurstTicks=FMath::CeilToInt((FColdSteelAcquisitionTimeline::Life+FColdSteelAcquisitionTimeline::Interval)*35.f/.1f)+100;
    for(int32 I=0;I<BurstTicks;++I)
    {
        Tick(.1f,2);
        for(const auto& Line:Timeline.Lines)if(!Seen.Contains(Line.Notice.Key)){Seen.Add(Line.Notice.Key);SeenTotal+=Line.Notice.Count;}
    }
    Check(Seen.Num()==70&&SeenTotal==2485&&Client->AcquisitionNotices.IsEmpty(),TEXT("70 distinct queued gains all appear with exact counts at two-row capacity"));
    Timeline.Reset();Client->ResetAcquisitionNotices();Queue(TEXT("a"),1);Tick(0,1);Queue(TEXT("b"),2);Tick(.35f,1);
    Check(Timeline.Lines.Num()==1&&Timeline.Lines[0].Notice.Key==TEXT("a")&&Client->AcquisitionNotices.Num()==1,TEXT("full feed retains old row and queues next gain"));
    Queue(TEXT("a"),4);Tick(.35f,1);Check(Timeline.Lines.Num()==1&&Timeline.Lines[0].Notice.Count==5,TEXT("full feed still coalesces visible key behind waiting key"));
    const auto Pending=Client->AcquisitionNotices.Num();Tick(20,0);Check(Client->AcquisitionNotices.Num()==Pending&&Timeline.Lines[0].Notice.Count==5,TEXT("zero layout space pauses without consuming gains"));
    Client->ResetAcquisitionNotices();Check(Client->AcquisitionNotices.IsEmpty(),TEXT("profile epoch reset clears queued gains"));
    // Actual chunk reassembly and mirror publication: delayed snapshots may
    // cross a free hammer customization and an unrelated inventory receipt.
    auto HammerState=Blank;auto Hammer=Client->CreateItem(TEXT("ue_thunder_god_hammer"));Hammer.Place=0;Hammer.Cell=0;
    const FString HammerId=Hammer.InstanceId;HammerState.Items={Hammer};Client->AdoptNetMirror(HammerState);
    auto SetSeat=[&](FColdSteelProfile& Profile,const TCHAR* Seat)
    {
        auto& Item=Profile.Items[0];TSharedPtr<FJsonObject> Data;
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("head_mount"),Seat);
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Data->SetNumberField(TEXT("gunsmith_version"),1);
        Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Item.Data));
    };
    auto HasSeat=[&](const TCHAR* Seat){const auto* I=Client->FindItem(HammerId);return I&&GI->GetSubsystem<UGunsmithSystem>()->Installed(*I).FindRef(TEXT("head_mount"))==Seat;};
    auto Heavy=HammerState;SetSeat(Heavy,TEXT("reinforced_block"));Client->AdoptNetMirror(Heavy);
    Receiver->LocalGunsmithSequence=1;Receiver->PendingGunsmithInstances.Add(HammerId);
    auto* SentSave=NewObject<UColdSteelProfileSave>();Client->SyncRuntime();SentSave->Profile=Client->Snapshot();
    Receiver->bHasLastSent=ColdSteelProfileTransfer::SaveToBlob(SentSave,Receiver->LastSentBlob);
    Mirror(HammerState,0);Check(HasSeat(TEXT("reinforced_block")),TEXT("old same-revision mirror cannot undo just-uploaded hammer customization"));
    auto PickupMirror=HammerState;++PickupMirror.CampfireInventoryRevision;
    auto Bread=Client->CreateItem(TEXT("bread"));Bread.Cell=4;PickupMirror.Items.Add(Bread);
    Mirror(PickupMirror,0);
    Check(HasSeat(TEXT("reinforced_block"))&&Client->FindItem(Bread.InstanceId)&&Client->Snapshot().CampfireInventoryRevision==PickupMirror.CampfireInventoryRevision,
        TEXT("new inventory revision preserves pending hammer parts and still adopts authoritative pickup"));
    auto Accepted=Client->Snapshot();Mirror(Accepted,1);
    Check(HasSeat(TEXT("reinforced_block"))&&Receiver->PendingGunsmithInstances.IsEmpty(),TEXT("matching server receipt resolves applied hammer customization"));
    auto Light=Accepted;SetSeat(Light,TEXT("ribbed_light"));Client->AdoptNetMirror(Light);
    Receiver->LocalGunsmithSequence=2;Receiver->PendingGunsmithInstances.Add(HammerId);Receiver->bHasLastSent=false;
    Mirror(Accepted,2);
    Check(HasSeat(TEXT("reinforced_block"))&&Receiver->PendingGunsmithInstances.IsEmpty(),TEXT("rejected customization rolls back even with unrelated local changes"));
    Client->AdoptNetMirror(Light);Receiver->LocalGunsmithSequence=3;Receiver->PendingGunsmithInstances.Add(HammerId);
    auto Removed=Accepted;Removed.Items.RemoveAt(0);++Removed.CampfireInventoryRevision;Mirror(Removed,2);
    Check(!Client->FindItem(HammerId)&&Client->FindItem(Bread.InstanceId),TEXT("pending customization never recreates an authority-removed hammer"));
    Mirror(Removed,3);Check(Receiver->PendingGunsmithInstances.IsEmpty(),TEXT("removed hammer receipt retires its pending customization"));
    // Switch two one-handed recipes before the first acknowledgement returns. Both
    // instances must retain their own intent until the authority accepts or rolls it back.
    auto Blades=Blank;
    auto Axe=Client->CreateItem(TEXT("ue_tactical_hatchet"));Axe.Place=1;Axe.Cell=6;
    auto Knife=Client->CreateItem(TEXT("ue_kukri"));Knife.Place=1;Knife.Cell=8;
    Blades.Items={Axe,Knife};Blades.ActiveWeaponSlot=6;
    auto Modified=Blades;
    const auto SetBlade=[](FColdSteelItem& Item,const TCHAR* Blade,const TCHAR* Pommel)
    {
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),Blade);Parts->SetStringField(TEXT("pommel"),Pommel);
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Data->SetNumberField(TEXT("gunsmith_version"),1);
        Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
    };
    SetBlade(Modified.Items[0],TEXT("hatchet_ghost_scythe"),TEXT("knife_pommel_yangu"));
    SetBlade(Modified.Items[1],TEXT("canine_blade"),TEXT("knife_pommel_chenheng"));
    const auto HasBlade=[&](const FString& Id,const TCHAR* Blade,const TCHAR* Pommel)
    {
        const auto* Item=Client->FindItem(Id);if(!Item)return false;
        const auto Parts=GI->GetSubsystem<UGunsmithSystem>()->Installed(*Item);
        return Parts.FindRef(TEXT("blade_1"))==Blade&&Parts.FindRef(TEXT("pommel"))==Pommel;
    };
    Client->AdoptNetMirror(Modified);Receiver->LocalGunsmithSequence=5;
    Receiver->PendingGunsmithInstances.Add(Axe.InstanceId);Receiver->PendingGunsmithInstances.Add(Knife.InstanceId);
    Mirror(Blades,4);
    Check(HasBlade(Axe.InstanceId,TEXT("hatchet_ghost_scythe"),TEXT("knife_pommel_yangu"))&&
        HasBlade(Knife.InstanceId,TEXT("canine_blade"),TEXT("knife_pommel_chenheng")),TEXT("stale mirror retains both hands' distinct blade and pommel recipes"));
    auto Resolved=Modified;Resolved.Items[1]=Knife;Receiver->bHasLastSent=false;
    Mirror(Resolved,5);
    Check(HasBlade(Axe.InstanceId,TEXT("hatchet_ghost_scythe"),TEXT("knife_pommel_yangu"))&&
        !HasBlade(Knife.InstanceId,TEXT("canine_blade"),TEXT("knife_pommel_chenheng"))&&Client->FindItem(Knife.InstanceId)&&
        Receiver->PendingGunsmithInstances.IsEmpty(),TEXT("authoritative mirror accepts the axe, restores the rejected kukri and clears both pending instances"));
    const FString ForgedId=TEXT("ue_forged_steel_greatsword");
    Client->AdoptNetMirror(Blank);
    Check(Client->ItemCatalog().ContainsByPredicate([&](const auto& E){return E.Definition==ForgedId&&E.Group==TEXT("武器")&&E.Subgroup==TEXT("双手剑");})
        &&Client->AddItem(ForgedId,1),TEXT("F6 forged greatsword catalog entry generates a backpack item"));
    auto ForgedStock=Client->Snapshot();
    const auto* ForgedItem=ForgedStock.Items.FindByPredicate([&](const auto& Item){return Item.Definition==ForgedId;});
    const FString ForgedInstance=ForgedItem?ForgedItem->InstanceId:FString();
    auto* Smith=GI->GetSubsystem<UGunsmithSystem>();
    const auto* Forge=GI->GetSubsystem<UColdSteelForgingSystem>();
    const auto* Recipe=Forge?Forge->Find(TEXT("forge_forged_steel_greatsword")):nullptr;
    Check(Recipe&&Recipe->Output==ForgedId&&Recipe->MetalCount==8,TEXT("forge resolves forged greatsword recipe and metal cost"));
    Check(Smith->Begin(ForgedInstance)&&Smith->Select(TEXT("blade_1"),TEXT("hollow_blade"))&&
        Smith->Select(TEXT("pommel"),TEXT("ring_chain_pommel"))&&Smith->Apply()&&
        HasBlade(ForgedInstance,TEXT("hollow_blade"),TEXT("ring_chain_pommel")),TEXT("workbench applies hollow blade and chain to generated instance"));
    auto ForgedApplied=Client->Snapshot();
    // The fixture invokes the actual mirror receiver without a socket. Stage the
    // client Apply sequence that a networked player state records at the workbench.
    Receiver->LocalGunsmithSequence=6;Receiver->PendingGunsmithInstances.Add(ForgedInstance);
    ++ForgedStock.CampfireInventoryRevision;ForgedStock.Items.Add(Bread);
    Mirror(ForgedStock,5);
    Check(HasBlade(ForgedInstance,TEXT("hollow_blade"),TEXT("ring_chain_pommel"))&&Client->FindItem(Bread.InstanceId),
        TEXT("older server reply preserves pending forged parts while admitting new pickup"));
    ForgedApplied.CampfireInventoryRevision=ForgedStock.CampfireInventoryRevision;
    ForgedApplied.Items.Add(Bread);Mirror(ForgedApplied,6);
    Check(HasBlade(ForgedInstance,TEXT("hollow_blade"),TEXT("ring_chain_pommel"))&&Receiver->PendingGunsmithInstances.IsEmpty(),
        TEXT("matching server reply confirms the forged part selection"));
    Check(Smith->Begin(ForgedInstance)&&Smith->Select(TEXT("blade_1"),TEXT("executioner_blade"))&&Smith->Apply()&&
        HasBlade(ForgedInstance,TEXT("executioner_blade"),TEXT("ring_chain_pommel")),TEXT("workbench replaces hollow with executioner while retaining chain"));
    Receiver->LocalGunsmithSequence=7;Receiver->PendingGunsmithInstances.Add(ForgedInstance);Receiver->bHasLastSent=false;
    Mirror(ForgedApplied,7);
    Check(HasBlade(ForgedInstance,TEXT("hollow_blade"),TEXT("ring_chain_pommel"))&&Receiver->PendingGunsmithInstances.IsEmpty(),
        TEXT("authority rejection restores only the previous forged selection"));
    Client->AdoptNetMirror(Blank);
    auto Bow=Client->CreateItem(TEXT("bow_woodsteel"));Bow.Place=0;Bow.Cell=0;
    auto BowStock=Blank;BowStock.Items={Bow};Client->AdoptNetMirror(BowStock);
    const auto BowParts=[&](){const auto* Found=Client->FindItem(Bow.InstanceId);return Found?Smith->Installed(*Found):FGunsmithParts();};
    Check(Smith->Begin(Bow.InstanceId)&&Smith->Select(TEXT("riser"),TEXT("highland_far_peak"))&&Smith->Apply(),
        TEXT("highland bow stock with authority-selected riser"));
    auto AuthorityBow=Client->Snapshot();
    Client->AdoptNetMirror(BowStock);
    Check(Smith->Begin(Bow.InstanceId)&&Smith->Select(TEXT("sight"),TEXT("highland_peakwatch_3_6x"))&&
        Smith->Select(TEXT("string"),TEXT("highland_mountain_echo"))&&Smith->Apply(),TEXT("workbench equips Peakwatch sight and Mountain Echo string"));
    Receiver->LocalGunsmithSequence=8;Receiver->PendingGunsmithInstances.Add(Bow.InstanceId,{TEXT("sight"),TEXT("string")});
    ++AuthorityBow.CampfireInventoryRevision;Mirror(AuthorityBow,7);
    const auto PendingBow=BowParts();
    Check(PendingBow.FindRef(TEXT("sight"))==TEXT("highland_peakwatch_3_6x")&&PendingBow.FindRef(TEXT("string"))==TEXT("highland_mountain_echo")&&
        PendingBow.FindRef(TEXT("riser"))==TEXT("highland_far_peak"),TEXT("pending sight and string survive pickup while adopting server riser"));
    Receiver->bHasLastSent=false;Mirror(AuthorityBow,8);
    const auto RejectedBow=BowParts();
    Check(RejectedBow.FindRef(TEXT("sight"))!=TEXT("highland_peakwatch_3_6x")&&RejectedBow.FindRef(TEXT("string"))!=TEXT("highland_mountain_echo")&&
        RejectedBow.FindRef(TEXT("riser"))==TEXT("highland_far_peak")&&Receiver->PendingGunsmithInstances.IsEmpty(),
        TEXT("matching rejection restores factory sight and string while keeping server riser"));
    Smith->Close();
    auto Frontier=Client->CreateItem(TEXT("bow_frontier_compound"));Frontier.Place=0;Frontier.Cell=0;
    auto FrontierStock=Blank;FrontierStock.Items={Frontier};Client->AdoptNetMirror(FrontierStock);
    Check(Smith->Begin(Frontier.InstanceId)&&Smith->Select(TEXT("riser"),TEXT("frontier_aurora"))&&
        Smith->Select(TEXT("string"),TEXT("highland_mountain_echo"))&&Smith->Apply(),TEXT("compound bow workbench applies laser and light pillar"));
    Receiver->LocalGunsmithSequence=9;Receiver->PendingGunsmithInstances.Add(Frontier.InstanceId,{TEXT("riser"),TEXT("string")});
    ++FrontierStock.CampfireInventoryRevision;Mirror(FrontierStock,8);
    auto FrontierOption=[&](const TCHAR* Slot){const auto* I=Client->FindItem(Frontier.InstanceId);return I?Smith->Installed(*I).FindRef(Slot):FString();};
    Check(FrontierOption(TEXT("riser"))==TEXT("frontier_aurora")&&FrontierOption(TEXT("string"))==TEXT("highland_mountain_echo"),
        TEXT("late inventory mirror retains both pending compound slots"));
    Receiver->bHasLastSent=false;Mirror(FrontierStock,9);
    Check(FrontierOption(TEXT("riser"))!=TEXT("frontier_aurora")&&FrontierOption(TEXT("string"))!=TEXT("highland_mountain_echo")
        &&Receiver->PendingGunsmithInstances.IsEmpty(),TEXT("matching authority rejection retires both pending compound slots"));
    Smith->Close();
    Host->SetAcquisitionFeedEnabled(false);Client->SetAcquisitionFeedEnabled(false);Server->SetAcquisitionFeedEnabled(false);
    Report+=FString::Printf(TEXT("COMPLETE checks=%d failures=%d\n"),Checks,Failures);
    FFileHelper::SaveStringToFile(Report,*(Root/TEXT("report.txt")));UE_LOG(LogTemp,Display,TEXT("ACQUISITION_AUDIT COMPLETE checks=%d failures=%d"),Checks,Failures);
    // Only isolated scratch profiles were written. No gameplay world was begun.
    Client->bPersistenceBlocked=true;GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
