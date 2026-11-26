#include "FPSSurvivalComponent.h"
#include "../FPSWeatherManager.h"
#include "EngineUtils.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Building/ColdSteelCampfire.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Movement/FPSFurnitureRestComponent.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../UI/StatusEffectsComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void FFPSSurvivalState::Normalize()
{
    auto Max=[](float V){return FMath::IsFinite(V)&&V>0.f?V:100.f;};
    auto Value=[](float V,float Limit){return FMath::IsFinite(V)?FMath::Clamp(V,0.f,Limit):Limit;};
    MaxHunger=Max(MaxHunger);MaxHydration=Max(MaxHydration);MaxSanity=Max(MaxSanity);
    Hunger=Value(Hunger,MaxHunger);Hydration=Value(Hydration,MaxHydration);Sanity=Value(Sanity,MaxSanity);
    DeprivationSeconds=FMath::IsFinite(DeprivationSeconds)?FMath::Clamp(DeprivationSeconds,0.f,.999999f):0.f;
    if(!IsDeprived())DeprivationSeconds=0.f;
    FountainBlessingSeconds=FMath::IsFinite(FountainBlessingSeconds)?FMath::Clamp(FountainBlessingSeconds,0.f,FountainBlessingDuration):0.f;
    SausageRecoverySeconds=FMath::IsFinite(SausageRecoverySeconds)?FMath::Clamp(SausageRecoverySeconds,0.f,SausageRecoveryDuration):0.f;
    LargeLambMealSeconds=FMath::IsFinite(LargeLambMealSeconds)?FMath::Clamp(LargeLambMealSeconds,0.f,LargeLambMealDuration):0.f;
}

UFPSSurvivalComponent::UFPSSurvivalComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickInterval=.25f;
    SetIsReplicatedByDefault(true);
}

double UFPSSurvivalComponent::ServerTime() const
{
    const auto* World=GetWorld();if(!World)return 0.;
    const auto* GameState=World->GetGameState();
    return GameState?GameState->GetServerWorldTimeSeconds():World->GetTimeSeconds();
}

float UFPSSurvivalComponent::FoodRecoveryRemaining(float SavedSeconds,double EndsAt,float Duration) const
{
    // Both peers read the server deadline. Only authority sets it; profile saves
    // capture remaining gameplay time, never an absolute time from another World.
    const auto* Health=GetOwner()?GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(Health&&Health->IsDead())return SavedSeconds;
    return float(FMath::Clamp(EndsAt-ServerTime(),0.,double(Duration)));
}

float UFPSSurvivalComponent::SausageRecoveryRemaining() const
{
    return FoodRecoveryRemaining(State.SausageRecoverySeconds,SausageRecoveryEndsAt,FFPSSurvivalState::SausageRecoveryDuration);
}

float UFPSSurvivalComponent::LargeLambMealRemaining() const
{
    return FoodRecoveryRemaining(State.LargeLambMealSeconds,LargeLambMealEndsAt,FFPSSurvivalState::LargeLambMealDuration);
}

FFPSSurvivalState UFPSSurvivalComponent::GetState() const
{
    auto Result=State;Result.SausageRecoverySeconds=SausageRecoveryRemaining();Result.LargeLambMealSeconds=LargeLambMealRemaining();return Result;
}

void UFPSSurvivalComponent::OnRep_SausageRecoveryClock()
{
    UStatusEffectsComponent::Notify(GetOwner());
}

void UFPSSurvivalComponent::OnRep_LargeLambMealClock()
{
    UStatusEffectsComponent::Notify(GetOwner());
}

void UFPSSurvivalComponent::LoadTuning()
{
    // Load this tiny read-only catalog once per process, never from the HUD or integration loop.
    static const TSharedPtr<FJsonObject> Config=[](){
        FString Json;TSharedPtr<FJsonObject> Root;
        if(FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/survival.json"))))
            FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root);
        return Root;
    }();
    if(!Config)return;
    auto Read=[&](const TCHAR* Key,float& Value){double N;if(Config->TryGetNumberField(Key,N)&&FMath::IsFinite(N)&&N>=0.)Value=static_cast<float>(N);};
    Read(TEXT("hungerPerSecond"),HungerPerSecond);Read(TEXT("hydrationPerSecond"),HydrationPerSecond);
    Read(TEXT("dungeonSanityPerSecond"),DungeonSanityPerSecond);Read(TEXT("monsterSanityMultiplier"),MonsterSanityMultiplier);
    Read(TEXT("bedRestSanityPerSecond"),BedRestSanityPerSecond);
    auto Table=[&](const TCHAR* Key,TMap<FName,float>& Out){
        const TSharedPtr<FJsonObject>* Values=nullptr;
        if(Config->TryGetObjectField(Key,Values)&&Values&&Values->IsValid())
            for(const auto& Pair:(*Values)->Values){double N;if(Pair.Value->TryGetNumber(N)&&FMath::IsFinite(N)&&N>=0.)Out.Add(FName(*Pair.Key),static_cast<float>(N));}
    };
    Table(TEXT("monsterSanityLossByTag"),MonsterSanityLossByTag);
    Table(TEXT("monsterSanityLossByClass"),MonsterSanityLossByClass);
}

