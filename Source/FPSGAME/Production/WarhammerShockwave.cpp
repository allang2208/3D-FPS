#include "WarhammerShockwave.h"
#include "../Combat/FPSAttackQuery.h"
#include "../UI/ColdSteelStatusModel.h"
#include "WarhammerHeavyMotion.h"
#include "WarhammerCombat.h"
#include "WarhammerSlamFXSubsystem.h"
#include "ThunderHammerTuning.h"
#include "ThunderHammerFX.h"
#include "ThunderHammerCall.h"
#include "ThunderHammerZhenTing.h"
#include "ThunderHammerStaticField.h"
#include "ThunderHammerCoil.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/FPSLightningArc.h"
#include "NiagaraSystem.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/MagicOcclusion.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"
#include "Net/UnrealNetwork.h"

AWarhammerShockwave::AWarhammerShockwave()
{
    bReplicates=true;SetReplicateMovement(true);PrimaryActorTick.bCanEverTick=true;
    Ring=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GroundRing"));SetRootComponent(Ring);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> GroundWave(TEXT("/Game/Weapons/SteelWarhammer20261014/HeavySlamV1/M_WarhammerGroundWave.M_WarhammerGroundWave"));
    static ConstructorHelpers::FObjectFinder<USoundBase> GroundImpact(TEXT("/Game/Weapons/SteelWarhammer20261014/GroundImpactAudioV1/S_Warhammer_GroundImpact.S_Warhammer_GroundImpact"));
    ImpactSound=GroundImpact.Object;
    Ring->SetStaticMesh(Plane.Object);Ring->SetMaterial(0,GroundWave.Object);Ring->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Ring->SetCastShadow(false);Ring->SetReceivesDecals(false);Ring->SetCanEverAffectNavigation(false);
    NetUpdateFrequency=30.f;InitialLifeSpan=1.f;
}

ALeapStrikeShockwave::ALeapStrikeShockwave()
{
    static ConstructorHelpers::FObjectFinder<UStaticMesh> WaveMesh(TEXT("/Game/Weapons/SteelWarhammer20261014/LeapStrikeV2/SM_LeapGroundWave.SM_LeapGroundWave"));
    if(WaveMesh.Succeeded())
    {
        Ring->SetStaticMesh(WaveMesh.Object);
        Ring->SetMaterial(0,WaveMesh.Object->GetMaterial(0));
    }
}

