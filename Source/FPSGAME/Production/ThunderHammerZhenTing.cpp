#include "ThunderHammerZhenTing.h"
#include "ThunderHammerTuning.h"
#include "WarhammerShockwave.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "TimerManager.h"

DEFINE_LOG_CATEGORY_STATIC(LogThunderHammerZhenTing,Log,All);

bool ThunderHammerZhenTing::Installed(const FColdSteelItem* Item)
{
    if(!Item||Item->Definition!=ThunderHammer::Definition)return false;
    const auto Data=ColdSteelItemData::Read(Item->Data);
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Selected;
    if(Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts))
        (*Parts)->TryGetStringField(TEXT("pommel"),Selected);
    return Selected==Pommel;
}

void ThunderHammerZhenTing::Commit(FColdSteelSkillShot& Shot,const FColdSteelItem* Item,const FVector& Forward)
{
    Shot.ZhenTingForward=Installed(Item)?Forward.GetSafeNormal2D():FVector::ZeroVector;
    UE_LOG(LogThunderHammerZhenTing,Verbose,TEXT("Commit weapon=%s installed=%d direction=%s"),Item?*Item->Definition:TEXT("none"),!Shot.ZhenTingForward.IsNearlyZero(),*Shot.ZhenTingForward.ToCompactString());
}

void ThunderHammerZhenTing::ContinueLightning(AWarhammerShockwave* Origin,const FColdSteelSkillShot& Shot,float Radius,float Magic,bool ThunderCall)
{
    if(!Origin||!Origin->HasAuthority()||Shot.ZhenTingForward.IsNearlyZero())return;
    UE_LOG(LogThunderHammerZhenTing,Verbose,TEXT("Continue origin=%s source=%s direction=%s magic=%.2f"),*Origin->GetActorLocation().ToCompactString(),*GetNameSafe(Origin->GetOwner()),*Shot.ZhenTingForward.ToCompactString(),Magic);
    auto* World=Origin->GetWorld();const FVector Forward=Shot.ZhenTingForward.GetSafeNormal2D();
    FVector Ground=Origin->GetActorLocation();const FVector Start=Ground;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ZhenTingGround),false,Origin->GetOwner());
    Query.AddIgnoredActor(Origin);
    // Bodies do not become stepping stones or block the continuation's floor probe.
    const auto Trace=[&](const FVector& A,const FVector& B,FHitResult& Hit)
    {
        for(int32 Pass=0;Pass<32;++Pass)
        {
            if(!World->LineTraceSingleByChannel(Hit,A,B,ECC_Visibility,Query))return false;
            auto* Actor=Hit.GetActor();
            if(Actor&&(Actor->IsA<APawn>()||Actor->FindComponentByClass<UMonsterCombatComponent>()))
            {Query.AddIgnoredActor(Actor);continue;}
            return true;
        }
        Hit=FHitResult();return true; // Too many bodies: stop rather than treating a body as terrain.
    };
    // Each new wave contains only the relevant lightning receipt. It cannot
    // repeat physical slam damage or recursively produce another three waves.
    auto Lightning=Shot;Lightning.ZhenTingForward=FVector::ZeroVector;Lightning.DamagePanel={};
    const float Spacing=Radius*2.f;
    const int32 Steps=FMath::Max(1,FMath::CeilToInt(Spacing/100.f));
    for(int32 Strike=1;Strike<=3;++Strike)
    {
        for(int32 Step=1;Step<=Steps;++Step)
        {
            FVector Candidate=Start+Forward*(Spacing*(float(Strike-1)+float(Step)/Steps));
            Candidate.Z=Ground.Z;
            FHitResult Wall,Floor;
            if(Trace(Ground+FVector(0,0,50),Candidate+FVector(0,0,50),Wall))
            {UE_LOG(LogThunderHammerZhenTing,Verbose,TEXT("Blocked strike=%d step=%d actor=%s point=%s"),Strike,Step,*GetNameSafe(Wall.GetActor()),*Wall.ImpactPoint.ToCompactString());return;}
            if(!Trace(Candidate+FVector(0,0,120),Candidate-FVector(0,0,220),Floor)||Floor.ImpactNormal.Z<.5f)
            {UE_LOG(LogThunderHammerZhenTing,Verbose,TEXT("No floor strike=%d step=%d actor=%s normal=%s"),Strike,Step,*GetNameSafe(Floor.GetActor()),*Floor.ImpactNormal.ToCompactString());return;}
            Ground=Floor.ImpactPoint;
            if(Step!=Steps)continue;
            // Keep the committed landing points and damage; the short-lived
            // original wave must not own the timers for the later strikes.
            auto* Source=Origin->GetOwner();if(!Source)return;
            const TWeakObjectPtr<APawn> Instigator=Origin->GetInstigator();
            const FVector Impact=Ground+Floor.ImpactNormal*2.f;
            const FRotator Rotation=FRotationMatrix::MakeFromZ(Floor.ImpactNormal).Rotator();
            FTimerHandle Timer;
            World->GetTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(Source,
                [Source,Instigator,Impact,Rotation,Lightning,Radius,Magic,ThunderCall]()
                {
                    auto* StrikeWorld=Source->GetWorld();if(!StrikeWorld)return;
                    FActorSpawnParameters Params;Params.Owner=Source;Params.Instigator=Instigator.Get();
                    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
                    if(auto* Wave=StrikeWorld->SpawnActor<AWarhammerShockwave>(Impact,Rotation,Params))
                    {Wave->Setup(Lightning,Radius,ThunderHammer::StunSeconds,Magic,ThunderCall);UE_LOG(LogThunderHammerZhenTing,Verbose,TEXT("Released %s at %s"),*Wave->GetName(),*Impact.ToCompactString());}
                }),float(Strike)*.25f,false);
            UE_LOG(LogThunderHammerZhenTing,Verbose,TEXT("Scheduled strike=%d delay=%.2f point=%s"),Strike,float(Strike)*.25f,*Impact.ToCompactString());
        }
    }
}
