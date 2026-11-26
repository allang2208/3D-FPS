#include "HillsNightRaidSubsystem.h"
#include "HillsNightRaidSave.h"
#include "TemperateHillsWorld.h"
#include "ChapelShrine.h"
#include "HillsNightPortal.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/FatZombie.h"
#include "../Monsters/MonsterAIController.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationSystem.h"

bool UHillsNightRaidSubsystem::RestoreSession()
{
    if(!Hills.IsValid())for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It){Hills=*It;break;}
    if(!Weather.IsValid())for(TActorIterator<AFPSWeatherManager> It(GetWorld());It;++It){Weather=*It;break;}
    if(!Hills.IsValid()||!Hills->WorldId.IsValid()||!Weather.IsValid()||!Weather->HasActorBegunPlay())return false;
    if(!bClockRestored)
    {
        SaveSlot=TEXT("HillsNight_")+Hills->WorldId.ToString(EGuidFormats::Digits);
        PendingSave=Cast<UHillsNightRaidSave>(UGameplayStatics::LoadGameFromSlot(SaveSlot,0));
        if(PendingSave&&(PendingSave->Version!=1||PendingSave->WorldId!=Hills->WorldId||PendingSave->Seed!=Hills->Seed))
        {PendingSave=nullptr;bSaveWritable=false;UE_LOG(LogTemp,Error,TEXT("HILLS_RAID incompatible sidecar retained: %s"),*SaveSlot);}
        else if(!PendingSave&&UGameplayStatics::DoesSaveGameExist(SaveSlot,0))
        {bSaveWritable=false;UE_LOG(LogTemp,Error,TEXT("HILLS_RAID unreadable sidecar retained: %s"),*SaveSlot);}
        if(PendingSave)Weather->RestorePersistentState(PendingSave->Weather);
        else if(bSaveWritable && Hills->PlaythroughSeed) Weather->WeatherSeed=Hills->PlaythroughSeed;
        bClockRestored=true;
    }
    if(!Hills->bReady)return false;
    if(!Shrine.IsValid())for(TActorIterator<AChapelShrine> It(GetWorld());It;++It){Shrine=*It;break;}
    if(!Shrine.IsValid())return false;
    if(!bSessionReady)
    {
        if(PendingSave)
        {
            bNight=PendingSave->Night;NightSerial=PendingSave->NightSerial;
            SpawnedThisNight=FMath::Max(0,PendingSave->Spawned);WaveRemaining=FMath::Max(0,PendingSave->WaveRemaining);
            Random.Initialize(PendingSave->RandomSeed);PortalSite=PendingSave->PortalSite;PortalFacing=PendingSave->PortalFacing;
            bSiteChosen=PendingSave->SiteChosen;
            if(Hills->IsForestVillage() && (bSiteChosen || PendingSave->PortalActive))
            {
                // Older forest saves can point to a gate on the village's former hill.
                const auto& Site=Hills->GetVillageSite();
                const FVector2D Local=Site.Local(PortalSite.X,PortalSite.Y);
                const double Side=Local.X<0.?-1.:1.;
                const FVector2D Gate(Side*Site.WallHalfSize().X,Site.GateY(Side));
                if(FVector2D::DistSquared(Local,Gate)>FMath::Square(5000.))
                {
                    bSiteChosen=false;
                    PendingSave->SiteChosen=false;
                    PendingSave->PortalActive=false;
                }
            }
            Shrine->RestoreWard(PendingSave->ShrineHealth,PendingSave->ShrineMaximum,bNight);
            bClockInitialized=true;bRestorePending=true;
            UE_LOG(LogTemp,Display,TEXT("HILLS_RAID restore world=%s day=%d hour=%.4f night=%d spawned=%d remaining=%d alive=%d ward=%.1f"),
                *Hills->WorldId.ToString(),Weather->GetScheduleDay(),Weather->NormalizedDayTime*24.,NightSerial,SpawnedThisNight,WaveRemaining,PendingSave->Raiders.Num(),Shrine->Durability);
        }
        bSessionReady=true;NextCheckpoint=GetWorld()->GetTimeSeconds()+5.;
    }
    return true;
}

