#include "FPSRiftSlashProjectile.h"
#include "FPSMeleeLightningComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Combat/WeaponDamageTypes.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

AFPSRiftSlashProjectile::AFPSRiftSlashProjectile()
{
    PrimaryActorTick.bCanEverTick=true;
    Root=CreateDefaultSubobject<USceneComponent>(TEXT("FlightRoot"));SetRootComponent(Root);
    Blade=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("CrescentEdge"));Blade->SetupAttachment(Root);
    Wake=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("EnergyWake"));Wake->SetupAttachment(Root);
    for(auto* Part:{Blade.Get(),Wake.Get()})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);
        Part->SetCanEverAffectNavigation(false);Part->bReceivesDecals=false;
        Part->SetVisibleInRayTracing(false);
    }
    Motes=CreateDefaultSubobject<UNiagaraComponent>(TEXT("CrescentMotes"));Motes->SetupAttachment(Root);
    Motes->SetAutoActivate(false);Motes->SetCanEverAffectNavigation(false);
}

void AFPSRiftSlashProjectile::Launch(const FTransform& Aim,float Damage,float RangeCM,float SpeedCM,
    const FColdSteelSkillShot& Snapshot,UStaticMesh* Mesh,UMaterialInterface* Material,UNiagaraSystem* Particles,USoundBase* HitSound)
{
    Direction=Aim.GetUnitAxis(EAxis::X);HitDamage=Damage;Remaining=RangeCM;Speed=SpeedCM;Shot=Snapshot;
    ImpactSound=HitSound;
    // Secondary sword damage cannot recursively produce more enchantment attacks.
    // Keep this release's typed damage, critical chance, penetration and mastery.
    Shot.ShatterRadiusCM=0.f;Shot.ElectrifiedRadiusCM=0.f;Shot.ElectrifiedMinLevel=0;
    Shot.ExtraMasteryExperience=0;Shot.WeakpointPercent=0.f;
    SetActorLocationAndRotation(Aim.GetLocation(),Aim.GetRotation()*FQuat(FVector::ForwardVector,FMath::DegreesToRadians(-18.f)));
    if(Mesh&&Material)
    {
        Blade->SetStaticMesh(Mesh);Wake->SetStaticMesh(Mesh);
        BladeMaterial=UMaterialInstanceDynamic::Create(Material,this);
        WakeMaterial=UMaterialInstanceDynamic::Create(Material,this);
        Blade->SetMaterial(0,BladeMaterial);Wake->SetMaterial(0,WakeMaterial);
        WakeMaterial->SetScalarParameterValue(TEXT("Layer"),1.f);
        Wake->SetRelativeLocation(FVector(-14,0,0));Wake->SetRelativeScale3D(FVector(2.1,1.025,1.06));
        BladeMaterial->SetScalarParameterValue(TEXT("Opacity"),0.f);
        WakeMaterial->SetScalarParameterValue(TEXT("Opacity"),0.f);
    }
    if(Particles){Motes->SetAsset(Particles);Motes->Activate(true);}
    SetLifeSpan(RangeCM/FMath::Max(1.f,SpeedCM)+.3f);
    // The first flight tick sweeps from the aim origin, so a nearby wall is
    // never skipped. Damage also stays outside the sword's release callback.
}

void AFPSRiftSlashProjectile::Advance(float Distance)
{
    if(bFinished||Distance<=0.f)return;
    const FVector Start=GetActorLocation(),End=Start+Direction*Distance;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RiftSlashFlight),false,GetOwner());Query.AddIgnoredActor(this);
    TArray<FHitResult> Contacts;
    float WallTime=1.f;bool bWall=false;
    // Channel queries return only as far as their first blocking component.
    // Repeat past each body, retaining the nearest real wall for the whole wave.
    for(;;)
    {
        TArray<FHitResult> Hits;bool bPastBody=false;
        GetWorld()->SweepMultiByChannel(Hits,Start,End,GetActorQuat(),ECC_Visibility,
            FCollisionShape::MakeBox(FVector(6.f,88.f,36.f)),Query);
        for(const FHitResult& Hit:Hits)
        {
            AActor* Target=Hit.GetActor();
            const bool bBody=Target&&(Target->IsA<APawn>()||Target->FindComponentByClass<UMonsterCombatComponent>());
            if(bBody)
            {
                Query.AddIgnoredActor(Target);bPastBody|=Hit.bBlockingHit;
                if(UFPSMeleeLightningComponent::IsEnemy(Target,GetOwner())&&!HitActors.Contains(Target))Contacts.Add(Hit);
            }
            else if(Hit.bBlockingHit){bWall=true;WallTime=FMath::Min(WallTime,Hit.Time);}
        }
        if(!bPastBody)break;
    }
    Contacts.Sort([](const FHitResult& A,const FHitResult& B){return A.Time<B.Time;});
    for(const FHitResult& Hit:Contacts)
    {
        AActor* Target=Hit.GetActor();
        if((bWall&&Hit.Time>=WallTime)||HitActors.Contains(Target)||!UFPSMeleeLightningComponent::IsEnemy(Target,GetOwner()))continue;
        HitActors.Add(Target);
        FWeaponDamageResult DamageResult;
        const float Applied=ColdSteelSkills::ApplyHit(GetOwner(),Hit,HitDamage,Direction,Shot,&DamageResult);
        if(Applied>0.f)
        {
            HitGlow=1.f;
            // Capture the releasing sword's cue, just like its damage snapshot.
            // A weapon swap must not change feedback from a wave already in flight.
            if(ImpactSound)UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Hit.ImpactPoint,.90f,.85f);
            if(auto* Character=Cast<AFPSGAMECharacter>(GetOwner()))
                Character->NotifyConfirmedWeaponHit(Target,Applied,&DamageResult);
        }
    }
    SetActorLocation(FMath::Lerp(Start,End,WallTime));Remaining-=Distance*WallTime;
    if(bWall||Remaining<=UE_KINDA_SMALL_NUMBER)FinishFlight();
}

void AFPSRiftSlashProjectile::FinishFlight()
{
    if(bFinished)return;
    bFinished=true;FadeAge=0.f;Motes->Deactivate();
}

void AFPSRiftSlashProjectile::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!IsValid(GetOwner())){Destroy();return;}
    Age+=DeltaSeconds;HitGlow=FMath::Max(0.f,HitGlow-DeltaSeconds*12.f);
    if(!bFinished)Advance(FMath::Min(Remaining,Speed*DeltaSeconds));
    else FadeAge+=DeltaSeconds;
    const float Fade=bFinished?1.f-FMath::SmoothStep(0.f,.20f,FadeAge):1.f;
    const float Alpha=FMath::SmoothStep(0.f,.05f,Age)*Fade;
    for(auto* Material:{BladeMaterial.Get(),WakeMaterial.Get()})if(Material)
    {
        Material->SetScalarParameterValue(TEXT("Age"),Age);
        Material->SetScalarParameterValue(TEXT("Opacity"),Alpha);
        Material->SetScalarParameterValue(TEXT("Dissolve"),bFinished?1.f-Fade:0.f);
        Material->SetScalarParameterValue(TEXT("HitGlow"),HitGlow);
    }
    if(bFinished&&FadeAge>=.20f){Motes->DeactivateImmediate();Destroy();}
}
