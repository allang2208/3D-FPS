#include "VillageNetworkAudit.h"
#include "../FPSGAMECharacter.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "../NPC/ChapelNun.h"
#include "../Movement/FPSTraversalComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/VillageDefenseState.h"
#include "../WorldGeneration/VillageDefenseDebris.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/NurseZombie.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/NetDriver.h"
#include "Engine/DamageEvents.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/UnrealType.h"
#include "Dom/JsonObject.h"
#include "Containers/Ticker.h"
#include "Misc/CommandLine.h"

using namespace VillageNetAudit;
void AVillageNetworkAudit::Record(const FString& Name,bool Passed,const FString& Detail)
{
    auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("case"),Name);J->SetBoolField(TEXT("passed"),Passed);J->SetStringField(TEXT("detail"),Detail);
    Checks.Add(MakeShared<FJsonValueObject>(J));bPassed&=Passed;
    UE_LOG(LogTemp,Display,TEXT("VILLAGE_NET_CASE %s=%d %s"),*Name,Passed,*Detail);
}
void AVillageNetworkAudit::Send(int32 Case,AActor* Actor)
{
    Peer->Target=Actor;Peer->Observed=0;Peer->bPeerPassed=false;Peer->Phase=Case;Peer->ForceNetUpdate();StageAt=FPlatformTime::Seconds();
}
void AVillageNetworkAudit::Finish()
{
    if(bFinished)return;bFinished=true;
    auto J=MakeShared<FJsonObject>();J->SetBoolField(TEXT("passed"),bPassed);J->SetArrayField(TEXT("checks"),Checks);
    J->SetNumberField(TEXT("final_stage"),Stage);J->SetBoolField(TEXT("real_udp"),true);J->SetBoolField(TEXT("rendered"),false);
    J->SetStringField(TEXT("scope"),FParse::Param(FCommandLine::Get(),TEXT("VillageConstructionAudit"))
        ?TEXT("production hill village, real guest construction requests and repair input, replicated state, guest wallet, reconnect and host reset")
        :TEXT("production hills, host and remote player, production RPC/profile/disk paths, same-profile reconnect, opt-in setup and asset-load fault injection"));
    Save(TEXT("result"),J);if(Peer.IsValid())Peer->ClientFinish();
    FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([](float){FPlatformMisc::RequestExit(false);return false;}),3.f);
}
bool AVillageNetworkAudit::Bind()
{
    Host=nullptr;Guest=nullptr;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)if(auto* PC=It->Get())
    {if(PC->IsLocalController())Host=PC;else Guest=PC;}
    Hills=FindHills(GetWorld());Nun=FindNun(GetWorld());
    return Hills.IsValid()&&Nun.IsValid()&&Host.IsValid()&&Guest.IsValid()&&Host->GetPawn()&&Guest->GetPawn()&&Model(Guest.Get());
}
bool AVillageNetworkAudit::Setup()
{
    auto* H=Hills.Get();
    // Only the isolated copied world is reset, before exercising real unlock RPCs.
    auto* Saved=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(TEXT("TemperateHills_World"),0));
    if(!Saved||Saved->WorldId!=H->WorldId){Record(TEXT("isolated_world_ready"),false);return false;}
    Saved->bVillageWallRepaired=false;Saved->bVillageBlacksmithRepaired=false;Saved->VillagePlansUnlocked=0;Saved->VillagePlanVersion=2;
    if(!UGameplayStatics::SaveGameToSlot(Saved,TEXT("TemperateHills_World"),0)){Record(TEXT("fixture_world_save"),false);return false;}
    for(const TCHAR* Name:{TEXT("bVillageWallRepaired"),TEXT("bVillageBlacksmithRepaired")})
        FindFProperty<FBoolProperty>(H->GetClass(),Name)->SetPropertyValue_InContainer(H,false);
    FindFProperty<FByteProperty>(H->GetClass(),TEXT("VillagePlansUnlocked"))->SetPropertyValue_InContainer(H,0);
    for(const TCHAR* Name:{TEXT("OnRep_VillageWall"),TEXT("OnRep_VillageBlacksmith")})H->ProcessEvent(H->FindFunction(Name),nullptr);
    H->ForceNetUpdate();
    for(auto* PC:{Host.Get(),Guest.Get()})
    {
        auto* M=Model(PC);auto P=M->Snapshot();P.Level=15;P.LearnedSkills.Remove(TEXT("holyLight"));P.SkillTreeVersion=1;
        if(!M->CommitState(P)){Record(TEXT("fixture_profile_level"),false,M->ResultMessage());return false;}
        PC->GetPawn()->SetCanBeDamaged(false);
    }
    GuestIdentity=Model(Guest.Get())->Snapshot().NetworkProfileId;
    FActorSpawnParameters Spawn;Spawn.Owner=Guest.Get();Peer=GetWorld()->SpawnActor<AVillageNetworkAudit>(Spawn);