ANurseZombie* UHillsNightRaidSubsystem::CreateRaider(bool Heavy,const FTransform& Transform,float SavedHealth)
{
    if(!MonsterClasses.IsValidIndex(Heavy?1:0)||!Shrine.IsValid())return nullptr;
    auto* Monster=GetWorld()->SpawnActorDeferred<ANurseZombie>(MonsterClasses[Heavy?1:0],Transform,Portal.Get(),nullptr,ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding);
    if(!Monster)return nullptr;
    Monster->Tags.AddUnique(TEXT("HillsNightRaider"));Monster->AggroRadius=2200.f;
    if(Heavy)
    {auto* Move=Monster->GetCharacterMovement();Move->SetUpdateNavAgentWithOwnersCollisions(false);Move->NavAgentProps.AgentRadius=62.f;Move->NavAgentProps.AgentHeight=204.f;}
    UGameplayStatics::FinishSpawningActor(Monster,Transform);
    if(!IsValid(Monster)||Monster->IsActorBeingDestroyed())return nullptr;
    auto* AI=Cast<AMonsterAIController>(Monster->GetController());
    if(!AI){Monster->Destroy();return nullptr;}
    if(SavedHealth>=0.f)Monster->Health=FMath::Clamp(SavedHealth,.01f,Monster->MaxHealth);
    AI->SetNightRaidObjective(Shrine.Get());AI->SetEncounterArea(Shrine.Get());
    UNavigationSystemV1::RegisterNavigationInvoker(*Monster,5000,6500);Monster->ForceNetUpdate();
    return Monster;
}

bool UHillsNightRaidSubsystem::RestoreActors()
{
    if(!bRestorePending)return true;
    if(!bAssetsReady)return false;
    const double Now=GetWorld()->GetTimeSeconds();
    if(PendingSave->PortalActive&&!Portal.IsValid())
    {
        const FTransform T(PortalFacing,PortalSite);
        auto* P=GetWorld()->SpawnActorDeferred<AHillsNightPortal>(AHillsNightPortal::StaticClass(),T,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!P)return false;
        const auto* GS=GetWorld()->GetGameState();P->OpenedAt=(GS?GS->GetServerWorldTimeSeconds():Now)-FMath::Max(0.,PendingSave->PortalAge);
        UGameplayStatics::FinishSpawningActor(P,T);Portal=P;
    }
    if(RestoreIndex<PendingSave->Raiders.Num())
    {
        const auto& Saved=PendingSave->Raiders[RestoreIndex];
        if(Saved.Health<=0.f){++RestoreIndex;return false;}
        const bool Heavy=Saved.Kind==TEXT("fat");
        const auto* Defaults=MonsterClasses[Heavy?1:0]->GetDefaultObject<ANurseZombie>();
        const float Half=Defaults->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        // Keep actors pending while collision streams. Nearby attempts handle an
        // occupied saved point without clearing the saved wave or its budget.
        for(int32 I=0;I<25;++I)
        {
            const float Angle=((I-1)%8)*PI*.25f;
            FVector P=Saved.Transform.GetLocation();if(I)P+=FVector(FMath::Cos(Angle),FMath::Sin(Angle),0)*(((I-1)/8+1)*180.);
            FHitResult Floor;FCollisionQueryParams Q(SCENE_QUERY_STAT(HillsRaidRestore),false);
            // A save can catch a living raider in a knockback arc. Include the
            // generated surface below it, while preserving support on upper floors.
            const double Ground=Hills->Height(P.X,P.Y);
            const FVector Top(P.X,P.Y,FMath::Max(P.Z-Half+60.,Ground+60.));
            const FVector Bottom(P.X,P.Y,FMath::Min(P.Z-Half-350.,Ground-350.));
            if(!GetWorld()->LineTraceSingleByChannel(Floor,Top,Bottom,ECC_Visibility,Q)||Floor.ImpactNormal.Z<.5f)continue;
            P.Z=Floor.ImpactPoint.Z+Half+3.;
            if(auto* M=CreateRaider(Heavy,FTransform(Saved.Transform.GetRotation(),P,Saved.Transform.GetScale3D()),Saved.Health))
            {Raiders.Add(M);++RestoreIndex;return false;}
        }
        return false;
    }
    NextSpawn=Now+FMath::Max(0.,PendingSave->SpawnDelay);NextWave=Now+FMath::Max(0.,PendingSave->WaveDelay);
    NextPortalAttempt=Now+FMath::Max(0.,PendingSave->PortalDelay);
    bRestorePending=false;PendingSave=nullptr;Checkpoint();
    UE_LOG(LogTemp,Display,TEXT("HILLS_RAID actors restored alive=%d spawned=%d remaining=%d"),LivingCount(),SpawnedThisNight,WaveRemaining);
    return true;
}

