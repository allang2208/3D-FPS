#include "HillsContinuityAudit.h"
#include "HillsContinuitySupport.h"
#include "../FPSGAMECharacter.h"
#include "../FPSWeatherManager.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/ChapelShrine.h"
#include "../WorldGeneration/HillsNightRaidSubsystem.h"
#include "../WorldGeneration/HillsNightRaidSave.h"
#include "../WorldGeneration/HillsNightPortal.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/FatZombie.h"
#include "../Monsters/MonsterAIController.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/NetDriver.h"
#include "Engine/DamageEvents.h"
#include "EngineUtils.h"
#include "Engine/GameInstance.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

using namespace HillsContinuity;
void AHillsContinuityAudit::PlayerWasHit(AActor* Victim,float Damage,const UDamageType* Type,AController* SourceController,AActor* Causer)
{
    if(Director&&Phase==102&&Damage>0&&Causer&&Causer->ActorHasTag(TEXT("HillsNightRaider")))
    {++NativePlayerHits;UE_LOG(LogTemp,Display,TEXT("HILLS_CONTINUITY_NATIVE_PLAYER_HIT causer=%s damage=%.2f"),*Causer->GetName(),Damage);}
}
namespace
{
template<class T>T* Find(UWorld* W){for(TActorIterator<T> It(W);It;++It)return *It;return nullptr;}
FString Slot(const ATemperateHillsWorld* H){return TEXT("HillsNight_")+H->WorldId.ToString(EGuidFormats::Digits);}
void Retreat(APlayerController* PC,ATemperateHillsWorld* H,float Offset)
{
    const auto& S=H->GetVillageSite();const auto XY=S.World(Offset,S.PadHalfY+5000.);
    Place(PC,FVector(XY,H->Height(XY.X,XY.Y)+10),FVector(S.Ground));
}
}
void AHillsContinuityAudit::Record(const FString& Case,bool Pass,const FString& Text)
{
    auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Case);R->SetBoolField(TEXT("passed"),Pass);R->SetStringField(TEXT("detail"),Text);
    Checks.Add(MakeShared<FJsonValueObject>(R));Passed&=Pass;
    UE_LOG(LogTemp,Display,TEXT("HILLS_CONTINUITY_CASE %s=%d %s"),*Case,Pass,*Text);
}
void AHillsContinuityAudit::Send(int32 Step,AActor* Object,FVector Position,float Value)
{
    Phase=Step;Began=FPlatformTime::Seconds();Requested=SawExit=false;
    Peer->Reported=0;Peer->Phase=Step;Peer->Target=Object;Peer->Point=Position;Peer->Expected=Value;Peer->ForceNetUpdate();
    UE_LOG(LogTemp,Display,TEXT("HILLS_CONTINUITY_PHASE %d"),Step);
}
void AHillsContinuityAudit::Finish()
{
    auto J=MakeShared<FJsonObject>();J->SetBoolField(TEXT("passed"),Passed);J->SetArrayField(TEXT("checks"),Checks);
    J->SetBoolField(TEXT("restart"),Restart);if(Hills.IsValid()){J->SetStringField(TEXT("world_id"),Hills->WorldId.ToString());J->SetNumberField(TEXT("seed"),Hills->Seed);}
    Save(Restart?TEXT("restart-result"):TEXT("initial-result"),J);if(Peer.IsValid())Peer->ClientExit();
    Director=false;FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([](float){FPlatformMisc::RequestExit(false);return false;}),3.f);
}
bool AHillsContinuityAudit::Bind()
{
    Host=nullptr;Guest=nullptr;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)if(auto* PC=It->Get())
        {if(PC->IsLocalController())Host=PC;else Guest=PC;}
    Hills=Find<ATemperateHillsWorld>(GetWorld());Shrine=Find<AChapelShrine>(GetWorld());Weather=Find<AFPSWeatherManager>(GetWorld());
    return Host.IsValid()&&Guest.IsValid()&&Character(Host.Get())&&Character(Guest.Get())&&Hills.IsValid()&&Hills->bReady&&Shrine.IsValid()&&Weather.IsValid();
}
bool AHillsContinuityAudit::SetGroundPositions()
{
    const auto& Site=Hills->GetVillageSite();
    for(int32 I=0;I<12;++I)
    {
        const auto XY=Site.Approach(I<6?1.:-1.,Site.PadHalfX-TemperateVillageLayout::HalfX+Site.Shoulder+800.+(I%6)*300.,Hills->Seed);
        const FVector Direction=FVector(XY-FVector2D(Site.Ground),0).GetSafeNormal();
        FVector Feet(XY,Hills->Height(XY.X,XY.Y));bool Clear=true;
        for(int32 J=0;J<3;++J)
        {
            const auto P=Feet+Direction*(J*700.);FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(ContinuityFloor),false);
            if(!GetWorld()->LineTraceSingleByChannel(Hit,P+FVector(0,0,500),P-FVector(0,0,1000),ECC_Visibility,Q)
                ||!Hit.GetComponent()->ComponentHasTag(TEXT("HillsGround"))||Hit.ImpactNormal.Z<.8){Clear=false;break;}
            if(J==0)Feet=Hit.ImpactPoint;
        }
        if(!Clear)continue;
        Place(Guest.Get(),Feet,Feet+Direction*1000.);Place(Host.Get(),Feet+FVector(-Direction.Y,Direction.X,0)*250.,Feet+Direction*1000.);
        StartPosition=Character(Host.Get())->GetActorLocation();Point=Direction;return true;
    }
    return false;
}
bool AHillsContinuityAudit::SetPewPositions()
{
    for(TActorIterator<AActor> It(GetWorld());It;++It)
    {
        TInlineComponentArray<UStaticMeshComponent*> Components(*It);
        for(auto* M:Components)if(M->GetStaticMesh()&&M->GetStaticMesh()->GetName()==TEXT("SM_ChapelPew"))
        {
            const auto* ISM=Cast<UInstancedStaticMeshComponent>(M);const int32 Count=ISM?ISM->GetInstanceCount():1;
            for(int32 I=0;I<Count;++I)
            {
                FTransform T=M->GetComponentTransform();if(ISM)ISM->GetInstanceTransform(I,T,true);
                if(!T.GetScale3D().Equals(FVector(1.25),.02)||T.GetUnitAxis(EAxis::Z).Z<.96)continue;
                const FVector Forward=T.GetRotation().RotateVector(FVector(-110,0,0));
                const FVector H=T.TransformPosition(FVector(-18,-70,0))+Forward,G=T.TransformPosition(FVector(-18,0,0))+Forward;
                auto* C=Character(Host.Get());FCollisionQueryParams Q(SCENE_QUERY_STAT(ContinuityPew),false,C);Q.AddIgnoredActor(Character(Guest.Get()));
                const auto Shape=FCollisionShape::MakeCapsule(C->GetCapsuleComponent()->GetScaledCapsuleRadius(),C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
                const FVector Up(0,0,C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3);
                if(GetWorld()->OverlapBlockingTestByChannel(H+Up,FQuat::Identity,ECC_Pawn,Shape,Q)||GetWorld()->OverlapBlockingTestByChannel(G+Up,FQuat::Identity,ECC_Pawn,Shape,Q))continue;
                Pew=T;GuestSeat=G;GuestAim=T.TransformPosition(FVector(-8,0,43.6488));
                Place(Host.Get(),H,T.TransformPosition(FVector(-8,-70,43.6488)));Place(Guest.Get(),G,GuestAim);return true;
            }
        }
    }
    return false;
}
void AHillsContinuityAudit::RunHost()
{
    const double Now=FPlatformTime::Seconds();if(Started==0.){Started=Began=Now;Restart=HillsContinuity::Restart();}
    if(Now-Started>1500.){Record(TEXT("bounded_completion"),false,FString::Printf(TEXT("phase=%d"),Phase));Finish();return;}
    const bool Bound=Bind();auto* Raid=GetWorld()->GetSubsystem<UHillsNightRaidSubsystem>();
    if(Now>=NextLog)
    {
        NextLog=Now+30.;UE_LOG(LogTemp,Display,TEXT("HILLS_CONTINUITY_WAIT phase=%d bound=%d raid=%d host_body=%d guest_body=%d alive=%d ward=%.1f"),Phase,Bound,Raid&&Raid->IsSessionReady(),BodyReady(Host.IsValid()?Host->GetPawn():nullptr),BodyReady(Guest.IsValid()?Guest->GetPawn():nullptr),Raiders(GetWorld()).Num(),Shrine.IsValid()?Shrine->Durability:-1.);
        if(Phase>=100)for(auto* Monster:Raiders(GetWorld()))
        {
            const auto* AI=Cast<AMonsterAIController>(Monster->GetController());const auto* B=AI?AI->GetBlackboardComponent():nullptr;
            UE_LOG(LogTemp,Display,TEXT("HILLS_CONTINUITY_AI name=%s position=%s speed=%.1f state=%d target=%s goal=%s visible=%d can_attack=%d"),
                *Monster->GetName(),*Monster->GetActorLocation().ToString(),Monster->GetVelocity().Size2D(),int32(Monster->State),
                *GetNameSafe(B?B->GetValueAsObject(TEXT("Target")):nullptr),B?*B->GetValueAsVector(TEXT("LastKnown")).ToString():TEXT("none"),
                B&&B->GetValueAsBool(TEXT("Visible")),B&&B->GetValueAsBool(TEXT("CanAttack")));
        }
    }
    // Capture restored production state before waiting for the new client/body preload.
    if(Restart&&Phase==0&&Raid&&Raid->IsSessionReady()&&Hills.IsValid()&&Weather.IsValid()&&Shrine.IsValid())
    {
        auto* Before=Cast<UHillsNightRaidSave>(UGameplayStatics::LoadGameFromSlot(TEXT("HillsContinuityReference"),0));
        Raid->Checkpoint();auto* After=Cast<UHillsNightRaidSave>(UGameplayStatics::LoadGameFromSlot(Slot(Hills.Get()),0));
        Record(TEXT("restart_world_and_seed"),Before&&After&&Before->WorldId==Hills->WorldId&&Before->Seed==Hills->Seed);
        Record(TEXT("restart_night_budget_and_clock"),Before&&After&&Before->NightSerial==After->NightSerial&&Before->Spawned==After->Spawned&&Before->WaveRemaining==After->WaveRemaining&&After->Weather.Day==Before->Weather.Day&&FMath::Abs(After->Weather.DayTime-Before->Weather.DayTime)<.01,
            After?FString::Printf(TEXT("spawned=%d remaining=%d day=%d hour=%.4f"),After->Spawned,After->WaveRemaining,After->Weather.Day,After->Weather.DayTime*24.):TEXT("missing sidecar"));
        bool Same=Before&&After&&Before->Raiders.Num()==After->Raiders.Num();float MaxDistance=0.;
        TSet<int32> Used;
        if(Same)for(const auto& R:Before->Raiders)
        {
            int32 Best=INDEX_NONE;double Distance=DBL_MAX;
            for(int32 I=0;I<After->Raiders.Num();++I)if(!Used.Contains(I)&&After->Raiders[I].Kind==R.Kind&&FMath::IsNearlyEqual(After->Raiders[I].Health,R.Health,.1f))
            {const double D=FVector::Dist(R.Transform.GetLocation(),After->Raiders[I].Transform.GetLocation());if(D<Distance){Best=I;Distance=D;}}
            Same&=Best!=INDEX_NONE&&Distance<500.;Used.Add(Best);MaxDistance=FMath::Max(MaxDistance,float(Distance));
        }
        Record(TEXT("restart_survivors_health_positions_and_no_dead_respawn"),Same,FString::Printf(TEXT("before=%d after=%d max_distance=%.1f"),Before?Before->Raiders.Num():-1,After?After->Raiders.Num():-1,MaxDistance));
        Record(TEXT("restart_dormant_shrine_and_portal"),Before&&After&&After->ShrineHealth==0&&After->Night&&After->PortalActive&&After->PortalAge>=Before->PortalAge-1.);
        Phase=80;
    }
    if(Phase==90)
    {
        if(Guest.IsValid())return;Phase=91;UE_LOG(LogTemp,Display,TEXT("HILLS_CONTINUITY_REJOIN_READY"));return;
    }
    if(!Bound||!Raid||!Raid->IsSessionReady())return;
    if(auto* Load=GetWorld()->GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>();Load&&Load->IsHoldingGameplayInput())return;
    auto* HP=Character(Host.Get());auto* GP=Character(Guest.Get());
    if(Phase==0)
    {
        if(!BodyReady(HP)||!BodyReady(GP))return;
        HP->FindComponentByClass<UFPSPlayerBodyComponent>()->SetBodyType(TEXT("jason"));
        auto Clock=Weather->CapturePersistentState();Clock.DayTime=.375f;Clock.DaySeconds=86400.f;Weather->RestorePersistentState(Clock);
        FActorSpawnParameters P;P.Owner=Guest.Get();Peer=GetWorld()->SpawnActor<AHillsContinuityAudit>(P);
        auto* Driver=GetWorld()->GetNetDriver();Record(TEXT("real_udp_driver"),Driver&&Driver->ClientConnections.Num()==1,GetNameSafe(Driver));
#if DO_ENABLE_NET_TEST
        Record(TEXT("driver_packet_emulation_readback"),Driver&&Driver->PacketSimulationSettings.PktLag==60&&Driver->PacketSimulationSettings.PktLoss==2,
            Driver?FString::Printf(TEXT("lag=%d loss=%d"),Driver->PacketSimulationSettings.PktLag,Driver->PacketSimulationSettings.PktLoss):TEXT("no driver"));
#endif
        TArray<uint8> OriginalBytes;
        FFileHelper::LoadFileToArray(OriginalBytes,*(FPaths::ProjectDir()/TEXT("../OriginalSaveBackup/TemperateHills_World.sav")));
        auto* Original=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromMemory(OriginalBytes));
        const bool OriginalWall=Original&&(Original->bVillageWallRepaired||(Original->VillagePlanVersion<2&&(Original->VillagePlansUnlocked&1)));
        const bool OriginalShop=Original&&(Original->bVillageBlacksmithRepaired||(Original->VillagePlanVersion<2&&(Original->VillagePlansUnlocked&2)));
        Record(TEXT("copied_existing_world_identity_seed_and_repairs"),Original&&Original->WorldId==Hills->WorldId&&Original->Seed==Hills->Seed
            &&OriginalWall==Hills->IsVillageWallRepaired()&&OriginalShop==Hills->IsVillageBlacksmithRepaired(),
            Original?FString::Printf(TEXT("original=%s seed=%d version=%d plans_version=%d effective_wall=%d effective_shop=%d"),*Original->WorldId.ToString(),Original->Seed,Original->Version,Original->VillagePlanVersion,OriginalWall,OriginalShop):TEXT("original backup not decoded"));
        int32 Budget=0;GConfig->GetInt(TEXT("TemperateHills.NightRaid"),TEXT("MaxPerNight"),Budget,GGameIni);
        Record(TEXT("isolated_three_monster_budget"),Budget==3,FString::Printf(TEXT("MaxPerNight=%d"),Budget));
        if(Budget!=3){Finish();return;}
        Send(1);return;
    }
    if(Phase==80||Phase==91)
    {
        if(!BodyReady(GP))return;
        FActorSpawnParameters P;P.Owner=Guest.Get();Peer=GetWorld()->SpawnActor<AHillsContinuityAudit>(P);
        if(Phase==80){Retreat(Host.Get(),Hills.Get(),0);Retreat(Guest.Get(),Hills.Get(),300);Send(9,nullptr,FVector::ZeroVector,Weather->NormalizedDayTime*24.f);}
        else Send(4,HP);
        return;
    }
    if(Phase==2&&Now-Began>2.&&Now-Began<6.)HP->AddMovementInput(Point);
    if(Phase==3)
    {
        if(!Requested)
        {
            const FVector At=Pew.TransformPosition(FVector(-8,-70,43.6488));const bool Aimed=Aim(Host.Get(),At);
            if(Now-Began>5.&&Aimed&&HP->FindComponentByClass<UFPSFurnitureRestComponent>()->UpdateFocus(true).Contains(TEXT("坐下")))
            {KeyE(Host.Get());Requested=true;UE_LOG(LogTemp,Display,TEXT("HILLS_CONTINUITY_HOST_E %s"),*InteractionTrace(Host.Get(),At));}
        }
        const auto State=RestState(HP);SawEnter|=State.Phase==1||State.Phase==2;
    }
    if(Phase==6)SawExit|=RestState(HP).Phase==4;
    if(Phase==100)
    {
        auto Monsters=Raiders(GetWorld());if(Monsters.Num()<3)return;
        Record(TEXT("natural_portal_spawn_three_raiders"),Find<AHillsNightPortal>(GetWorld())!=nullptr);
        Bait=Monsters[0];auto* Health=GP->FindComponentByClass<UFPSCombatHealthComponent>();Health->MaxHealth=Health->Health=1000.f;GP->ForceNetUpdate();PlayerHealth=Health->Health;
        const FVector Feet=Bait->GetActorLocation()-FVector(0,0,Bait->GetCapsuleComponent()->GetScaledCapsuleHalfHeight())+Bait->GetActorForwardVector()*160.;
        GP->OnTakeAnyDamage.AddDynamic(this,&AHillsContinuityAudit::PlayerWasHit);
        Place(Guest.Get(),Feet,Bait->GetActorLocation(),true);Phase=102;Began=Now;return;
    }
    if(Phase==102)
    {
        if(NativePlayerHits>0){Send(7,Bait.Get(),FVector::ZeroVector,GP->FindComponentByClass<UFPSCombatHealthComponent>()->Health);return;}
        if(Now-Began>120.){Record(TEXT("native_ai_player_attack_timeout"),false);Finish();}return;
    }
    if(Phase==101)
    {
        if(!Shrine->IsDormant())return;
        Record(TEXT("native_ai_reaches_and_disables_shrine"),Shrine->bRaidNight&&Raiders(GetWorld()).Num()>0);Send(8);return;
    }
    if(!Peer.IsValid()||Peer->Reported!=Phase)
    {if(Phase>0&&Phase<80&&Now-Began>240.){Record(TEXT("peer_response_timeout"),false,FString::Printf(TEXT("phase=%d"),Phase));Finish();}return;}
    // Each peer advances at its own time under lag/loss. Client completion does
    // not imply the host has already finished its native alignment/enter clip.
    if(Phase==3&&Peer->Passed)
    {
        FString HostState;
        if(!Seated(HP,HostState)&&Now-Began<40.)return;
    }
    Record(FString::Printf(TEXT("client_phase_%02d"),Phase),Peer->Passed,Peer->Detail);
    if(!Peer->Passed){Finish();return;}
    if(Phase==1)
    {if(!SetGroundPositions()){Record(TEXT("generated_ground_route"),false);Finish();return;}Send(2,nullptr,Point);}
    else if(Phase==2)
    {
        auto* Move=HP->GetCharacterMovement();Record(TEXT("host_world_space_generated_ground"),Move->IsMovingOnGround()&&!HP->GetMovementBase()&&FVector::Dist2D(HP->GetActorLocation(),StartPosition)>120.);
        if(!SetPewPositions()){Record(TEXT("usable_pew_entry"),false);Finish();return;}Send(3,HP,GuestAim);
    }
    else if(Phase==3)
    {
        FString Text;const auto HS=RestState(HP),GS=RestState(GP);
        const bool Both=Seated(HP,Text)&&SawEnter&&GS.Phase==3&&HS.SlotIndex!=GS.SlotIndex;
        Record(TEXT("male_and_female_native_pew_E_distinct_reservations"),Both,Text+TEXT(" ")+InteractionTrace(Host.Get(),Pew.TransformPosition(FVector(-8,-70,43.6488))));
        if(!Both){Finish();return;}
        GuestSlot=GS.SlotIndex;Peer->ClientExit();Phase=90;UE_LOG(LogTemp,Display,TEXT("HILLS_CONTINUITY_DISCONNECT_CLIENT"));
    }
    else if(Phase==4){Place(Guest.Get(),GuestSeat,GuestAim);Send(5,nullptr,GuestAim);}
    else if(Phase==5)
    {Record(TEXT("disconnect_frees_same_pew_slot"),RestState(GP).SlotIndex==GuestSlot);KeyE(Host.Get());Send(6);}
    else if(Phase==6)
    {
        Record(TEXT("host_exit_restores_movement_and_input"),SawExit&&RestState(HP).Phase==0&&HP->GetCharacterMovement()->IsMovingOnGround()&&!Host->IsMoveInputIgnored());
        Retreat(Host.Get(),Hills.Get(),0);Retreat(Guest.Get(),Hills.Get(),300);
        const float Hour=Weather->NormalizedDayTime*24.f;Weather->AdvanceGameTime(Hour<20.f?20.f-Hour:44.f-Hour);Phase=100;Began=Now;
    }
    else if(Phase==7)
    {
        auto* Health=GP->FindComponentByClass<UFPSCombatHealthComponent>();Record(TEXT("native_ai_player_damage_authority"),NativePlayerHits>0&&Health->Health<PlayerHealth,FString::Printf(TEXT("health=%.2f raider_damage_events=%d"),Health->Health,NativePlayerHits));
        GP->OnTakeAnyDamage.RemoveDynamic(this,&AHillsContinuityAudit::PlayerWasHit);
        Retreat(Guest.Get(),Hills.Get(),300);Phase=101;Began=Now;
    }
    else if(Phase==8)
    {
        // Damage/death are explicit persistence setup; the player/shrine attack
        // assertions above are exclusively the native AI's own attacks.
        auto Monsters=Raiders(GetWorld());if(Monsters.Num()>=2)
        {Monsters[0]->TakeDamage(Monsters[0]->MaxHealth*100.f,FDamageEvent(),nullptr,nullptr);Monsters[1]->TakeDamage(20.f,FDamageEvent(),nullptr,nullptr);}
        Record(TEXT("night_checkpoint_written"),Raid->Checkpoint());
        auto* Saved=Cast<UHillsNightRaidSave>(UGameplayStatics::LoadGameFromSlot(Slot(Hills.Get()),0));
        Record(TEXT("night_budget_death_and_dormancy_saved"),Saved&&Saved->Spawned==3&&Saved->Raiders.Num()==2&&Saved->ShrineHealth==0&&Saved->PortalActive);
        if(Saved)UGameplayStatics::SaveGameToSlot(Saved,TEXT("HillsContinuityReference"),0);Finish();
    }
    else if(Phase==9)
    {const float Hour=Weather->NormalizedDayTime*24.f;Weather->AdvanceGameTime(Hour<6.1f?6.1f-Hour:30.1f-Hour);Send(10);}
    else if(Phase==10)
    {
        Raid->Checkpoint();auto* Saved=Cast<UHillsNightRaidSave>(UGameplayStatics::LoadGameFromSlot(Slot(Hills.Get()),0));
        Record(TEXT("dawn_restores_and_persists_ward"),Saved&&!Saved->Night&&Saved->ShrineHealth==Saved->ShrineMaximum&&!Saved->PortalActive);Finish();
    }
}
