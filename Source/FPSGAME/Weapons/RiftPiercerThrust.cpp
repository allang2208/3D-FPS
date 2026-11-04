#include "RiftPiercerThrust.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Combat/WeaponDamageTypes.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"
#include "FPSMeleeLightningComponent.h"
#include "JingangRuneComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Net/UnrealNetwork.h"

namespace RiftPiercerFX
{
    constexpr int32 MoteCount=48;
    constexpr float Hold=.30f,Fade=.22f,Lifetime=Hold+Fade;
    constexpr float HalfWidth=48.f,HalfThickness=15.f;
    const TCHAR* Material=TEXT("/Game/Weapons/FrostCrystalSword20260915/RiftPiercer20261102/M_RiftPiercer_Phantom.M_RiftPiercer_Phantom");
    const TCHAR* Mote=TEXT("/Game/Weapons/FrostCrystalSword20260915/RiftPiercer20261102/SM_RiftPiercer_Mote.SM_RiftPiercer_Mote");
    const TCHAR* MoteMaterial=TEXT("/Game/Weapons/FrostCrystalSword20260915/RiftPiercer20261102/M_RiftPiercer_Mote.M_RiftPiercer_Mote");
}
ARiftPiercerThrust::ARiftPiercerThrust()
{
    PrimaryActorTick.bCanEverTick=true;bReplicates=true;SetReplicateMovement(false);
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("ReleaseHilt")));
    Blade=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FullLengthBlade"));Blade->SetupAttachment(RootComponent);
    Motes=CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("EdgeBurst"));Motes->SetupAttachment(RootComponent);
    Motes->NumCustomDataFloats=1;
    for(auto* Part:TArray<UStaticMeshComponent*>{Blade.Get(),Motes.Get()})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);
        Part->SetCanEverAffectNavigation(false);Part->SetVisibleInRayTracing(false);Part->bReceivesDecals=false;
    }
}
double ARiftPiercerThrust::Clock() const
{
    const auto* State=GetWorld()->GetGameState();return State?State->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
}
void ARiftPiercerThrust::Activate(const FRiftPiercerThrustState& State,float ThirdDamage,const FColdSteelSkillShot& Snapshot,bool CosmeticOnly)
{
    if(CosmeticOnly)SetReplicates(false);
    NetState=State;NetState.StartedAt=Clock();SetActorTransform(NetState.HiltFrame);
    auto Shot=Snapshot;
    // Ordinary thrust poise is damage-derived. Damage x2 already supplies poise x2.
    Shot.AttackMeta=0x43;Shot.MeleeDamagePhase=1;Shot.bRisingDragonFinisher=false;
    Shot.ShatterRadiusCM=0;Shot.ElectrifiedRadiusCM=0;Shot.ElectrifiedMinLevel=0;
    Shot.ExtraMasteryExperience=0;Shot.WeakpointPercent=0;Shot.TimeSandEchoRatio=0;
    Shot.AzureDragonMagicDamage*=2.f;
    // One full-segment query on release, including cover. Tick never applies damage.
    ResolveThrust(ThirdDamage*2.f,Shot,!CosmeticOnly&&GetOwner()&&GetOwner()->HasAuthority());
    bInitialized=true;LoadVisuals();SetLifeSpan(RiftPiercerFX::Lifetime+.1f);
    if(!CosmeticOnly)ForceNetUpdate();
}
void ARiftPiercerThrust::LoadVisuals()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const auto* Pawn=Cast<APawn>(GetOwner());
    const bool HidePredicted=GetNetMode()==NM_Client&&GetIsReplicated()&&NetState.bOwnerPredicted&&Pawn&&Pawn->IsLocallyControlled();
    TArray<FSoftObjectPath> Paths;
    if(!HidePredicted)Paths={NetState.Blade,FSoftObjectPath(RiftPiercerFX::Material),FSoftObjectPath(RiftPiercerFX::Mote),FSoftObjectPath(RiftPiercerFX::MoteMaterial)};
    if(NetState.HitSound.IsValid())Paths.Add(NetState.HitSound);
    if(!Paths.ContainsByPredicate([](const FSoftObjectPath& Path){return !Path.ResolveObject();}))
    {SetupVisuals();return;} // Equipped assets already resident: show on this release frame.
    VisualLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this](){SetupVisuals();}));
}
void ARiftPiercerThrust::SetupVisuals()
{
    Age=float(FMath::Max(0.,Clock()-NetState.StartedAt));
    if(!bImpactCuesPlayed)if(auto* Cue=Cast<USoundBase>(NetState.HitSound.ResolveObject()))
    {
        bImpactCuesPlayed=true;
        for(const auto& Point:NetState.ImpactPoints)UGameplayStatics::PlaySoundAtLocation(this,Cue,Point,.95f,.80f);
    }
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(GetNetMode()==NM_Client&&GetIsReplicated()&&NetState.bOwnerPredicted&&Pawn&&Pawn->IsLocallyControlled())return;
    if(Age>=RiftPiercerFX::Lifetime)return;
    auto* Mesh=Cast<UStaticMesh>(NetState.Blade.ResolveObject());
    auto* Surface=Cast<UMaterialInterface>(FSoftObjectPath(RiftPiercerFX::Material).ResolveObject());
    if(!Mesh||!Surface)return;
    Blade->SetStaticMesh(Mesh);BladeMID=UMaterialInstanceDynamic::Create(Surface,this);
    for(int32 Slot=0;Slot<Blade->GetNumMaterials();++Slot)Blade->SetMaterial(Slot,BladeMID);
    const FBox Bounds=Mesh->GetBoundingBox();Length=NetState.Reach;
    // Root stays at the release hilt. The actual mesh tip reaches the whole segment immediately.
    BladeScale=FVector(RiftPiercerFX::HalfWidth/FMath::Max(.1f,float(Bounds.GetExtent().X)),
        RiftPiercerFX::HalfThickness/FMath::Max(.1f,float(Bounds.GetExtent().Y)),Length/FMath::Max(1.f,float(Bounds.GetSize().Z)));
    Blade->SetRelativeRotation(FRotationMatrix::MakeFromZX(FVector::ForwardVector,FVector::RightVector).ToQuat());
    Blade->SetRelativeLocation(FVector(-Bounds.Min.Z*BladeScale.Z,0,0));
    Blade->SetRelativeScale3D(BladeScale);BladeMID->SetVectorParameterValue(TEXT("Tint"),NetState.Tint);
    auto* Particle=Cast<UStaticMesh>(FSoftObjectPath(RiftPiercerFX::Mote).ResolveObject());
    auto* ParticleMaterial=Cast<UMaterialInterface>(FSoftObjectPath(RiftPiercerFX::MoteMaterial).ResolveObject());
    if(Particle&&ParticleMaterial)
    {
        Motes->SetStaticMesh(Particle);MoteMID=UMaterialInstanceDynamic::Create(ParticleMaterial,this);Motes->SetMaterial(0,MoteMID);
        MoteMID->SetVectorParameterValue(TEXT("Tint"),NetState.Tint);
        FRandomStream Random(18479);Seeds.Reserve(RiftPiercerFX::MoteCount);
        for(int32 Index=0;Index<RiftPiercerFX::MoteCount;++Index)
        {
            FMote Seed;Seed.Delay=Random.FRandRange(0.f,.035f);
            Seed.Station=.03f+.94f*(Index+Random.FRand())/RiftPiercerFX::MoteCount;
            Seed.Spread=Random.FRandRange(35.f,75.f);Seed.Spin=Random.FRandRange(0.f,360.f);
            Seed.Depth=Random.FRandRange(-1.f,1.f);Seed.Side=Index%2?1:-1;
            Seeds.Add(Seed);Motes->AddInstance(FTransform::Identity,false);
        }
    }
    UpdateVisuals();
}
void ARiftPiercerThrust::OnRep_State()
{
    if(NetState.Reach<=0||bInitialized)return;
    SetActorTransform(NetState.HiltFrame);bInitialized=true;LoadVisuals();
}
void ARiftPiercerThrust::ResolveThrust(float Damage,const FColdSteelSkillShot& Shot,bool ApplyDamage)
{
    const FVector Direction=NetState.HiltFrame.GetUnitAxis(EAxis::X),Start=NetState.HiltFrame.GetLocation(),End=Start+Direction*NetState.Reach;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RiftPiercerInstantThrust),false,GetOwner());Query.AddIgnoredActor(this);
    TArray<FHitResult> Contacts;float WallTime=1.f;bool Wall=false;
    for(;;)
    {
        TArray<FHitResult> Hits;bool PastBody=false;
        RangedAttackQuery::SweepMulti(GetWorld(),GetOwner(),Hits,Start,End,NetState.HiltFrame.GetRotation(),ECC_Visibility,
            FCollisionShape::MakeBox(FVector(2.f,RiftPiercerFX::HalfWidth,RiftPiercerFX::HalfThickness)),Query);
        for(const auto& Hit:Hits)
        {
            auto* Target=Hit.GetActor();
            if(Target&&(Target->IsA<APawn>()||Target->FindComponentByClass<UMonsterCombatComponent>()))
            {
                Query.AddIgnoredActor(Target);PastBody|=Hit.bBlockingHit;
                if(ApplyDamage&&UFPSMeleeLightningComponent::IsEnemy(Target,GetOwner()))Contacts.Add(Hit);
            }
            else if(Hit.bBlockingHit){Wall=true;WallTime=FMath::Min(WallTime,Hit.Time);}
        }
        if(!PastBody)break;
    }
    // The imprint ends at blocking cover and never damages through the wall.
    NetState.Reach*=WallTime;
    if(!ApplyDamage)return;
    Contacts.Sort([](const FHitResult& A,const FHitResult& B){return A.Time<B.Time;});
    TSet<TWeakObjectPtr<AActor>> HitActors;
    for(const auto& Hit:Contacts)
    {
        auto* Target=Hit.GetActor();
        if((Wall&&Hit.Time>=WallTime)||HitActors.Contains(Target)||!UFPSMeleeLightningComponent::IsEnemy(Target,GetOwner()))continue;
        HitActors.Add(Target);FWeaponDamageResult Result;
        const float Applied=ColdSteelSkills::ApplyHit(GetOwner(),Hit,Damage,Direction,Shot,&Result);
        if(Applied<=0&&!Result.bKilled)continue;
        HitGlow=1.f;
        if(NetState.ImpactPoints.Num()<8)NetState.ImpactPoints.Add(Hit.ImpactPoint);
        if(auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();Combat&&!Combat->IsDead())
            Combat->ReceiveForcedLaunch(Cast<APawn>(GetOwner()),Direction.GetSafeNormal2D()*500.f+FVector(0,0,520.f),.8f);
        if(auto* Character=Cast<AFPSGAMECharacter>(GetOwner()))
        {
            if(Character->IsLocallyControlled())Character->NotifyConfirmedWeaponHit(Target,Applied,&Result);
            else if(auto* State=Character->GetPlayerState<AColdSteelPlayerState>())
            {
                if(auto* Rune=Character->FindComponentByClass<UJingangRuneComponent>())Rune->ConfirmAttack(Target,Applied);
                FColdSteelNetHitReceipt Receipt;Receipt.Target=Target;Receipt.Applied=Applied;Receipt.bCritical=Result.bCritical;Receipt.bKilled=Result.bKilled;State->ClientConfirmHit(Receipt);
            }
        }
    }
}
void ARiftPiercerThrust::UpdateVisuals()
{
    const float Fade=1.f-FMath::SmoothStep(RiftPiercerFX::Hold,RiftPiercerFX::Lifetime,Age);
    for(auto* MID:{BladeMID.Get(),MoteMID.Get()})if(MID)
    {
        MID->SetScalarParameterValue(TEXT("Fade"),Fade);MID->SetScalarParameterValue(TEXT("Age"),Age);
        MID->SetScalarParameterValue(TEXT("HitGlow"),HitGlow);
    }
    // Cross-section punches outward briefly; length and position never travel or grow.
    const float Punch=1.f+.16f*FMath::Exp(-Age*55.f);
    if(BladeMID)Blade->SetRelativeScale3D(BladeScale*FVector(Punch,Punch,1.f));
    for(int32 Index=0;Index<Seeds.Num();++Index)
    {
        const auto& S=Seeds[Index];const float ParticleAge=FMath::Max(0.f,Age-S.Delay);
        const float Life=FMath::Clamp(ParticleAge/.50f,0.f,1.f),Burst=1.f-FMath::Exp(-ParticleAge*16.f);
        const float Outline=S.Station<.72f?1.f-.22f*S.Station:.842f*(1.f-S.Station)/.28f;
        const FVector Position(Length*S.Station,S.Side*(RiftPiercerFX::HalfWidth*Outline+S.Spread*Burst),
            S.Depth*(RiftPiercerFX::HalfThickness+Burst*20.f)+Life*18.f);
        const FTransform Transform(FRotator(S.Spin+Life*150.f,Life*80.f,S.Spin),Position,FVector(2.1f-Life));
        Motes->UpdateInstanceTransform(Index,Transform,false,false,true);
        Motes->SetCustomDataValue(Index,0,Age>=S.Delay?FMath::Pow(1.f-Life,.65f):0.f,false);
    }
    if(!Seeds.IsEmpty())Motes->MarkRenderStateDirty();
}
void ARiftPiercerThrust::Tick(float Delta)
{
    Super::Tick(Delta);if(!bInitialized)return;
    Age=float(FMath::Max(0.,Clock()-NetState.StartedAt));HitGlow=FMath::Max(0.f,HitGlow-Delta*10.f);
    UpdateVisuals();if(Age>=RiftPiercerFX::Lifetime)Destroy();
}
void ARiftPiercerThrust::EndPlay(EEndPlayReason::Type Reason)
{
    if(VisualLoad)VisualLoad->CancelHandle();VisualLoad.Reset();Super::EndPlay(Reason);
}
void ARiftPiercerThrust::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(ARiftPiercerThrust,NetState);
}