void UFPSSurvivalComponent::BeginPlay()
{
    Super::BeginPlay();LoadTuning();State.Normalize();
    if(!GetOwner()->HasAuthority())SetComponentTickEnabled(false);
    else NaturalConsumptionSeconds(0.f);
}

float UFPSSurvivalComponent::NaturalConsumptionSeconds(float DeltaTime)
{
    if(!NaturalClock.IsValid())
    {
        const double Now=GetWorld()->GetTimeSeconds();
        if(Now<ClockResolveAfter)return DeltaTime;
        ClockResolveAfter=Now+1.;
        for(TActorIterator<AFPSWeatherManager> It(GetWorld());It;++It)
        {
            NaturalClock=*It;LastNaturalDays=It->GetNaturalDayProgress();
            AddTickPrerequisiteActor(*It);
            return float(DeltaTime*It->GetNaturalDayRate()*2160.);
        }
        // Isolated worlds without the gameplay GameMode retain the reference rate.
        return DeltaTime;
    }
    const double Days=NaturalClock->GetNaturalDayProgress();
    const double Elapsed=FMath::Max(0.,Days-LastNaturalDays);LastNaturalDays=Days;
    return float(Elapsed*2160.);
}

void UFPSSurvivalComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(UFPSSurvivalComponent,State,COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UFPSSurvivalComponent,SausageRecoveryEndsAt,COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(UFPSSurvivalComponent,LargeLambMealEndsAt,COND_OwnerOnly);
}

void UFPSSurvivalComponent::RestoreState(const FFPSSurvivalState& Saved)
{
    if(!GetOwner()||!GetOwner()->HasAuthority())return;
    const bool WasBlessed=State.FountainBlessingSeconds>0.f;
    const float PreviousSausageSeconds=State.SausageRecoverySeconds;
    const float PreviousLargeLambSeconds=State.LargeLambMealSeconds;
    const bool WasDepleted=State.IsSanityDepleted();
    State=Saved;State.Normalize();HungerIntegrationRemainder=HydrationIntegrationRemainder=0.;
    SausageRecoveryEndsAt=State.SausageRecoverySeconds>0.f?ServerTime()+State.SausageRecoverySeconds:0.;
    LargeLambMealEndsAt=State.LargeLambMealSeconds>0.f?ServerTime()+State.LargeLambMealSeconds:0.;
    if(PreviousSausageSeconds!=State.SausageRecoverySeconds||PreviousLargeLambSeconds!=State.LargeLambMealSeconds)
    {GetOwner()->ForceNetUpdate();UStatusEffectsComponent::Notify(GetOwner());}
    NotifySanityChange(WasDepleted);
    if(WasBlessed!=(State.FountainBlessingSeconds>0.f))UStatusEffectsComponent::Notify(GetOwner());
}

void UFPSSurvivalComponent::OnRep_State(const FFPSSurvivalState& Previous)
{
    NotifySanityChange(Previous.IsSanityDepleted());
    if((Previous.FountainBlessingSeconds>0.f)!=(State.FountainBlessingSeconds>0.f)||
       (Previous.SausageRecoverySeconds>0.f)!=(State.SausageRecoverySeconds>0.f)||
       (Previous.LargeLambMealSeconds>0.f)!=(State.LargeLambMealSeconds>0.f))
        UStatusEffectsComponent::Notify(GetOwner());
}

void UFPSSurvivalComponent::NotifySanityChange(bool bWasDepleted)
{
    if(bWasDepleted==State.IsSanityDepleted())return;
    if(auto* Model=ColdSteelAuthority::ForPawn(Cast<APawn>(GetOwner())))Model->SetSurvivalState(State,GetOwner());
    if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();
    UStatusEffectsComponent::Notify(GetOwner());
}

