#include "FPSConsumableAuditCommandlet.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelGenericMelee.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/SkillNetworkAuditCommandlet.h"
#include "../Weapons/Unarmed/UnarmedPunchTuning.h"
#include "../Weapons/Staff/StaffPrimaryAttackMotion.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/HighlandRidgeThrust.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"

void UFPSConsumableAuditCommandlet::RunGenericMeleeAudit(UWorld* World,UColdSteelStatusModel* Model,
    TFunctionRef<void(bool,const FString&,const FString&)> Check)
{
    using namespace ColdSteelGenericMelee;
    const auto Report=[&](bool Pass,const FString& Name)
    {Check(Pass,TEXT("generic melee authority: ")+Name,FString());return Pass;};
    FString Root=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("SourceAssets/FoodSpoilage20261015/TestRuns"));
    FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());
    FPaths::NormalizeDirectoryName(Root);FPaths::NormalizeDirectoryName(Saved);
    if(!Report(World&&Model&&Model->IsAudit()&&World==Model->GetWorld()
        &&Model->ProfileSlot().StartsWith(TEXT("ColdSteel_FoodSpoilageAudit_"))&&Saved.StartsWith(Root+TEXT("/"))
        &&World->GetNetMode()==NM_Standalone&&!World->GetNetDriver(),
        TEXT("requires isolated catalog/profile and direct authority calls; no socket transport")))return;
    const auto HostBefore=Model->Snapshot();
    const double OriginalTime=World->GetTimeSeconds();World->TimeSeconds=100.;
    auto* PC=World->SpawnActor<ASkillAuditRemoteController>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();
    auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Target=World->SpawnActor<AActor>();auto* OtherTarget=World->SpawnActor<AActor>();
    auto* LocalPC=World->SpawnActor<APlayerController>();
    auto* LocalPawn=World->SpawnActor<AFPSGAMECharacter>();
    auto* LocalPS=World->SpawnActor<AColdSteelPlayerState>();
    ON_SCOPE_EXIT
    {
        Model->AdoptNetMirror(HostBefore);World->TimeSeconds=OriginalTime;
        if(PS)PS->ShadowModel=nullptr;if(Pawn)Pawn->NetShadowProfile=nullptr;
        if(PC)PC->UnPossess();if(LocalPC)LocalPC->UnPossess();
        for(AActor* Actor:{static_cast<AActor*>(Pawn),static_cast<AActor*>(PS),static_cast<AActor*>(PC),
            static_cast<AActor*>(LocalPawn),static_cast<AActor*>(LocalPS),static_cast<AActor*>(LocalPC),Target,OtherTarget})
            if(Actor)Actor->Destroy();
    };
    if(!Report(PC&&Pawn&&PS&&Target&&OtherTarget&&LocalPC&&LocalPawn&&LocalPS
        &&!Pawn->HasActorBegunPlay()&&!LocalPawn->HasActorBegunPlay(),TEXT("fixture actors have no BeginPlay")))return;
    PS->SetOwner(PC);PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    // Match GameModeBase::SpawnPlayerControllerCommon for a local authority
    // controller. A bare spawned PC has neither this designation nor a
    // ULocalPlayer, so UE's no-NetDriver path correctly considers it nonlocal.
    LocalPC->SetAsLocalPlayerController();
    LocalPS->SetOwner(LocalPC);LocalPC->SetPlayerState(LocalPS);LocalPC->Possess(LocalPawn);LocalPawn->SetPlayerState(LocalPS);
    const bool RemoteAuthority=Pawn->HasAuthority(),RemoteLocal=Pawn->IsLocallyControlled();
    const bool HostAuthority=LocalPawn->HasAuthority(),HostLocal=LocalPawn->IsLocallyControlled();
    const bool HostHasShadow=LocalPS->ShadowModel!=nullptr;
    const bool RemotePossession=PC->GetPawn()==Pawn&&Pawn->GetController()==PC
        &&Pawn->GetPlayerState()==PS&&PS->GetPawn()==Pawn&&PS->GetOwner()==PC;
    const bool HostPossession=LocalPC->GetPawn()==LocalPawn&&LocalPawn->GetController()==LocalPC
        &&LocalPawn->GetPlayerState()==LocalPS&&LocalPS->GetPawn()==LocalPawn&&LocalPS->GetOwner()==LocalPC;
    const bool OwnershipReady=RemoteAuthority&&!RemoteLocal&&HostAuthority&&HostLocal&&!HostHasShadow
        &&RemotePossession&&HostPossession;
    Check(OwnershipReady,TEXT("generic melee authority: separate remote-shadow and local-host-without-shadow ownership"),
        FString::Printf(TEXT("remote_authority=%d remote_local=%d host_authority=%d host_local=%d host_shadow=%d remote_possession=%d host_possession=%d"),
            RemoteAuthority,RemoteLocal,HostAuthority,HostLocal,HostHasShadow,RemotePossession,HostPossession));
    if(!OwnershipReady)return;
    struct FCase {const TCHAR* Id;uint8 Family,Meta;};
    const FCase Cases[]={
        {TEXT("ue_rune_sword"),Sword,1},{TEXT("ue_frost_crystal_sword"),Sword,1},
        {TEXT("ue_highland_claymore"),Sword,1},{TEXT("ue_tang_dao"),Sword,1},
        {TEXT("ue_xuanchi_zhenyue"),Sword,1},{TEXT("ue_zhanmadao"),Sword,1},
        {TEXT("ue_rune_sword"),Sword,3},{TEXT("ue_rune_sword"),SwordOverhead,1},
        {TEXT("tool_axe"),Tool,0},{TEXT("tool_pickaxe"),Tool,0},{TEXT("tool_shovel"),Tool,0},
        {TEXT("ue_apprentice_staff"),Staff,0},{TEXT(""),Unarmed,UnarmedPunch::AttackMeta}
    };
    uint32 Serial=0,LocalSerial=0;
    for(const auto& C:Cases)
    {
        const FString Label=FString::Printf(TEXT("%s family=%u meta=%u"),C.Id,C.Family,C.Meta);
        World->TimeSeconds+=40.;
        auto Item=C.Family==Unarmed?FColdSteelItem{}:Model->CreateItem(C.Id);
        Item.Place=1;Item.Cell=6;
        auto Bread=Model->CreateItem(TEXT("bread"));Bread.Place=0;Bread.Cell=0;
        auto Profile=HostBefore;Profile.Items={Bread};Profile.ActiveWeaponSlot=6;
        Profile.ActiveProductionTool.Reset();Profile.Health=100.;Profile.Stamina=10000.;Profile.DungeonRun={};
        if(C.Family!=Unarmed)Profile.Items.Add(Item);
        if(C.Family==Tool)Profile.ActiveProductionTool=Item.InstanceId;
        auto* Shadow=Model->CreateShadowModel(Profile);
        if(!Report(Shadow!=nullptr,Label+TEXT(" creates only a transient guest model")))continue;
        PS->ShadowModel=Shadow;Pawn->NetShadowProfile=Shadow;
        PS->GenericMeleeReceipts.Reset();PS->GenericMeleeReadyAt=0.;
        const uint32 Accepted=++Serial;
        PS->ServerRememberGenericMeleeStart_Implementation(Pawn,Item.InstanceId,C.Family,C.Meta,Accepted);
        if(!Report(ColdSteelAuthority::ForPawn(Pawn)==Shadow&&PS->GenericMeleeReceipts.Contains(Accepted),
            Label+TEXT(" real remote-authority begin accepts the held action")))continue;
        const auto Receipt=PS->GenericMeleeReceipts.FindChecked(Accepted);
        Report(PS->HasGenericMeleeBusy(Pawn)&&!PS->CanAuthorityBeginConsumable(Pawn),
            Label+TEXT(" authoritative recovery prevents new consumption"));
        PS->ServerRememberGenericMeleeStart_Implementation(Pawn,Item.InstanceId,C.Family,C.Meta,Accepted);
        Report(PS->GenericMeleeReceipts.Num()==1&&PS->GenericMeleeReceipts.FindChecked(Accepted).Expires==Receipt.Expires,
            Label+TEXT(" duplicate begin cannot renew a receipt"));
        const uint32 TooEarly=++Serial;
        PS->ServerRememberGenericMeleeStart_Implementation(Pawn,Item.InstanceId,C.Family,C.Meta,TooEarly);
        Report(!PS->GenericMeleeReceipts.Contains(TooEarly),Label+TEXT(" another begin cannot preregister future swings"));
        FColdSteelNetHitReport Hit;Hit.GenericMeleeSerial=Accepted;Hit.AttackMeta=C.Meta;Hit.Target=Target;
        Hit.ItemInstance=Item.InstanceId;Hit.ItemDefinition=Item.Definition;
        const double Pause=C.Family==Staff?FMath::Max(StaffPrimaryAttackMotion::FleshStopSeconds,
            StaffPrimaryAttackMotion::WallStopSeconds):0.;
        Hit.ClientFireTime=Receipt.ContactUntil-Pause-ContactSlack;
        const auto* Declared=C.Family==Unarmed?nullptr:Shadow->FindItem(Item.InstanceId);
        Report(PS->RequiresGenericMeleeReceipt(Hit,Declared)&&PS->ValidateGenericMeleeReceipt(Hit,Pawn,Declared),
            Label+TEXT(" legitimate contact requires and matches its start even with all client flags cleared"));
        // Move only fixture action deadlines. No game tick, animation or asset
        // playback is used to prove old-contact/new-reservation arbitration.
        World->TimeSeconds=FMath::Max(World->GetTimeSeconds(),Hit.ClientFireTime);
        PS->GenericMeleeReadyAt=World->GetTimeSeconds()-1.;
        const FGuid Use=FGuid::NewGuid();
        PS->ServerBeginConsumableUse_Implementation(Pawn,Use,Bread.InstanceId,TEXT("bread"));
        if(!Report(PS->HasAuthorityConsumableReservation(Pawn),Label+TEXT(" real food begin reserves hands after recovery")))continue;
        const uint32 Denied=++Serial;
        PS->ServerRememberGenericMeleeStart_Implementation(Pawn,Item.InstanceId,C.Family,C.Meta,Denied);
        Report(!PS->GenericMeleeReceipts.Contains(Denied)&&PS->LastGenericMeleeSequence==Denied,
            Label+TEXT(" food rejects a new real begin and retires its sequence"));
        Report(PS->ValidateGenericMeleeReceipt(Hit,Pawn,Declared),
            Label+TEXT(" earlier accepted contact remains valid during later food use"));
        auto Forged=Hit;Forged.GenericMeleeSerial=Denied;
        Report(!PS->ValidateGenericMeleeReceipt(Forged,Pawn,Declared),Label+TEXT(" denied begin cannot supply a hit receipt"));
        Forged=Hit;++Forged.AttackMeta;
        Report(!PS->ValidateGenericMeleeReceipt(Forged,Pawn,Declared),Label+TEXT(" accepted start cannot change attack semantics"));
        Forged=Hit;Forged.ItemInstance=TEXT("wrong-instance");
        Report(!PS->ValidateGenericMeleeReceipt(Forged,Pawn,Declared)
            &&!PS->ValidateGenericMeleeReceipt(Hit,LocalPawn,Declared),Label+TEXT(" receipt binds exact instance and pawn"));
        PS->CommitGenericMeleeReceipt(Hit,Pawn,Declared);
        Report(!PS->ValidateGenericMeleeReceipt(Hit,Pawn,Declared),Label+TEXT(" replayed target contact cannot settle twice"));
        Forged=Hit;Forged.Target=OtherTarget;
        const auto* Smith=World->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
        const bool PlainThrust=C.Family==Sword&&C.Meta==3
            &&!ColdSteelModularSword::UsesOverheadFinisher(Receipt.Item)
            &&!ColdSteelModularSword::UsesRisingDragonFinisher(Receipt.Item)
            &&!HighlandRidgeThrust::Installed(Smith,&Receipt.Item);
        if(C.Family==Tool||C.Family==Unarmed||PlainThrust)
            Report(!PS->ValidateGenericMeleeReceipt(Forged,Pawn,Declared),Label+TEXT(" single-target swing cannot spend a second contact"));
        else Report(PS->ValidateGenericMeleeReceipt(Forged,Pawn,Declared),Label+TEXT(" cleave retains another legitimate target"));
        PS->ServerCancelConsumableUse_Implementation(Use);
        PS->ServerRememberGenericMeleeStart_Implementation(Pawn,Item.InstanceId,C.Family,C.Meta,Denied);
        Report(!PS->GenericMeleeReceipts.Contains(Denied),Label+TEXT(" cancelling food cannot resurrect its rejected sequence"));
        const uint32 Next=++Serial;
        PS->ServerRememberGenericMeleeStart_Implementation(Pawn,Item.InstanceId,C.Family,C.Meta,Next);
        const bool NextAccepted=PS->GenericMeleeReceipts.Contains(Next);
        Report(NextAccepted,Label+TEXT(" genuinely new start works after cancellation"));
        if(NextAccepted)
        {
            // A positive control with an unused receipt prevents target
            // exhaustion from masquerading as an expiry rejection.
            auto Fresh=Hit;Fresh.GenericMeleeSerial=Next;Fresh.Target=OtherTarget;
            auto& FreshReceipt=PS->GenericMeleeReceipts.FindChecked(Next);
            Fresh.ClientFireTime=FreshReceipt.ContactUntil-Pause-ContactSlack;
            World->TimeSeconds=FMath::Max(World->GetTimeSeconds(),Fresh.ClientFireTime);
            Report(PS->ValidateGenericMeleeReceipt(Fresh,Pawn,Declared),Label+TEXT(" unused next receipt is valid before expiry"));
            FreshReceipt.Expires=World->GetTimeSeconds()-1.;
            Report(!PS->ValidateGenericMeleeReceipt(Fresh,Pawn,Declared),Label+TEXT(" changing only expiry rejects the same unused contact"));
        }
        // Exercise the listen-host model choice without inventing a host shadow.
        Model->AdoptNetMirror(Profile);LocalPS->GenericMeleeReceipts.Reset();LocalPS->GenericMeleeReadyAt=0.;
        const uint32 HostStart=++LocalSerial;
        LocalPS->ServerRememberGenericMeleeStart_Implementation(LocalPawn,Item.InstanceId,C.Family,C.Meta,HostStart);
        Report(!LocalPS->ShadowModel&&ColdSteelAuthority::ForPawn(LocalPawn)==Model
            &&LocalPS->GenericMeleeReceipts.Contains(HostStart),Label+TEXT(" local authority accepts the same begin with no ShadowModel"));
    }
    PS->GenericMeleeReceipts.Reset();PS->GenericMeleeReadyAt=0.;
    for(int32 I=0;I<MaxReceipts;++I)
    {
        auto& R=PS->GenericMeleeReceipts.Add(100000+I);R.Pawn=Pawn;R.Expires=World->GetTimeSeconds()+10.;
    }
    const uint32 Full=++Serial;
    PS->ServerRememberGenericMeleeStart_Implementation(Pawn,FString(),Unarmed,UnarmedPunch::AttackMeta,Full);
    Report(PS->GenericMeleeReceipts.Num()==MaxReceipts&&!PS->GenericMeleeReceipts.Contains(Full),
        TEXT("full bounded cache cannot accept preregistered attacks"));
    for(auto& Pair:PS->GenericMeleeReceipts)Pair.Value.Expires=World->GetTimeSeconds()-1.;
    const uint32 AfterCleanup=++Serial;
    PS->ServerRememberGenericMeleeStart_Implementation(Pawn,FString(),Unarmed,UnarmedPunch::AttackMeta,AfterCleanup);
    Report(PS->GenericMeleeReceipts.Num()==1&&PS->GenericMeleeReceipts.Contains(AfterCleanup),
        TEXT("expired cache entries are retired before another legitimate begin"));
    Model->AdoptNetMirror(HostBefore);
    Report(Model->Snapshot().CampfireInventoryRevision==HostBefore.CampfireInventoryRevision,
        TEXT("fixture restores isolated host profile and does not commit its inventory revision"));
}
