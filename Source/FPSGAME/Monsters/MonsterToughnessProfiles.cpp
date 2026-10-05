#include "MonsterToughnessProfiles.h"
#include "VortexCofferM25.h"
#include "MonsterCombatComponent.h"
#include "M10Mawcrawler.h"
#include "HangingBellM09.h"
#include "HundredEyedSlagMonster.h"
#include "FleshHandMonster.h"
#include "HandBrainMonster.h"
#include "PoisonMaggotMonster.h"
#include "InfectedDogMonster.h"
#include "WolfMonster.h"
#include "FatZombie.h"
#include "Mutant3.h"
#include "WitchMonster.h"
#include "SpitterZombie.h"
#include "BlindSupplicantMonster.h"
#include "NurseZombie.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace MonsterToughnessProfileData
{
const TCHAR* SpeciesOf(const AActor* Monster)
{
    if(Cast<AVortexCofferM25>(Monster))return TEXT("vortex_coffer_m25");
    if(Cast<AM10Mawcrawler>(Monster))return TEXT("mawcrawler_m10");
    if(Cast<AHangingBellM09>(Monster))return TEXT("hanging_bell_m09");
    if(Cast<AHundredEyedSlagMonster>(Monster))return TEXT("hundred_eyed_slag");
    if(const auto* Hand=Cast<AFleshHandMonster>(Monster))return Hand->bMinion?TEXT("small_hand"):TEXT("giant_hand");
    if(Cast<AHandBrainMonster>(Monster))return TEXT("hand_brain");
    if(Cast<APoisonMaggotMonster>(Monster))return TEXT("poison_maggot");
    if(Cast<AInfectedDogMonster>(Monster))return TEXT("infected_dog");
    if(Cast<AWolfMonster>(Monster))return TEXT("wolf");
    if(Cast<AFatZombie>(Monster)||Monster->ActorHasTag(TEXT("FatZombie")))return TEXT("fat_zombie");
    if(Cast<AMutant3>(Monster)||Monster->ActorHasTag(TEXT("Mutant3")))return TEXT("mutant3");
    if(Cast<AWitchMonster>(Monster)||Monster->ActorHasTag(TEXT("Witch")))return TEXT("witch");
    if(Cast<ASpitterZombie>(Monster)||Monster->ActorHasTag(TEXT("SpitterZombie")))return TEXT("spitter");
    if(Cast<ABlindSupplicantMonster>(Monster))return TEXT("blind_supplicant_m07");
    if(Cast<ANurseZombie>(Monster))return TEXT("nurse");
    return nullptr;
}

TSharedPtr<FJsonObject> ProfileData(AActor* Monster)
{
    // Authority-only spawn-time read, cached for this game instance (never on hit/tick).
    static TWeakObjectPtr<UGameInstance> CachedInstance;
    static TSharedPtr<FJsonObject> CachedData;
    static bool bLoaded=false;
    UGameInstance* Instance=Monster->GetWorld()->GetGameInstance();
    if(!bLoaded||CachedInstance.Get()!=Instance)
    {
        bLoaded=true;CachedInstance=Instance;CachedData.Reset();
        FString Json;
        const FString Path=FPaths::ProjectContentDir()/TEXT("ColdSteelData/monster-toughness.json");
        if(!FFileHelper::LoadFileToString(Json,*Path)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),CachedData))
            UE_LOG(LogTemp,Warning,TEXT("Monster toughness profiles unavailable: %s; using rank tier defaults"),*Path);
    }
    return CachedData;
}

TSharedPtr<FJsonObject> Child(const TSharedPtr<FJsonObject>& Parent,const TCHAR* Key)
{
    const TSharedPtr<FJsonObject>* Value=nullptr;
    return Parent&&Parent->TryGetObjectField(Key,Value)?*Value:nullptr;
}

float Number(const TSharedPtr<FJsonObject>& Object,const TCHAR* Key,float Default)
{
    double Value=Default;
    if(Object)Object->TryGetNumberField(Key,Value);
    return FMath::IsFinite(Value)?float(Value):Default;
}
}

void MonsterToughnessProfiles::Apply(AActor* Monster,EMonsterRank Rank)
{
    if(!Monster||!Monster->HasAuthority())return;
    auto* Combat=Monster->FindComponentByClass<UMonsterCombatComponent>();
    if(!Combat)return;
    const TCHAR* SpeciesKey=MonsterToughnessProfileData::SpeciesOf(Monster);
    const TCHAR* RankKey=Rank==EMonsterRank::Boss?TEXT("boss"):Rank==EMonsterRank::Lord?TEXT("lord"):
        Rank==EMonsterRank::Elite?TEXT("elite"):Rank==EMonsterRank::Minor?TEXT("minor"):TEXT("normal");
    using namespace MonsterToughnessProfileData;
    const auto Root=ProfileData(Monster);
    const auto Shared=Child(Root,TEXT("shared"));
    const auto RankData=Child(Child(Root,TEXT("ranks")),RankKey);
    const auto Species=SpeciesKey?Child(Child(Root,TEXT("species")),SpeciesKey):nullptr;
    const float RankStep=Rank==EMonsterRank::Boss?2.f:Rank==EMonsterRank::Lord?1.f:0.f;
    FMonsterToughnessBarTuning Tuning;
    const float DefaultMaximum=Rank==EMonsterRank::Boss?1000.f:Rank==EMonsterRank::Lord?600.f:Rank==EMonsterRank::Elite?200.f:0.f;
    const float RequestedMaximum=Number(Species,RankKey,Number(RankData,TEXT("default_maximum"),DefaultMaximum));
    // Zero is unarmoured; positive maxima belong to exactly five 200-point tiers.
    Tuning.Maximum=RequestedMaximum<=0.f?0.f:200.f*FMath::Clamp(FMath::RoundToInt(RequestedMaximum/200.f),1,5);
    Tuning.BrokenSeconds=FMath::Max(.1f,Number(RankData,TEXT("broken_seconds"),3.f+RankStep));
    Tuning.RefillSeconds=FMath::Max(.1f,Number(RankData,TEXT("refill_seconds"),4.f+2.f*RankStep));
    Tuning.InitialStaggerSeconds=FMath::Clamp(Number(RankData,TEXT("initial_stagger_seconds"),1.f+.1f*RankStep),.1f,Tuning.BrokenSeconds);
    Tuning.RegenDelaySeconds=FMath::Max(0.f,Number(Shared,TEXT("regen_delay_seconds"),3.f));
    Tuning.RegenFractionPerSecond=FMath::Clamp(Number(Shared,TEXT("regen_fraction_per_second"),.1f),0.f,1.f);
    Tuning.HitStaggerSeconds=FMath::Clamp(Number(Shared,TEXT("hit_stagger_seconds"),.2f),.15f,.25f);
    Tuning.HitIntervalSeconds=FMath::Max(.01f,Number(Shared,TEXT("hit_interval_seconds"),.15f));
    Combat->ConfigureToughnessBar(Tuning);
}