bool UFPSSurvivalComponent::DrinkBlessedWater()
{
    if(!GetOwner()||!GetOwner()->HasAuthority())return false;
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!Health||Health->IsDead())return false;
    RestoreResources(0.f,State.MaxHydration,0.f);
    State.FountainBlessingSeconds=FFPSSurvivalState::FountainBlessingDuration;
    GetOwner()->ForceNetUpdate();
    UStatusEffectsComponent::Notify(GetOwner());
    return true;
}

void UFPSSurvivalComponent::RestoreResources(float Food,float Water,float Sanity)
{
    if(!GetOwner()||!GetOwner()->HasAuthority())return;
    const bool WasDepleted=State.IsSanityDepleted();
    if(FMath::IsFinite(Food)&&Food!=0.f){State.Hunger=FMath::Clamp(State.Hunger+Food,0.f,State.MaxHunger);HungerIntegrationRemainder=0.;}
    if(FMath::IsFinite(Water)&&Water!=0.f){State.Hydration=FMath::Clamp(State.Hydration+Water,0.f,State.MaxHydration);HydrationIntegrationRemainder=0.;}
    if(FMath::IsFinite(Sanity))State.Sanity=FMath::Clamp(State.Sanity+Sanity,0.f,State.MaxSanity);
    if(!State.IsDeprived())State.DeprivationSeconds=0.f;
    NotifySanityChange(WasDepleted);
}

void UFPSSurvivalComponent::ApplySanityDamage(float BaseLoss,float Coefficient)
{
    if(!GetOwner()||!GetOwner()->HasAuthority()||!FMath::IsFinite(BaseLoss)||!FMath::IsFinite(Coefficient)||BaseLoss<=0.f||Coefficient<=0.f)return;
    const bool WasDepleted=State.IsSanityDepleted();
    State.Sanity=FMath::Max(0.f,State.Sanity-BaseLoss*Coefficient);
    NotifySanityChange(WasDepleted);
}

void UFPSSurvivalComponent::ApplySanityAttack(AActor* Attacker)
{
    if(!Attacker)return;
    float Loss=0.f;
    // A projectile inherits its owning monster's tuning. Matching entries use the largest value.
    for(int32 Depth=0;Attacker&&Depth<4;++Depth,Attacker=Attacker->GetOwner())
    {
        for(const FName Tag:Attacker->Tags)Loss=FMath::Max(Loss,MonsterSanityLossByTag.FindRef(Tag));
        Loss=FMath::Max(Loss,MonsterSanityLossByClass.FindRef(Attacker->GetClass()->GetFName()));
    }
    ApplySanityDamage(Loss,MonsterSanityMultiplier);
}

