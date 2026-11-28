#include "VillageNetworkAudit.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "../NPC/ChapelNun.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/HighVillageDefense.h"
#include "../WorldGeneration/HillsCarpenterWorkshop.h"
#include "../WorldGeneration/HillsHerbalistWorkshop.h"
#include "../WorldGeneration/VillageDefenseStairs.h"
#include "../Building/VillageWallStairs.h"
#include "../Building/VillageBuildDefense.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildPalette.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/NetDriver.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"

using namespace VillageNetAudit;
namespace
{
enum EConstructionPhase { OpenNun=210, WallPlan, SmithPlan, WoodPlan, HerbsPlan, TavernPlan,
    BattlementPlan, FortificationPlan, BreakWall, BlockRepair, PayForRepair, PlaceStair, Disconnect, Reconnect, RemoveStair, ResetPlans, InspectWall };
const FName Plans[]={TEXT("wall"),TEXT("blacksmith"),TEXT("carpenter"),TEXT("herbalist"),
    TEXT("tavern"),TEXT("high_wall"),TEXT("village_construction")};

template<class T> bool ShopMatches(UWorld* World,bool Repaired,FName ActiveTag,FName InactiveTag)
{
    for(TActorIterator<T> It(World);It;++It)
    {
        if(It->IsSceneStationAvailable()!=Repaired)continue;
        const auto* Building=Cast<AVoxelBuildWorld>(It->GetOwner());
        if(!Building)continue;
        const bool bRegistered=Building->PrefabActorAt(It->AnchorCell())==*It;
        if(bRegistered!=Repaired)continue;
        int32 Active=0,Inactive=0;
        for(const auto& Assembly:It->ShopAssemblies)if(IsValid(Assembly.Get()))
        {
            TInlineComponentArray<UStaticMeshComponent*> Parts(Assembly.Get());
            for(auto* Part:Parts)if(Part->IsVisible()&&Part->GetStaticMesh())
            {Active+=Part->ComponentHasTag(ActiveTag);Inactive+=Part->ComponentHasTag(InactiveTag);}
        }
        if(Active>0&&Inactive==0)return true;
    }
    return false;
}
bool WoodShop(UWorld* W,bool Repaired)
{
    static const FName Intact(TEXT("VillageCarpenter.Repaired")),Ruin(TEXT("VillageCarpenter.Ruined"));
    return ShopMatches<AHillsCarpenterWorkshop>(W,Repaired,Repaired?Intact:Ruin,Repaired?Ruin:Intact);
}
bool HerbShop(UWorld* W,bool Repaired)
{
    static const FName Intact(TEXT("VillageHerbalist.Repaired")),Ruin(TEXT("VillageHerbalist.Ruined"));
    return ShopMatches<AHillsHerbalistWorkshop>(W,Repaired,Repaired?Intact:Ruin,Repaired?Ruin:Intact);
}
bool AllPlans(ATemperateHillsWorld* H,bool Enabled)
{
    for(const FName Plan:Plans)if(H->IsVillagePlanUnlocked(Plan)!=Enabled)return false;
    return true;
}
bool UpgradedGeometry(UWorld* World)
{
    return TActorIterator<AHighVillageGate>(World) && TActorIterator<AHighVillageWall>(World);
}
int32 ChillOnTarget(const AActor& Wall)
{
    if(auto* Effects=Wall.FindComponentByClass<UStatusEffectsComponent>())
        for(const auto& Effect:Effects->Snapshot())
            if(Effect.Type==TEXT("chill")&&Effect.Kind==TEXT("debuff"))return Effect.Stacks;
    return 0;
}

AVoxelBuildWorld* BuildWorld(UWorld* World)
{
    for(TActorIterator<AVoxelBuildWorld> It(World);It;++It)if(It->IsReady())return *It;
    return nullptr;
}
AVoxelBuildPrefabActor* BuiltStair(UWorld* World,FIntVector Cell)
{
    for(TActorIterator<AVoxelBuildPrefabActor> It(World);It;++It)
        if(It->PrefabId()==VillageWallStairs::Id&&It->AnchorCell()==Cell)return *It;
    return nullptr;
}
const FVoxelBuildPrefab* BuildingDefinition(FName Id)
{
    auto* Palette=LoadObject<UVoxelBuildPalette>(nullptr,TEXT("/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette.DA_VoxelBuildPalette"));
    return Palette?Palette->FindComponent(Id):nullptr;
}
bool GetWallJoin(const AActor* Wall,FVector& Position)
{
    const auto* Def=BuildingDefinition(VillageBuildDefense::HighWall);
    VillageWallStairs::FDock Dock;
    if(!Def||!VillageWallStairs::MakeDockAtSocket(Def->Id,Def->Footprint,Wall,0,Dock))return false;
    Position=Dock.Pose.GetLocation();
    return true;
}
FString DescribeDock(const AVoxelBuildPrefabActor* Stair,const FTransform& Expected,const AActor* Wall)
{
    const AActor* Logic=Stair?Stair->Logic():nullptr;
    if(!Logic)return FString::Printf(TEXT("holder=%s logic=none"),*GetNameSafe(Stair));
    const FTransform Actual=Logic->GetActorTransform();
    return FString::Printf(TEXT("holder=%s logic=%s parent=%s delta_cm=%.4f delta_deg=%.4f actual=(%s) dock=(%s) wall=(%s)"),
        *GetNameSafe(Stair),*GetNameSafe(Logic),*GetNameSafe(Logic->GetAttachParentActor()),
        FVector::Distance(Actual.GetLocation(),Expected.GetLocation()),
        FMath::RadiansToDegrees(Actual.GetRotation().AngularDistance(Expected.GetRotation())),
        *Actual.ToString(),*Expected.ToString(),Wall?*Wall->GetActorTransform().ToString():TEXT("none"));
}
bool MatchesDock(const AVoxelBuildPrefabActor* Stair,const FTransform& Expected)
{
    if(!Stair||!Stair->Logic())return false;
    const FTransform Actual=Stair->Logic()->GetActorTransform();
    return FVector::Distance(Actual.GetLocation(),Expected.GetLocation())<=.15
        && Actual.GetRotation().AngularDistance(Expected.GetRotation())<=FMath::DegreesToRadians(.02)
        && Actual.GetScale3D().Equals(Expected.GetScale3D(),.0001);
}
}