#if DO_ENABLE_NET_TEST
    if(auto* Driver=GetWorld()->GetNetDriver())
    {const auto S=Driver->PacketSimulationSettings;Record(TEXT("weak_network_enabled"),S.PktLag>=60&&S.PktLoss>=2,FString::Printf(TEXT("PktLag=%d PktLoss=%d"),S.PktLag,S.PktLoss));}
#endif
    PlaceConversation();Send(1);return true;
}
void AVillageNetworkAudit::PlaceConversation()
{
    const FVector F=Nun->GetActorForwardVector(),R=Nun->GetActorRightVector(),Base=Nun->GetActorLocation()+F*190.;
    const FVector Look=Nun->GetActorLocation()+FVector(0,0,45);
    Place(Host.Get(),Base-R*90.,Look);Place(Guest.Get(),Base+R*90.,Look);
    Peer->Position=Base+R*90.;Peer->Aim=Look;
}
void AVillageNetworkAudit::RunHost()
{
    if(bFinished)return;
    const double Now=FPlatformTime::Seconds();if(Started==0.)Started=Now;
    if(Now<Next)return;Next=Now+.1;
    if(!bPassed){Finish();return;}
    if(Now-Started>1800.){Record(TEXT("run_deadline"),false,FString::FromInt(Stage));Finish();return;}
    if(Stage==90)
    {
        bool Connected=false;for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)if(!It->Get()->IsLocalController())Connected=true;
        if(Connected)return;
        Record(TEXT("production_logout_removed_guest"),true);Stage=91;
        UE_LOG(LogTemp,Display,TEXT("VILLAGE_NET_RECONNECT_READY"));return;
    }
    if(!Bind())return;
    // Construction concurrency needs an empty work site. Ambient wildlife is
    // random and can legitimately block the production repair overlap guard.
    // Remove only ambient spawns in this isolated opt-in fixture; keep players,
    // residents, the real occupancy guard, and the later siege monster intact.
    if(Stage<=30)for(TActorIterator<APawn> It(GetWorld());It;++It)
        if(It->ActorHasTag(TEXT("WildlifeSpawned")))
        {UE_LOG(LogTemp,Display,TEXT("VILLAGE_NET_FIXTURE clear ambient %s at %s"),*It->GetName(),*It->GetActorLocation().ToCompactString());It->Destroy();}
    auto* H=Hills.Get();auto* HostD=Host->FindComponentByClass<UChapelDialogueComponent>();
    auto* GuestD=Guest->FindComponentByClass<UChapelDialogueComponent>();
    const bool Reply=Peer.IsValid()&&Peer->Observed==Peer->Phase;
    FString Detail;
    const double StageLimit=(Stage==1||Stage==60)?600.:180.;
    if(Stage>0&&Stage!=91&&Now-StageAt>StageLimit&&Stage!=75)
    {Record(TEXT("stage_deadline"),false,FString::Printf(TEXT("stage=%d peer_phase=%d observed=%d"),Stage,Peer.IsValid()?Peer->Phase:-1,Peer.IsValid()?Peer->Observed:-1));Finish();return;}
    switch(Stage)
    {
    case 0:
        if(!H->GetVillageSite().bHilltop||!HostD||!GuestD)return;
        if(Setup())Stage=1;return;
    case 1:
        if(!Reply)return;Record(TEXT("guest_profile_ready"),Peer->bPeerPassed,Peer->PeerDetail);
        HostD->Open(Nun.Get());Send(10);Stage=10;return;
    case 10:
        if(!Reply||HostD->IsPending())return;
        Record(TEXT("two_concurrent_dialogue_sessions"),Peer->bPeerPassed&&HostD->IsOpen()&&GuestD->AuthorityNun.IsValid(),Peer->PeerDetail);
        Record(TEXT("each_nun_session_bound_to_its_own_pawn_and_chapel"),
            HostD->AuthorityConversationPawn.Get()==Host->GetPawn() && GuestD->AuthorityConversationPawn.Get()==Guest->GetPawn()
            && HostD->AuthorityNun==Nun && GuestD->AuthorityNun==Nun && Nun->GetParentActor()==H);
        Record(TEXT("host_faces_own_player"),Facing(Nun.Get(),Host.Get(),Detail),Detail);
        HostD->RequestAction(TEXT("wall"));Send(20);Stage=20;return;
    case 20:
        if(!Reply||HostD->IsPending())return;
        {int32 Gates=0,Ruined=0,Sections=0;for(TActorIterator<AVillageDefenseSection> It(GetWorld());It;++It)
            {++Sections;Gates+=It->IsA<AVillageDefenseGate>();Ruined+=It->GetSectionId()>=20000;}
            Record(TEXT("concurrent_wall_unlock_is_shared_idempotent"),Peer->bPeerPassed&&H->IsVillageWallRepaired()&&Gates==2&&Ruined==0,
                FString::Printf(TEXT("sections=%d gates=%d ruined=%d host=%s guest=%s"),Sections,Gates,Ruined,*HostD->Message,*Peer->PeerDetail));}
        HostD->RequestAction(TEXT("blacksmith"));Send(30);Stage=30;return;
    case 30:
        if(!Reply||HostD->IsPending())return;
        Record(TEXT("concurrent_blacksmith_unlock_replaces_building"),Peer->bPeerPassed&&ShopState(GetWorld(),Detail),Detail+TEXT(" guest=")+Peer->PeerDetail);
        Send(40);Stage=40;return;
    case 40:
        if(!Reply)return;
        Record(TEXT("holy_light_only_granted_to_guest"),Peer->bPeerPassed&&Model(Guest.Get())->IsSkillLearned(TEXT("holyLight"))&&!Model(Host.Get())->IsSkillLearned(TEXT("holyLight")),Peer->PeerDetail);
        {const auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();auto* Save=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(PS->CampfireGuestSlot(),0));
            Record(TEXT("holy_light_durable_guest_profile"),Save&&Save->Profile.NetworkProfileId==GuestIdentity&&Save->Profile.LearnedSkills.Contains(TEXT("holyLight")));}
        HostD->Close();
        for(TActorIterator<AVillageDefenseGate> It(GetWorld());It;++It)if(It->GetSectionId()==10000){Gate=*It;break;}
        if(!Gate.IsValid()){Record(TEXT("gate_spawned"),false);return;}
        {const auto T=Gate->GetActorTransform();Peer->Position=T.TransformPosition(FVector(-150,-180,94));Peer->Aim=T.TransformPosition(FVector(-150,0,130));
            Place(Guest.Get(),Peer->Position,Peer->Aim);Place(Host.Get(),Nun->GetActorLocation()+FVector(0,0,350),Nun->GetActorLocation());}
        Send(50,Gate.Get());Stage=50;return;
    case 50:
        if(!Reply)return;Record(TEXT("remote_gate_interaction_and_collision"),Peer->bPeerPassed&&GatePose(Gate.Get(),true,Detail),Detail+TEXT(" guest=")+Peer->PeerDetail);
        PreviousGuest=Guest;Stage=90;StageAt=Now;if(auto* D=GetWorld()->GetNetDriver())D->ConnectionTimeout=10.;
        UE_LOG(LogTemp,Display,TEXT("VILLAGE_NET_DISCONNECT_CLIENT"));return;
    case 91:
        if(Guest==PreviousGuest)return;
        Record(TEXT("same_profile_reconnected"),Model(Guest.Get())->Snapshot().NetworkProfileId==GuestIdentity&&Model(Guest.Get())->IsSkillLearned(TEXT("holyLight")));
        {FActorSpawnParameters Spawn;Spawn.Owner=Guest.Get();Peer=GetWorld()->SpawnActor<AVillageNetworkAudit>(Spawn);}
        Send(60,Gate.Get());Stage=60;return;
    case 60:
        if(!Reply)return;Record(TEXT("late_join_open_gate_and_learned_skill"),Peer->bPeerPassed,Peer->PeerDetail);
        if(StartClimb()){Stage=70;StageAt=Now;}return;
    case 70:
        {auto* T=Guest->GetPawn()->FindComponentByClass<UFPSTraversalComponent>();
            if(T&&T->NetworkRequest>RequestsAtStart&&Guest->IsMoveInputIgnored())Guest->SetIgnoreMoveInput(false);
            if(!Reply)return;
            Record(TEXT("weak_network_rejected_air_catch_retries"),Peer->bPeerPassed&&T&&T->bLastTraversalSucceeded,Peer->PeerDetail);}
        {const FVector Far=Wall->GetActorLocation()+(H->GetVillageSite().Ground-Wall->GetActorLocation()).GetSafeNormal2D()*4000.+FVector(0,0,200);Peer->Position=Far;Peer->Aim=Nun->GetActorLocation();
            Place(Host.Get(),Far+FVector(200,0,0),Peer->Aim);Place(Guest.Get(),Far,Peer->Aim);}
        Send(65);Stage=65;return;
    case 65:
        if(!Reply)return;
        for(TActorIterator<AVillageDefenseGate> It(GetWorld());It;++It)if(It->GetGateAngle()>45.f)It->ToggleDoor();
        Stage=74;StageAt=Now;return;
    case 74:
        if(Now-StageAt<4.)return;
        if(StartRaid()){Stage=75;StageAt=Now;}return;
    case 75:
        {AVillageDefenseSection* Breach=nullptr;int32 Damaged=0;
            if(Now>=NextRaidReport){NextRaidReport=Now+10.;UE_LOG(LogTemp,Display,TEXT("VILLAGE_NET_SIEGE %s"),*RaidStatus());}
            for(TActorIterator<AVillageDefenseSection> It(GetWorld());It;++It)if(It->GetHealth()<It->GetMaximumHealth()){++Damaged;if(It->GetHealth()<=0.f)Breach=*It;}
            if(Breach){Record(TEXT("autonomous_ai_breaches_wall"),Raider.IsValid()&&Raider->GetController()&&FVector::Dist2D(Raider->GetActorLocation(),RaidStart)>30.,FString::Printf(TEXT("damaged=%d section=%d"),Damaged,Breach->GetSectionId()));
                Wall=Breach;Peer->ExpectedHealth=0;Send(80,Breach);Stage=80;return;}
            if(Now-StageAt>240.){Record(TEXT("autonomous_ai_breach_timeout"),false,FString::Printf(TEXT("damaged=%d %s"),Damaged,*RaidStatus()));return;}}
        return;
    case 80:
        if(!Reply)return;Record(TEXT("autonomous_breach_replicated"),Peer->bPeerPassed,Peer->PeerDetail);
        if(Raider.IsValid())Raider->Destroy();
        if(Gate->GetHealth()<=0.f)for(TActorIterator<AVillageDefenseGate> It(GetWorld());It;++It)if(It->GetHealth()>0.f){Gate=*It;break;}
        Record(TEXT("live_gate_before_streaming_race"),Gate->GetHealth()>0.f);
        Send(90,Gate.Get());Stage=100;return;
    case 100:
        if(!Reply)return;Record(TEXT("async_mesh_race_injected"),Peer->bPeerPassed,Peer->PeerDetail);
        {FDamageEvent E;Gate->TakeDamage(Gate->GetHealth(),E,nullptr,nullptr);}Send(91,Gate.Get());Stage=101;return;
    case 101:
        if(!Reply)return;Record(TEXT("gate_destroy_sync_missing_right_mesh_safe"),Peer->bPeerPassed&&Gate->GetHealth()<=0.f,Peer->PeerDetail);
        Send(93);Stage=103;return;
    case 103:
        if(!Reply)return;Record(TEXT("client_physics_debris_expires"),Peer->bPeerPassed,Peer->PeerDetail);
        {int32 Count=0;for(TActorIterator<AVillageDefenseDebris> It(GetWorld());It;++It)++Count;
            Record(TEXT("host_physics_debris_expires"),Count==0,FString::FromInt(Count));
            const FString Slot=TEXT("VillageDefenses_")+H->WorldId.ToString(EGuidFormats::Digits);
            const auto* Saved=Cast<UVillageDefenseSave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
            Record(TEXT("destroyed_gate_and_wall_saved"),Saved&&Saved->DamagedSections.Contains(Gate->GetSectionId())&&Saved->DamagedSections.Contains(Wall->GetSectionId())
                &&Saved->DamagedSections.FindRef(Gate->GetSectionId())==0.f&&Saved->DamagedSections.FindRef(Wall->GetSectionId())==0.f);}
        PlaceConversation();Send(100);Stage=110;return;
    case 110:
        if(!Reply)return;Record(TEXT("live_session_before_death"),Peer->bPeerPassed,Peer->PeerDetail);
        Guest->GetPawn()->FindComponentByClass<UFPSCombatHealthComponent>()->Health=0.f;Guest->GetPawn()->ForceNetUpdate();
        Send(101);Stage=111;return;
    case 111:
        if(!Reply)return;Record(TEXT("dead_player_open_and_action_rejected"),Peer->bPeerPassed&&!GuestD->AuthorityNun.IsValid(),Peer->PeerDetail);
        Finish();return;
    }
}