void UFPSSurvivalComponent::TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime,TickType,ThisTickFunction);
    const auto* Pawn=Cast<APawn>(GetOwner());
    auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!Pawn||!Pawn->HasAuthority()||!Pawn->IsPlayerControlled()||!Health||!FMath::IsFinite(DeltaTime)||DeltaTime<=0.f||GetWorld()->IsPaused())return;
    // Sample even while dead so revival never pays for skipped calendar time.
    const float NaturalTimeScale=NaturalConsumptionSeconds(DeltaTime)/DeltaTime;
    if(Health->IsDead())
    {
        // Match the existing fountain-blessing pause while awaiting revival.
        // Death respawn still resets the entire survival state in AttachPawn.
        SausageRecoveryEndsAt=State.SausageRecoverySeconds>0.f?ServerTime()+State.SausageRecoverySeconds:0.;
        LargeLambMealEndsAt=State.LargeLambMealSeconds>0.f?ServerTime()+State.LargeLambMealSeconds:0.;
        return;
    }
    const bool WasDepleted=State.IsSanityDepleted();
    const auto* Run=UDungeonRunSubsystem::Get(GetWorld());
    const auto* Rest=Pawn->FindComponentByClass<UFPSFurnitureRestComponent>();
    const float RecoveryRate=Rest&&Rest->IsRestingInBed()?BedRestSanityPerSecond:0.f;
    const float SanityRate=(Run&&Run->IsRunActive()?DungeonSanityPerSecond:0.f)-RecoveryRate;
    // Positive recovery lifts SAN off zero, so the depletion multiplier no
    // longer applies during this interval. Existing dungeon drain still stacks.
    const float DepletedAt=SanityRate<0.f?TNumericLimits<float>::Max():
        WasDepleted?0.f:SanityRate>0.f?State.Sanity/SanityRate:TNumericLimits<float>::Max();
    // Split at blessing expiry and SAN depletion so both multipliers compose
    // during a hitch, without advancing the starvation clock before depletion.
    const float PreviousSausageSeconds=State.SausageRecoverySeconds;
    const float PreviousLargeLambSeconds=State.LargeLambMealSeconds;
    State.SausageRecoverySeconds=SausageRecoveryRemaining();
    if(State.SausageRecoverySeconds<=0.f)SausageRecoveryEndsAt=0.;
    if(PreviousSausageSeconds>0.f&&State.SausageRecoverySeconds<=0.f)UStatusEffectsComponent::Notify(GetOwner());
    State.LargeLambMealSeconds=LargeLambMealRemaining();
    if(State.LargeLambMealSeconds<=0.f)LargeLambMealEndsAt=0.;
    if(PreviousLargeLambSeconds>0.f&&State.LargeLambMealSeconds<=0.f)UStatusEffectsComponent::Notify(GetOwner());
    const float BlessedTime=FMath::Min(DeltaTime,State.FountainBlessingSeconds);
    const float SanityTime=FMath::Min(DeltaTime,DepletedAt);
    const float Boundaries[]={FMath::Min(BlessedTime,SanityTime),FMath::Max(BlessedTime,SanityTime),DeltaTime};
    const float CampfireRate=AColdSteelCampfire::ConsumptionMultiplierAt(Pawn);
    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const float EquipmentRate=Profile?float(Profile->SetEffect(TEXT("survivalConsumption"))):1.f;
    const auto RateMultiplier=[BlessedTime,DepletedAt,CampfireRate,NaturalTimeScale,EquipmentRate](float Time)
    {return NaturalTimeScale*CampfireRate*EquipmentRate*(Time<BlessedTime?.9f:1.f)*(Time>=DepletedAt?2.f:1.f);};
    float ConsumptionTime=0.f,Start=0.f;
    for(const float End:Boundaries)
    {ConsumptionTime+=(End-Start)*RateMultiplier((Start+End)*.5f);Start=End;}
    const auto EmptyAt=[&](float Resource,float Rate)
    {
        if(Resource<=0.f)return 0.f;
        if(Rate<=0.f)return TNumericLimits<float>::Max();
        float Left=Resource,Beginning=0.f;
        for(const float End:Boundaries)
        {
            const float EffectiveRate=Rate*RateMultiplier((Beginning+End)*.5f);
            const float Loss=EffectiveRate*(End-Beginning);
            if(Left<=Loss)return Beginning+Left/EffectiveRate;
            Left-=Loss;Beginning=End;
        }
        return TNumericLimits<float>::Max();
    };
    const float FoodTime=EmptyAt(State.Hunger,HungerPerSecond);
    const float WaterTime=EmptyAt(State.Hydration,HydrationPerSecond);
    const float EmptyTime=FMath::Min(FoodTime,WaterTime);
    // Float replication/save values remain unchanged. Compensate rounding so
    // 8640 quarter-second steps do not leave a positive tail after a full day.
    const auto ConsumeResource=[ConsumptionTime](float Value,float Rate,double& Remainder)
    {
        const double Exact=FMath::Max(0.,double(Value)+Remainder-double(Rate)*ConsumptionTime);
        // The stored rate is float too; discard a tail below one 100-point
        // resource's float resolution instead of delaying zero by another tick.
        const float Next=Exact<1.e-5?0.f:float(Exact);
        Remainder=Next>0.f?Exact-double(Next):0.;return Next;
    };
    State.Hunger=ConsumeResource(State.Hunger,HungerPerSecond,HungerIntegrationRemainder);
    State.Hydration=ConsumeResource(State.Hydration,HydrationPerSecond,HydrationIntegrationRemainder);
    State.FountainBlessingSeconds=FMath::Max(0.f,State.FountainBlessingSeconds-DeltaTime);
    if(BlessedTime>0.f&&State.FountainBlessingSeconds<=0.f)UStatusEffectsComponent::Notify(GetOwner());
    State.Sanity=FMath::Clamp(State.Sanity-SanityRate*DeltaTime,0.f,State.MaxSanity);
    NotifySanityChange(WasDepleted);
    if(State.IsDeprived())
    {
        State.DeprivationSeconds+=FMath::Max(0.f,DeltaTime-EmptyTime);
        while(State.DeprivationSeconds>=1.f&&!Health->IsDead())
        {
            State.DeprivationSeconds-=1.f;
            Health->ApplySurvivalDamage(Health->MaxHealth*.1f);
        }
    }
    else State.DeprivationSeconds=0.f;
}