void AVillageNetworkAudit::RunConstructionHost()
{
    if(bFinished)return;
    const double Now=FPlatformTime::Seconds();
    if(Started==0.)Started=Now;
    if(Now<Next)return;
    Next=Now+.15;
    if(!bPassed||Now-Started>1200.||(Stage!=0 && Now-StageAt>200.))
    {
        if(bPassed)Record(TEXT("construction_stage_deadline"),false,FString::FromInt(Stage));
        Finish();return;
    }
    if(Stage==Disconnect)
    {
        for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)if(!It->Get()->IsLocalController())return;
        Stage=Reconnect;StageAt=Now;UE_LOG(LogTemp,Display,TEXT("VILLAGE_NET_RECONNECT_READY"));return;
    }
    if(!Bind())return;
    auto* H=Hills.Get();auto* GuestModel=Model(Guest.Get());
    if(Stage==0)
    {
        if(!H->GetVillageSite().bPlaced||!GuestModel->Snapshot().NetworkProfileId.IsValid())return;
        FText Reason;
        Record(TEXT("reset_isolated_world_before_construction"),H->ResetVillageUpgrades(Reason),Reason.ToString());
        if(!bPassed)return;
        GuestIdentity=GuestModel->Snapshot().NetworkProfileId;
        Host->GetPawn()->SetCanBeDamaged(false);Guest->GetPawn()->SetCanBeDamaged(false);
        const int64 Balance=GuestModel->SoulBalance();
        const int32 RepairCost=GetDefault<AHighVillageWall>()->GetRepairSoulCost();
        Record(TEXT("fresh_guest_can_afford_wall_repair"),Balance>=RepairCost,
            FString::Printf(TEXT("starting_souls=%lld wall_cost=%d"),Balance,RepairCost));
        if(!bPassed)return;
        HostFundsBeforeRepair=Model(Host.Get())->SoulBalance();
        FActorSpawnParameters Spawn;Spawn.Owner=Guest.Get();Peer=GetWorld()->SpawnActor<AVillageNetworkAudit>(Spawn);
#if DO_ENABLE_NET_TEST
        const auto& P=GetWorld()->GetNetDriver()->PacketSimulationSettings;
        Record(TEXT("lag_and_packet_loss_active"),P.PktLag>=60&&P.PktLoss>=2,FString::Printf(TEXT("lag=%d loss=%d"),P.PktLag,P.PktLoss));
#endif
        PlaceConversation();Send(OpenNun);Stage=OpenNun;return;
    }
    if(Stage==Reconnect && Guest!=PreviousGuest && !Peer.IsValid())
    {
        Guest->GetPawn()->SetCanBeDamaged(false);
        FActorSpawnParameters Spawn;Spawn.Owner=Guest.Get();Peer=GetWorld()->SpawnActor<AVillageNetworkAudit>(Spawn);
        Peer->Aim=FVector(ConstructionCell);Send(Reconnect,Wall.Get());return;
    }
    if(Stage>=OpenNun&&Stage<=FortificationPlan)
        for(TActorIterator<APawn> It(GetWorld());It;++It)
            if(It->ActorHasTag(TEXT("WildlifeSpawned")))It->Destroy();
    if(!Peer.IsValid()||Peer->Observed!=Stage)return;
    if(Stage>=OpenNun&&Stage<=FortificationPlan)
    {
        const bool bOpen=Stage==OpenNun;
        Record(bOpen?TEXT("guest_opened_nun"):TEXT("guest_plan_")+Plans[Stage-WallPlan].ToString(),
            Peer->bPeerPassed&&(bOpen||H->IsVillagePlanUnlocked(Plans[Stage-WallPlan])),Peer->PeerDetail);
        if(!bPassed)return;
        if(Stage<FortificationPlan){Send(++Stage);return;}
        for(TActorIterator<AHighVillageWall> It(GetWorld());It;++It)
        {
            auto* Part=It->GetMasonry();
            if(!Part||!Part->GetStaticMesh()||It->GetHealth()<=0.f)continue;
            const FBox Bounds=Part->GetStaticMesh()->GetBoundingBox();
            FVector Point=Bounds.GetCenter();Point.Y=Bounds.Max.Y;
            Peer->Aim=Part->GetComponentTransform().TransformPosition(Point);
            Peer->Position=Peer->Aim+Part->GetRightVector()*135.-(Guest->GetPawn()->GetPawnViewLocation()-Guest->GetPawn()->GetActorLocation());
            Wall=*It;break;
        }
        if(!Wall.IsValid()){Record(TEXT("loaded_high_wall_bay"),false);return;}
        GuestDebitsBeforeRepair=GuestModel->Snapshot().ServerSoulDebits;
        GuestFundsBeforeRepair=GuestModel->SoulBalance();
        Place(Guest.Get(),Peer->Position,Peer->Aim);
        if(!GetWallJoin(Wall.Get(),Peer->SocketPosition)){Record(TEXT("host_has_high_wall_end_socket"),false);return;}
        UCombatStatusFormula::GetOrAdd(Wall.Get())->AddChill(2,300.f,true);
        Stage=InspectWall;Send(Stage,Wall.Get());return;
    }
    if(Stage==InspectWall)
    {
        Record(TEXT("remote_focused_wall_shows_health_and_two_chill_stacks"),Peer->bPeerPassed&&ChillOnTarget(*Wall.Get())==2,Peer->PeerDetail);
        if(!bPassed)return;
        Wall->TakeDamage(Wall->GetMaximumHealth(),FDamageEvent(),nullptr,nullptr);
        Stage=BreakWall;Send(Stage,Wall.Get());return;
    }
    if(Stage==BreakWall)
    {
        Record(TEXT("client_aimed_at_same_broken_bay"),Peer->bPeerPassed&&Wall->GetHealth()==0.f,Peer->PeerDetail);
        if(!bPassed)return;
        const FTransform Pose(Peer->Position+Wall->GetActorForwardVector()*350.);
        auto* EnemyClass=LoadClass<APoisonMaggotMonster>(nullptr,TEXT("/Game/Monsters/PoisonMaggot/BP_PoisonMaggot.BP_PoisonMaggot_C"));
        auto* Threat=EnemyClass?GetWorld()->SpawnActorDeferred<APoisonMaggotMonster>(EnemyClass,Pose,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn):nullptr;
        if(!Threat){Record(TEXT("hostile_at_breach"),false);return;}
        Threat->AutoPossessAI=EAutoPossessAI::Disabled;Threat->FinishSpawning(Pose);
        if(auto* Movement=Threat->GetCharacterMovement())Movement->DisableMovement();
        RepairThreat=Threat;
        Stage=BlockRepair;Send(Stage,Wall.Get());return;
    }
    if(Stage==BlockRepair)
    {
        const int64 Funds=GuestModel->SoulBalance();
        const int64 Debits=GuestModel->Snapshot().ServerSoulDebits;
        const FString Detail=FString::Printf(TEXT("%s host_hp=%.0f host_guest_souls=%lld->%lld host_guest_debits=%lld->%lld hostile=%d"),
            *Peer->PeerDetail,Wall->GetHealth(),GuestFundsBeforeRepair,Funds,GuestDebitsBeforeRepair,Debits,RepairThreat.IsValid());
        Record(TEXT("remote_enemy_block_preserves_wall_and_wallet"),Peer->bPeerPassed&&Wall->GetHealth()==0.f
            &&Funds==GuestFundsBeforeRepair&&Debits==GuestDebitsBeforeRepair,Detail);
        if(RepairThreat.IsValid())RepairThreat->Destroy();
        Stage=PayForRepair;Send(Stage,Wall.Get());return;
    }
    if(Stage==PayForRepair)
    {
        const int32 Cost=Wall->GetRepairSoulCost();
        Record(TEXT("eight_remote_E_presses_one_purchase"),Peer->bPeerPassed&&Wall->GetHealth()==Wall->GetMaximumHealth()
            &&GuestModel->Snapshot().ServerSoulDebits==GuestDebitsBeforeRepair+Cost
            &&GuestModel->SoulBalance()==GuestFundsBeforeRepair-Cost&&Model(Host.Get())->SoulBalance()==HostFundsBeforeRepair,
            Peer->PeerDetail+FString::Printf(TEXT(" guest=%lld before=%lld cost=%d"),GuestModel->SoulBalance(),GuestFundsBeforeRepair,Cost));
        if(!bPassed)return;
        auto* Build=BuildWorld(GetWorld());const auto* Def=BuildingDefinition(VillageWallStairs::Id);
        bool Found=false;
        for(TActorIterator<AHighVillageWall> It(GetWorld());Build&&Def&&It&&!Found;++It)
        {
            for(int32 Socket=0;Socket<8&&!Found;++Socket)
            {
                VillageWallStairs::FDock Dock;FString Reason;
                if(!VillageWallStairs::MakeDockAtSocket(Def->Id,Def->Footprint,*It,Socket,Dock)
                    ||!Build->CanPlacePrefab(Def->Id,Dock.Anchor,Dock.Yaw,Reason,false,true,*It))continue;
                ConstructionCell=Dock.Anchor;ConstructionTransform=Dock.Pose;
                Peer->Aim=FVector(Dock.Anchor);Peer->ExpectedHealth=float(Socket);
                Peer->Position=AVoxelBuildWorld::CellCenter(Dock.Anchor)+FVector(0,0,900);
                Place(Guest.Get(),Peer->Position,Dock.Pose.GetLocation());
                Stage=PlaceStair;Send(Stage,*It);Found=true;
            }
        }
        Record(TEXT("available_stair_socket"),Found);return;
    }
    if(Stage==PlaceStair)
    {
        auto* Stair=BuiltStair(GetWorld(),ConstructionCell);
        Record(TEXT("remote_stair_uses_authoritative_socket"),Peer->bPeerPassed&&MatchesDock(Stair,ConstructionTransform),
            TEXT("client ")+Peer->PeerDetail+TEXT(" server ")+DescribeDock(Stair,ConstructionTransform,Peer->Target.Get()));
        if(!bPassed)return;
        PreviousGuest=Guest;Peer.Reset();Stage=Disconnect;StageAt=Now;
        GetWorld()->GetNetDriver()->ConnectionTimeout=10.f;
        UE_LOG(LogTemp,Display,TEXT("VILLAGE_NET_DISCONNECT_CLIENT"));return;
    }
    if(Stage==Reconnect)
    {
        Record(TEXT("same_guest_reconnects_with_upgrades_and_paid_bay"),Peer->bPeerPassed
            &&GuestModel->Snapshot().NetworkProfileId==GuestIdentity&&GuestModel->SoulBalance()==GuestFundsBeforeRepair-Wall->GetRepairSoulCost(),Peer->PeerDetail);
        if(!bPassed)return;
        auto* Stair=BuiltStair(GetWorld(),ConstructionCell);
        if(!Stair){Record(TEXT("placed_stair_on_reconnect"),false);return;}
        Peer->Position=Stair->GetActorLocation()+FVector(0,0,900);
        Peer->Aim=FVector(ConstructionCell);
        Place(Guest.Get(),Peer->Position,Stair->GetActorLocation());
        Stage=RemoveStair;Send(Stage,Stair);return;
    }
    if(Stage==RemoveStair)
    {
        Record(TEXT("remote_stair_removed_on_both_peers"),Peer->bPeerPassed&&BuiltStair(GetWorld(),ConstructionCell)==nullptr,Peer->PeerDetail);
        if(!bPassed)return;
        FText Error;Record(TEXT("host_resets_upgrades"),H->ResetVillageUpgrades(Error),Error.ToString());
        Stage=ResetPlans;Send(Stage);return;
    }
    if(Stage==ResetPlans)
    {
        auto* Save=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(TEXT("TemperateHills_World"),0));
        Record(TEXT("reset_reaches_guest_and_world_save"),Peer->bPeerPassed&&AllPlans(H,false)&&Save&&Save->WorldId==H->WorldId
            &&!Save->bVillageWallRepaired&&!Save->bVillageBlacksmithRepaired&&Save->VillagePlansUnlocked==0,Peer->PeerDetail);
        Finish();
    }
}