double AWarhammerShockwave::Clock() const
{
    if(const auto* State=GetWorld()->GetGameState())return State->GetServerWorldTimeSeconds();
    return GetWorld()->GetTimeSeconds();
}
void AWarhammerShockwave::Setup(const FColdSteelSkillShot& InShot,float Radius,float StunSeconds,float ThunderMagic,bool ThunderCall)
{
    Shot=InShot;MaxRadius=Radius;HeavyStunSeconds=StunSeconds;StartedAt=Clock();bConfigured=true;
    bThunder=ThunderMagic>=0.f;
    bThunderCall=ThunderCall&&bThunder;
    NativeThunderMagic=bThunder?ThunderMagic:0.f;
    if(bThunder)
    {
        // The common hit receipt combines native stacks and a rune proc once.
        Shot.HammerNativeStacks=ThunderHammer::ElectrifyStacks;
        MaxRadius=ThunderHammer::RadiusCM;HeavyStunSeconds=ThunderHammer::StunSeconds;
        Shot.DamagePanel.AddedMagic+=NativeThunderMagic;
        // JiLei changes damage type, not the heavy attack's amount. Preserve
        // base/additional receipts and include the native thunder exactly once.
        if(bThunderCall)
            Shot.DamagePanel={0.,Shot.DamagePanel.Base(),0.,Shot.DamagePanel.Additional()};
        Shot.HammerElectricDamage=bThunderCall?Shot.DamagePanel.Total():NativeThunderMagic;
        ThunderSeed=int32(Shot.MasteryAttackSerial)^GetTypeHash(GetActorLocation());
        ThunderHeight=ThunderHammer::SkyHeightCM;
        FCollisionQueryParams Q(SCENE_QUERY_STAT(ThunderHammerCeiling),false,GetOwner());
        const FVector Start=GetActorLocation()+FVector(0,0,12);
        FHitResult Ceiling;
        // Indoor strikes end below the ceiling, always along world Z. Bodies
        // cannot act as ceilings; this trace never chooses damage targets.
        for(int32 Pass=0;Pass<16;++Pass)
        {
            if(!MagicOcclusion::TraceBlocker(GetWorld(),Start,Start+FVector(0,0,ThunderHeight),Q,Ceiling))break;
            auto* Actor=Ceiling.GetActor();
            if(Actor&&(Actor->IsA<APawn>()||Actor->FindComponentByClass<UMonsterCombatComponent>())){Q.AddIgnoredActor(Actor);continue;}
            ThunderHeight=FMath::Max(8.f,float(Ceiling.ImpactPoint.Z-GetActorLocation().Z)-8.f);break;
        }
        // One server receipt per victim at the contact instant. The remaining
        // ground ring is cosmetic; walking into its afterglow cannot hit again.
        ApplyWave(MaxRadius);
        if(bThunderCall)
        {
            ThunderHammerStaticField::Pulse(GetOwner(),GetActorLocation(),Shot,ThunderHammerStaticField::CallRadiusCM,5);
            ThunderHammerCoil::Discharge(GetOwner(),GetActorLocation(),Shot,ThunderHammerCoil::CallRadiusCM,2);
        }
        ThunderHammerZhenTing::ContinueLightning(this,Shot,MaxRadius,
            bThunderCall?float(Shot.DamagePanel.Total()):NativeThunderMagic,bThunderCall);
    }
    ForceNetUpdate();
}
void AWarhammerShockwave::BeginPlay()
{
    Super::BeginPlay();
    Ring->SetRelativeScale3D(FVector(.001));
    if(GetNetMode()!=NM_DedicatedServer)
        Material=Ring->CreateDynamicMaterialInstance(0);
}
void AWarhammerShockwave::SetLeapTraining(UColdSteelStatusModel* Profile)
{
    if(HasAuthority())LeapRewardModel=Profile;
}
void AWarhammerShockwave::EndPlay(const EEndPlayReason::Type Reason)
{
    auto* Reward=LeapRewardModel.Get();LeapRewardModel.Reset();
    if(HasAuthority()&&Reward)Reward->TrainLeapStrike(LeapKills);
    Super::EndPlay(Reason);
}
void AWarhammerShockwave::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AWarhammerShockwave,MaxRadius);DOREPLIFETIME(AWarhammerShockwave,StartedAt);
    DOREPLIFETIME(AWarhammerShockwave,bThunder);DOREPLIFETIME(AWarhammerShockwave,ThunderHeight);DOREPLIFETIME(AWarhammerShockwave,ThunderSeed);
    DOREPLIFETIME(AWarhammerShockwave,bThunderCall);DOREPLIFETIME(AWarhammerShockwave,ImpactSound);
}
FWeaponDamageParts AWarhammerShockwave::DamageWithElectricMultiplier(float Multiplier) const
{
    if(!bThunder)return Shot.DamagePanel;
    if(bThunderCall)return Shot.DamagePanel.Scaled(Multiplier);
    auto Damage=Shot.DamagePanel;
    Damage.AddedMagic+=NativeThunderMagic*(Multiplier-1.f);
    return Damage;
}
void AWarhammerShockwave::ApplyWave(float Radius)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn)return;
    auto* Profile=ColdSteelAuthority::ForPawn(Pawn);ColdSteelAuthority::FScope Scope(Profile);
    const FVector Origin=GetActorLocation();
    TArray<FOverlapResult> Overlaps;
    FFPSAttackQuery Q(SCENE_QUERY_STAT(WarhammerWave),false,Pawn);
    GetWorld()->OverlapMultiByObjectType(Overlaps,Origin+FVector(0,0,65),FQuat::Identity,
        FCollisionObjectQueryParams::AllDynamicObjects,FCollisionShape::MakeBox(FVector(Radius,Radius,110)),Q);
    for(const auto& Overlap:Overlaps)if(auto* Body=Cast<APawn>(Overlap.GetActor()))Q.AddIgnoredActor(Body);
    for(const auto& Overlap:Overlaps)
    {
        auto* Target=Overlap.GetActor();auto* Shape=Overlap.GetComponent();
        auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(!Shape||!Combat||HitActors.Contains(Target)||!UFPSMeleeLightningComponent::IsEnemy(Target,Pawn))continue;
        const auto Bounds=Shape->Bounds;
        if(FMath::Abs(Bounds.Origin.Z-Bounds.BoxExtent.Z-Origin.Z)>70.f)continue;
        FVector Point;
        if(Shape->GetClosestPointOnCollision(Origin+FVector(0,0,30),Point)<0.f)Point=Bounds.GetBox().GetClosestPointTo(Origin+FVector(0,0,30));
        const FVector Normal=GetActorUpVector(),ToPoint=Point-Origin;
        const FVector PlaneOffset=ToPoint-Normal*FVector::DotProduct(ToPoint,Normal);
        if(PlaneOffset.SizeSquared()>FMath::Square(Radius))continue;
        const FVector ToBounds=Bounds.Origin-Origin;
        const float FarEdge=(ToBounds-Normal*FVector::DotProduct(ToBounds,Normal)).Size()+Bounds.BoxExtent.Size2D();
        if(FarEdge<PreviousRadius-16.f)continue;
        // The expanding band reaches every target once, even across a late frame.
        // Feet/height and solid-cover checks prevent cross-floor/wall damage.
        FHitResult Cover;
        if(MagicOcclusion::TraceBlocker(GetWorld(),Origin+FVector(0,0,12),Point,Q,Cover)&&Cover.GetActor()!=Target)continue;
        HitActors.Add(Target);
        FHitResult Hit(Target,Shape,Point,(Origin-Point).GetSafeNormal());Hit.TraceStart=Origin;Hit.TraceEnd=Point;
        FWeaponDamageResult Result;
        const bool Eligible=ColdSteelSkills::IsMasteryTrainingTarget(Pawn,Target);
        auto HitShot=Shot;HitShot.ExtraMasteryExperience=Eligible&&MasteryHits==1&&Profile?Profile->MasteryDefinition(Shot.MasteryId).MultiHitExperience:0;
        if(bThunder)if(const auto* Status=Target->FindComponentByClass<UCombatStatusFormula>())
            HitShot.DamagePanel=DamageWithElectricMultiplier(Status->ElectricMultiplier());
        const float Damage=ColdSteelSkills::ApplyHit(Pawn,Hit,HitShot.DamagePanel.Total(),(Point-Origin).GetSafeNormal(),HitShot,&Result);
        if(Eligible&&Result.bKilled&&LeapRewardModel.IsValid())++LeapKills;
        if(Eligible&&(Damage>0.f||Result.bKilled))++MasteryHits;
        if(Damage>0.f||Combat->IsDead())Pawn->NotifyConfirmedWeaponHit(Target,Damage,&Result);
        if(Damage>0.f)WarhammerCombat::ApplyHeavyStun(Target,HeavyStunSeconds);
    }
}
void AWarhammerShockwave::Tick(float Delta)
{
    Super::Tick(Delta);
    if(StartedAt<0.||(HasAuthority()&&!bConfigured))return;
    const float Age=FMath::Max(0.f,float(Clock()-StartedAt));
    const float T=FMath::Clamp(Age/WarhammerHeavy::WaveSeconds,0.f,1.f);
    const float Radius=FMath::Lerp(12.f,MaxRadius,T);
    if(HasAuthority()&&!bThunder){ApplyWave(Radius);PreviousRadius=Radius;}
    // Scale only the visual component; replication owns the impact transform.
    Ring->SetRelativeScale3D(FVector(Radius/50.f,Radius/50.f,1.f));
    if(Material)Material->SetScalarParameterValue(TEXT("Opacity"),FMath::Pow(1.f-T,1.15f));
    PresentImpact();
    if(bThunder&&!bThunderVisualPlayed&&GetNetMode()!=NM_DedicatedServer)
        if(auto* FX=GetWorld()->GetSubsystem<UThunderHammerFXSubsystem>())
            bThunderVisualPlayed=FX->Emit(GetActorLocation()-GetActorUpVector()*2.f,GetActorUpVector(),ThunderHeight,ThunderSeed,Age,bThunderCall?ThunderHammerCall::VisualScale:1.f);
    if(HasAuthority()&&Age>=(bThunder?ThunderHammer::VisualSeconds+.1f:WarhammerHeavy::WaveSeconds))Destroy();
}

void AWarhammerShockwave::PresentImpact()
{
    if(bSoundPlayed||StartedAt<0.||GetNetMode()==NM_DedicatedServer)return;
    bSoundPlayed=true;
    if(auto* FX=GetWorld()->GetSubsystem<UWarhammerSlamFXSubsystem>())
        FX->Emit(GetActorLocation()-GetActorUpVector()*2.f,GetActorQuat(),MaxRadius,float(Clock()-StartedAt));
    if(ImpactSound)UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,GetActorLocation(),1.f,1.f);
}