bool UHillsNightRaidSubsystem::Checkpoint()
{
    if(!bSessionReady||!bSaveWritable||GetWorld()->GetNetMode()==NM_Client||!Hills.IsValid()||!Weather.IsValid()||!Shrine.IsValid())return false;
    auto* Save=NewObject<UHillsNightRaidSave>(this);const double Now=GetWorld()->GetTimeSeconds();
    Save->WorldId=Hills->WorldId;Save->Seed=Hills->Seed;Save->Weather=Weather->CapturePersistentState();
    Save->Night=bNight;Save->NightSerial=NightSerial;Save->Spawned=SpawnedThisNight;Save->WaveRemaining=WaveRemaining;Save->RandomSeed=Random.GetCurrentSeed();
    Save->ShrineHealth=Shrine->Durability;Save->ShrineMaximum=Shrine->MaxDurability;
    Save->SiteChosen=bSiteChosen;Save->PortalSite=PortalSite;Save->PortalFacing=PortalFacing;
    Save->PortalActive=Portal.IsValid()&&Portal->ClosedAt<0.;
    const auto* GS=GetWorld()->GetGameState();Save->PortalAge=Save->PortalActive?FMath::Max(0.,(GS?GS->GetServerWorldTimeSeconds():Now)-Portal->OpenedAt):0.;
    Save->SpawnDelay=FMath::Max(0.,NextSpawn-Now);Save->WaveDelay=FMath::Max(0.,NextWave-Now);Save->PortalDelay=FMath::Max(0.,NextPortalAttempt-Now);
    for(const auto& Raider:Raiders)if(Raider.IsValid()&&Raider->Health>0.f)
    {auto& R=Save->Raiders.AddDefaulted_GetRef();R.Kind=Raider->IsA<AFatZombie>()?TEXT("fat"):TEXT("nurse");R.Transform=Raider->GetActorTransform();R.Health=Raider->Health;}
    if(bRestorePending&&PendingSave)
    {
        for(int32 I=RestoreIndex;I<PendingSave->Raiders.Num();++I)Save->Raiders.Add(PendingSave->Raiders[I]);
        Save->SpawnDelay=PendingSave->SpawnDelay;Save->WaveDelay=PendingSave->WaveDelay;Save->PortalDelay=PendingSave->PortalDelay;
        if(PendingSave->PortalActive&&!Portal.IsValid()){Save->PortalActive=true;Save->PortalAge=PendingSave->PortalAge;}
    }
    const bool OK=UGameplayStatics::SaveGameToSlot(Save,SaveSlot,0);NextCheckpoint=Now+(OK?5.:1.);
    if(!OK)UE_LOG(LogTemp,Error,TEXT("HILLS_RAID checkpoint failed: %s"),*SaveSlot);
    return OK;
}

void UHillsNightRaidSubsystem::WorldTearingDown(UWorld* World)
{if(World==GetWorld())Checkpoint();}