void AVillageNetworkAudit::RunConstructionClient()
{
    auto* PC=Cast<APlayerController>(GetOwner());auto* H=FindHills(GetWorld());auto* D=PC?PC->FindComponentByClass<UChapelDialogueComponent>():nullptr;
    if(!PC||!PC->GetPawn()||!H||!D||Phase<OpenNun)return;
    if(PreviousPhase!=Phase){PreviousPhase=Phase;ClientAt=FPlatformTime::Seconds();bRequested=bReported=false;}
    if(bReported)return;
    const double Age=FPlatformTime::Seconds()-ClientAt;
    bool Pass=false;FString Detail;
    if(Phase==OpenNun)
    {
        auto* N=FindNun(GetWorld());
        if(!bRequested&&N){Place(PC,Position,Aim);D->Open(N);bRequested=D->IsPending()||D->IsOpen();}
        Pass=D->IsOpen()&&!D->IsPending();
    }
    else if(Phase>=WallPlan&&Phase<=FortificationPlan)
    {
        const FName Plan=Plans[Phase-WallPlan];
        if(!bRequested&&D->IsOpen()&&!D->IsPending()){D->RequestAction(Plan);bRequested=true;}
        Pass=bRequested&&!D->IsPending()&&H->IsVillagePlanUnlocked(Plan);
        if(Phase==WoodPlan)Pass&=WoodShop(GetWorld(),true);
        if(Phase==HerbsPlan)Pass&=HerbShop(GetWorld(),true);
        if(Phase==BattlementPlan)Pass&=UpgradedGeometry(GetWorld());
        Detail=D->Message;
    }
    else if(Phase==InspectWall)
    {
        auto* Bay=Cast<AVillageDefenseSection>(Target);
        if(!bRequested&&Bay){D->Close();Place(PC,Position,Aim);bRequested=true;}
        auto* Focus=ColdSteelWorldInteraction::TraceUseTargets(PC).Target;
        FVector Join;
        const double Offset=GetWallJoin(Bay,Join)?FVector::Distance(Join,SocketPosition):MAX_dbl;
        Pass=Bay&&Focus==Bay&&Bay->GetHealth()==Bay->GetMaximumHealth()&&ChillOnTarget(*Bay)==2&&Offset<=.15;
        Detail=FString::Printf(TEXT("focus=%s bay=%s hp=%.0f chill=%d wall_socket_delta_cm=%.4f"),*GetNameSafe(Focus),*GetNameSafe(Bay),
            Bay?Bay->GetHealth():-1.f,Bay?ChillOnTarget(*Bay):-1,Offset);
    }
    else if(Phase==BreakWall||Phase==BlockRepair||Phase==PayForRepair)
    {
        auto* Bay=Cast<AVillageDefenseSection>(Target);auto* Wallet=Model(PC);
        if(Phase==BreakWall&&Bay&&Wallet)
        {
            if(!bRequested){D->Close();Place(PC,Position,Aim);bRequested=true;GuestFundsBeforeRepair=Wallet->SoulBalance();}
            Pass=Bay->GetHealth()==0.f&&ColdSteelWorldInteraction::TraceUseTargets(PC).Target==Bay;
        }
        else if(Bay&&Wallet)
        {
            const bool bBlocked=Phase==BlockRepair;
            if(!bRequested&&(!bBlocked||Bay->HasNearbyRepairEnemy(PC->GetPawn()))&&ColdSteelWorldInteraction::TraceUseTargets(PC).Target==Bay)
            {
                for(int32 I=0;I<8;++I){PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::E,IE_Pressed,1.f));PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::E,IE_Released,0.f));}
                bRequested=true;Next=FPlatformTime::Seconds()+2.;
            }
            Pass=bRequested&&(bBlocked
                ?FPlatformTime::Seconds()>=Next&&Bay->GetHealth()==0.f&&Wallet->SoulBalance()==GuestFundsBeforeRepair
                :Bay->GetHealth()==Bay->GetMaximumHealth()&&Wallet->SoulBalance()==GuestFundsBeforeRepair-Bay->GetRepairSoulCost()&&ChillOnTarget(*Bay)==0);
        }
        Detail=FString::Printf(TEXT("requested=%d bay=%s aimed=%s hp=%.0f souls=%lld"),bRequested,*GetNameSafe(Bay),
            *GetNameSafe(ColdSteelWorldInteraction::TraceUseTargets(PC).Target),Bay?Bay->GetHealth():-1.f,Wallet?Wallet->SoulBalance():-1LL);
    }
    else if(Phase==Reconnect)
    {
        auto* Bay=Cast<AVillageDefenseSection>(Target);
        auto* Stair=BuiltStair(GetWorld(),FIntVector(Aim));
        Pass=AllPlans(H,true)&&UpgradedGeometry(GetWorld())&&Bay&&Bay->GetHealth()==Bay->GetMaximumHealth()&&Stair&&Stair->Logic()
            &&WoodShop(GetWorld(),true)&&HerbShop(GetWorld(),true);
        Detail=TEXT("replicated plans, two available workstations, high gate, stairs and restored bay");
    }
    else if(Phase==PlaceStair||Phase==RemoveStair)
    {
        auto* PS=PC->GetPlayerState<AColdSteelPlayerState>();auto* Build=BuildWorld(GetWorld());
        const FIntVector Cell(Aim);auto* Stair=BuiltStair(GetWorld(),Cell);
        VillageWallStairs::FDock Dock;
        const auto* Def=BuildingDefinition(VillageWallStairs::Id);
        const bool bPlace=Phase==PlaceStair;
        const bool bSocket=bPlace&&Def&&VillageWallStairs::MakeDockAtSocket(Def->Id,Def->Footprint,Target.Get(),FMath::RoundToInt(ExpectedHealth),Dock);
        if(!bRequested&&PS&&Build&&(bPlace?bSocket:(Stair&&Target==Stair)))
        {
            Place(PC,Position,bPlace?Dock.Pose.GetLocation():Stair->GetActorLocation());
            FColdSteelInventoryRequest Request;Request.Action=EColdSteelInventoryAction::Building;
            Request.ContainerRevision=int64(Build->StructureRevision());
            Request.Mode=bPlace?TEXT("wallDockPrefab"):TEXT("removePrefab");Request.Target=Target.Get();
            if(bPlace){Request.Definition=Def->Id;Request.Cell=Dock.Socket;Request.Anchor=Dock.Anchor;Request.Orientation=Dock.Yaw;}
            bRequested=PS->RequestInventoryAction(Request);
        }
        Pass=bRequested&&(bPlace?(bSocket&&MatchesDock(Stair,Dock.Pose)):Stair==nullptr);
        Detail=FString::Printf(TEXT("request=%d socket=%d cell=%s"),bRequested,bSocket,*Cell.ToString());
        if(bPlace&&bSocket)Detail+=TEXT(" ")+DescribeDock(Stair,Dock.Pose,Target.Get());
    }
    else if(Phase==ResetPlans)
    {
        Pass=AllPlans(H,false)&&!TActorIterator<AHighVillageGate>(GetWorld())&&!TActorIterator<AHighVillageWall>(GetWorld())
            &&WoodShop(GetWorld(),false)&&HerbShop(GetWorld(),false);
        Detail=TEXT("plans cleared, fixed high wall and gate gone, wood and alchemy stations unavailable");
    }
    if(Pass||Age>75.){bReported=true;ServerResult(Phase,Pass,Detail);}
}
