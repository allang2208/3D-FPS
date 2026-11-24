#include "BowArrow.h"
#include "AuroraBeamVisual.h"
#include "EclipseBowMark.h"
#include "../../Combat/FPSAttackQuery.h"
#include "../../Monsters/UnknownHumanoid.h"
#include "BowMountainEchoComponent.h"
#include "../WeaponDamageFalloff.h"
#include "Components/MaterialBillboardComponent.h"
#include "Curves/CurveFloat.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "../FPSMeleeLightningComponent.h"
#include "../../Combat/RangedAttackQuery.h"
#include "../../Dungeons/WardBreakableGlass.h"
#include "../../FPSGAMECharacter.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Skills/FPSFireMagicComponent.h"
#include "../../Monsters/MonsterDamageAlert.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Props/FPSPracticeTarget.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../UI/ColdSteelWorldInteraction.h"
#include "Components/CapsuleComponent.h"
#include "Components/SphereComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Multiplayer/ColdSteelPlayerState.h"
#include "Net/UnrealNetwork.h"

ABowArrow::ABowArrow()
{
    PrimaryActorTick.bCanEverTick = true;
    bReplicates=true;SetReplicateMovement(true);SetNetUpdateFrequency(30.f);
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);
    FlightVisual = CreateDefaultSubobject<USceneComponent>(TEXT("FlightVisual"));
    FlightVisual->SetupAttachment(Root);
    Shaft = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Shaft"));
    Shaft->SetupAttachment(FlightVisual);
    Head = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Head"));
    Head->SetupAttachment(FlightVisual);
    FlightGlow = CreateDefaultSubobject<UMaterialBillboardComponent>(TEXT("FlightGlow"));
    FlightGlow->SetupAttachment(FlightVisual);
    FlightGlow->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    FlightGlow->SetCanEverAffectNavigation(false);
    FlightGlow->SetCastShadow(false);
    RecoveryShape = CreateDefaultSubobject<UCapsuleComponent>(TEXT("RecoveryShape"));
    RecoveryShape->SetupAttachment(Root);
    RecoveryShape->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RecoveryShape->SetCollisionResponseToAllChannels(ECR_Ignore);
    RecoveryShape->SetCollisionResponseToChannel(ECC_Visibility, ECR_Overlap);
    RecoveryShape->SetGenerateOverlapEvents(false);
    RecoveryShape->SetCanEverAffectNavigation(false);
    AutoRecovery=CreateDefaultSubobject<USphereComponent>(TEXT("AutoRecovery"));
    AutoRecovery->SetupAttachment(Root);
    AutoRecovery->InitSphereRadius(125.f);
    AutoRecovery->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    AutoRecovery->SetCollisionObjectType(ECC_WorldDynamic);
    AutoRecovery->SetCollisionResponseToAllChannels(ECR_Ignore);
    AutoRecovery->SetCollisionResponseToChannel(ECC_Pawn,ECR_Overlap);
    AutoRecovery->SetGenerateOverlapEvents(true);
    AutoRecovery->SetCanEverAffectNavigation(false);
    AutoRecovery->OnComponentBeginOverlap.AddDynamic(this,&ABowArrow::OnRecoveryOverlap);
    AutoRecovery->OnComponentEndOverlap.AddDynamic(this,&ABowArrow::OnRecoveryEndOverlap);
    for (UStaticMeshComponent* Component : { Shaft.Get(), Head.Get() })
    {
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetCanEverAffectNavigation(false);
        Component->SetCastShadow(false);
        Component->SetNotifyRigidBodyCollision(false);
    }
    // 箭体不做世界碰撞：命中由本 Actor 的扫掠负责，否则生成时会戳到自己手上的弓。
    SetActorEnableCollision(false);
}

void ABowArrow::Configure(float InDamage, float InSpeed, float InGravityCM, float InRangeCM,
                          const FColdSteelSkillShot& InShot, UStaticMesh* InShaftMesh, UStaticMesh* InHeadMesh,
                          float InRadiusCM, float InLengthCM, const FString& InAmmoId,
                          bool bInRecoverable, float InRecoverySeconds)
{
    Damage = FMath::Max(1.f, InDamage);
    Speed = FMath::Max(600.f, InSpeed);
    GravityCM = FMath::Max(0.f, InGravityCM);
    EffectiveRangeCM = FMath::Max(400.f, InRangeCM);
    if (HasAuthority()) SetNetCullDistanceSquared(FMath::Square(EffectiveRangeCM * 3.f));
    Shot = InShot;
    EclipseShot = HasAuthority() ? FEclipseBowShot::Capture(GetInstigator()) : nullptr;
    RemainingPenetrations=Shot.bHeartPiercingArrow?FMath::Clamp(Shot.BowTargetPenetration,0,3):0;
    HitTargets.Reset();
    AmmoId = InAmmoId;
    bRecoverable = bInRecoverable;
    if(HasAuthority())
    {
        Presentation.bAuroraBeam=Shot.bAuroraBeam;
        if(Shot.bAuroraBeam)Presentation.AuroraOrigin=GetActorLocation();
        Presentation.FlightStartServerTime=GetWorld()->GetTimeSeconds();
        Presentation.Shaft=InShaftMesh;Presentation.Head=InHeadMesh;Presentation.Ammo=InAmmoId;Presentation.Radius=InRadiusCM;Presentation.Length=InLengthCM;
        const auto* Fire=GetInstigator()?GetInstigator()->FindComponentByClass<UFPSFireMagicComponent>():nullptr;
        Presentation.bFlameArmor=!Shot.bAuroraBeam&&Fire&&Fire->ArmorRemaining()>0.f;ForceNetUpdate();
    }
    RecoverySeconds = FMath::Clamp(InRecoverySeconds, 8.f, 300.f);
    if (const auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        RecoveryCaption = FString::Printf(TEXT("拾回 %s ×1"), *Profile->AmmoLabel(AmmoId));
    const float Radius = FMath::Clamp(InRadiusCM, .05f, 6.f);
    const float Length = FMath::Clamp(InLengthCM, 20.f, 200.f);
    RecoveryShape->SetRelativeRotation(FRotator(90.f, 0.f, 0.f));
    RecoveryShape->SetRelativeLocation(FVector(-Length * .5f, 0.f, 0.f));
    AutoRecovery->SetRelativeLocation(FVector(-Length * .5f, 0.f, 0.f));
    RecoveryShape->SetCapsuleSize(FMath::Max(2.f, Radius), Length * .5f);
    CollisionRadiusCM = FMath::Clamp(Radius * 1.2f, .25f, 2.f);
    Velocity = GetActorForwardVector() * Speed;
    if (!Presentation.bAuroraBeam && GetNetMode() != NM_DedicatedServer && FlightGlow->Elements.IsEmpty())
    {
        if (auto* Base = LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Items/LootFX/M_LootCenter.M_LootCenter")))
        {
            auto* Glow = UMaterialInstanceDynamic::Create(Base,FlightGlow);
            Glow->SetVectorParameterValue(TEXT("LootColor"),FLinearColor(1.f,.72f,.22f));
            Glow->SetScalarParameterValue(TEXT("Intensity"),5.f);
            // Keep the nock small up close and legible at bow ranges, including inside a scope.
            auto* Size = NewObject<UCurveFloat>(FlightGlow);
            Size->FloatCurve.AddKey(0.f,.025f);
            Size->FloatCurve.AddKey(30000.f,.45f);
            Size->FloatCurve.AddKey(70000.f,1.f);
            FlightGlow->AddElement(Glow,nullptr,false,100.f,100.f,Size);
        }
    }
    FlightGlow->SetRelativeLocation(FVector(-Length,0,0));
    FlightGlow->SetVisibility(!Presentation.bAuroraBeam && !bStuck && !MountainContact.bHit);

    // 占位箭：引擎圆柱做箭杆、引擎圆锥做箭头；两者局部 +Z 沿箭身，转 90° 俯仰对到 Actor +X。
    auto* ShaftMesh = InShaftMesh ? InShaftMesh : LoadObject<UStaticMesh>(nullptr,
        TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    auto* HeadMesh = InHeadMesh ? InHeadMesh : LoadObject<UStaticMesh>(nullptr,
        TEXT("/Engine/BasicShapes/Cone.Cone"));
    const float HeadLength = FMath::Min(9.f, Length * .12f);
    Shaft->SetStaticMesh(ShaftMesh);
    if (InShaftMesh)
    {
        // Authored arrow includes shaft, nock, fletching and head. Actor origin
        // is always its tip, which is also the collision/launch contact point.
        const auto Bounds = InShaftMesh->GetBounds();
        const bool bAlongX = Bounds.BoxExtent.X > Bounds.BoxExtent.Z;
        const float Authored = 2.f * (bAlongX ? Bounds.BoxExtent.X : Bounds.BoxExtent.Z);
        const float LongScale = Length / FMath::Max(.01f, Authored);
        const FVector Scale = bAlongX ? FVector(LongScale, 1.f, 1.f) : FVector(1.f, 1.f, LongScale);
        const FQuat Rotation = FQuat::FindBetweenNormals(bAlongX ? FVector::XAxisVector : FVector::ZAxisVector, FVector::XAxisVector);
        Shaft->SetRelativeRotation(Rotation);
        Shaft->SetRelativeScale3D(Scale);
        const FVector Axis = bAlongX ? FVector::XAxisVector : FVector::ZAxisVector;
        const FVector Centre = Axis * FVector::DotProduct(Bounds.Origin, Axis);
        Shaft->SetRelativeLocation(FVector(-Length * .5f, 0.f, 0.f) - Rotation.RotateVector(Centre * Scale));
        Head->SetVisibility(false);
        UpdateAuroraBeam();
        return;
    }
    Shaft->SetRelativeRotation(FRotator(90.f, 0.f, 0.f));
    Shaft->SetRelativeLocation(FVector(-(Length + HeadLength) * .5f, 0.f, 0.f));
    Shaft->SetRelativeScale3D(FVector(Radius / 50.f, Radius / 50.f, (Length - HeadLength) / 100.f));
    Head->SetStaticMesh(HeadMesh);
    Head->SetRelativeRotation(FRotator(90.f, 0.f, 0.f));
    Head->SetRelativeLocation(FVector(-HeadLength * .5f, 0.f, 0.f));
    Head->SetRelativeScale3D(FVector(Radius * 2.1f / 50.f, Radius * 2.1f / 50.f, HeadLength / 100.f));
    UpdateAuroraBeam();
}

void ABowArrow::RefreshFlightTick()
{
    const bool bFlightEffects = Presentation.bAuroraBeam || Presentation.bIllumination || Presentation.bFlameArmor || ElementalArrow::IsElement(Presentation.Element);
    SetActorTickEnabled(!bStuck && !bEchoPending && !MountainContact.bHit && (HasAuthority() || bFlightSettling || bFlightEffects));
}

void ABowArrow::UpdateFlightSettle()
{
    if (!bFlightSettling || GetNetMode() == NM_DedicatedServer) return;
    const AGameStateBase* State = GetWorld()->GetGameState();
    const double Now = State ? State->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds();
    const float Age = FMath::Max(0.f, float(Now - Presentation.FlightStartServerTime));
    constexpr float SettleSeconds = .16f;
    if (Age >= SettleSeconds || bStuck || MountainContact.bHit)
    {
        FlightVisual->SetRelativeRotation(FQuat::Identity);
        bFlightSettling = false;
        RefreshFlightTick();
        return;
    }
    const float Envelope = FMath::Exp(-13.f * Age) * (1.f - FMath::SmoothStep(.11f, SettleSeconds, Age));
    // Actor origin and visual pivot are the arrow tip. The shaft, fletching
    // and nock glow settle as a unit while the sweep remains at the tip.
    FlightVisual->SetRelativeRotation(FRotator(.60f * FMath::Sin(51.f * Age),
        1.75f * FMath::Sin(75.f * Age), 0.f) * Envelope);
}

void ABowArrow::Tick(float Delta)
{
    Super::Tick(Delta);
    if(bEchoPending||MountainContact.bHit)return;
    UpdateFlightSettle();
    if(!HasAuthority()){UpdateAuroraBeam();UpdateFlameVisual(Delta);UpdateElementVisual(Delta);UpdateIlluminationVisual(Delta);return;}
    Delta = FMath::Max(0.f, Delta);
    if (bStuck) return;
    if (Delta <= 0.f || Speed <= 0.f) return;
    float Remaining = Delta;
    FVector Previous = GetActorLocation();
    while (Remaining > KINDA_SMALL_NUMBER)
    {
        const float TimeUntilDrop = FMath::Max(0.f, (EffectiveRangeCM - TravelledCM) / Speed);
        // A single swept segment covers straight flight. Only curvature needs substeps.
        const float Dt = FMath::Min(Remaining, FMath::Max(TimeUntilDrop, 1.f / 120.f));
        // The crossing substep contains a straight interval followed by a falling interval.
        const float FlatTime = FMath::Min(TimeUntilDrop, Dt);
        const float FallTime = Dt - FlatTime;
        const FVector Gravity(0., 0., -GravityCM);
        const FVector Next = Previous + Velocity * Dt + Gravity * (.5f * FallTime * FallTime);
        Velocity += Gravity * FallTime;
        SetActorRotation(Velocity.Rotation());
        float Distance=0.f;
        const bool bContinue=AdvanceSegment(Previous,Next,Distance);
        TravelledCM+=Distance;
        if(!bContinue)return;
        Previous = Next;
        Remaining -= Dt;
    }
    SetActorLocation(Previous);
    UpdateAuroraBeam();
    if (!CheckStillInWorld()) return;
    UpdateFlameVisual(Delta);
    UpdateElementVisual(Delta);
    UpdateIlluminationVisual(Delta);
}

void ABowArrow::ResolveLaunchObstruction(const FVector& CameraOrigin)
{
    if(Presentation.bIllumination)LastIlluminationScan=CameraOrigin;
    float Distance=0.f;
    AdvanceSegment(CameraOrigin,GetActorLocation(),Distance);
}

bool ABowArrow::AdvanceSegment(const FVector& Start,const FVector& End,float& Distance)
{
    FHitResult Hit;
    FFPSAttackQuery Query(SCENE_QUERY_STAT(BowArrow),true,GetInstigator());
    Query.AddIgnoredActor(this);
    for(const auto& Target:HitTargets)if(Target.IsValid())Query.AddIgnoredActor(Target.Get());
    // Re-query the complete segment after each penetrated target. Moving the
    // start beyond a body could skip a thin wall or an adjacent second target.
    while(RangedAttackQuery::SweepSingle(GetWorld(),GetInstigator(),Hit,Start,End,FQuat::Identity,
        ECC_Visibility,FCollisionShape::MakeSphere(CollisionRadiusCM),Query))
    {
        Distance=FVector::Distance(Start,Hit.Location);
        auto* Target=Hit.GetActor();
        auto* Component=Hit.GetComponent();
        ScanIllumination(Hit.Location,true);
        if(!ApplyHit(Hit,TravelledCM+Distance))return false;
        if(Target&&HitTargets.Contains(Target))Query.AddIgnoredActor(Target);
        else if(Component)Query.AddIgnoredComponent(Component); // Broken pane only; its wall still blocks.
    }
    Distance=FVector::Distance(Start,End);
    ScanIllumination(End,false);
    return true;
}

bool ABowArrow::ApplyHit(const FHitResult& Hit,float ContactDistanceCM)
{
    if(bResolved||bStuck)return false;
    const auto BurstAtPassThrough=[&]()
    {
        if(!Presentation.bAuroraBeam)return;
        FAuroraBeamContact Contact;
        Contact.At=AuroraBeamVisual::Clock(GetWorld());
        Contact.Point=Hit.ImpactPoint;
        Contact.Normal=Hit.ImpactNormal;
        MulticastAuroraPierce(Contact);
    };
    // Continue flight through the removed pane instead of pinning an arrow in empty air.
    if(UWardBreakableGlass::BreakHit(Hit,Velocity.GetSafeNormal()))
    {
        if(Presentation.bMountainEcho){FinishMountainEchoHit(Hit);return false;}
        BurstAtPassThrough();
        return true;
    }
    auto* Target=Hit.GetActor();
    if(Target&&HitTargets.Contains(Target))return true;
    ApplyIlluminationImpact(Hit);
    const auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    const auto* Health=Target?Target->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    // Practice targets receive point damage without monster/health components.
    // They must also earn resonance and provide the original hit's crit receipt.
    const bool bEchoPracticeTarget=IsValid(Target)&&Target->IsA<AFPSPracticeTarget>()&&
        Target->CanBeDamaged()&&!Target->IsActorBeingDestroyed();
    const bool bEchoEligible=bEchoPracticeTarget||
        (((Combat&&!Combat->IsDead())||(Health&&!Health->IsDead()))&&
        UFPSMeleeLightningComponent::IsEnemy(Target,GetInstigator()));
    // Capture life before damage: a lethal arrow may still pass through its victim.
    const bool bCanPierce=RemainingPenetrations>0&&((Combat&&!Combat->IsDead())||(Health&&!Health->IsDead()));
    if(Target)
    {
        HitTargets.Add(Target);
        auto* Pawn = Cast<APawn>(GetInstigator());
        const FVector Direction = Velocity.GetSafeNormal();
        if (Target)
        {
            const float RangeScale=WeaponDamageFalloff::Multiplier(ContactDistanceCM,EffectiveRangeCM);
            const float ContactDamage=Damage*RangeScale;
            FWeaponDamageResult Result;
            float Applied = 0.f;
            {
                // Bow release/impact never reports a hearing stimulus. Keep
                // the local audio, and resolve group alarms only after death.
                const MonsterDamageAlert::FScopedSilentShot SilentShot(Target);
                FEclipseBowImpact EclipseImpact(EclipseShot.Get(), Target);
                // Illumination uses this ordinary-arrow damage snapshot and shared
                // armour/critical/status calculation, with no extra skill damage.
                if (auto* Unknown=Cast<AUnknownHumanoid>(Pawn)) Applied=Unknown->HitWithArrow(Hit,ContactDamage,Direction,Shot);
                else Applied = Presentation.bMountainEcho?ApplyEchoHit(Hit,RangeScale,Result):ColdSteelSkills::ApplyHit(Pawn, Hit, ContactDamage, Direction, Shot, &Result);
                EclipseImpact.Confirm(Applied);
            }
            if(!Presentation.bMountainEcho&&bEchoEligible)
            {
                if(MountainImpact&&!MountainImpact->bRecorded)
                {
                    // Store the pre-falloff receipt so the echo uses its own impact distance once.
                    MountainImpact->Physical=Result.BeforeDefense.Scaled(1.f/RangeScale);
                    if(!Shot.bAuroraBeam)MountainImpact->Physical.BaseMagic=MountainImpact->Physical.AddedMagic=0;
                    MountainImpact->bCritical=Result.bCritical;MountainImpact->bRecorded=true;
                }
                if(bMountainGain)
                {
                    bMountainGain=false;
                    if(MountainSource.IsValid())MountainSource->ConfirmHit(MountainEpoch);
                }
            }
            if (auto* Character = Cast<AFPSGAMECharacter>(Pawn))
            {
                Character->NotifyConfirmedWeaponHit(Target, Applied, &Result, true,false);
                if(HasAuthority()&&!Character->IsLocallyControlled())if(auto* PS=Character->GetPlayerState<AColdSteelPlayerState>())
                {FColdSteelNetHitReceipt Receipt;Receipt.bFirearm=true;Receipt.Target=Target;Receipt.Applied=Applied;Receipt.MagicApplied=Result.Applied.MagicPortion(Applied);Receipt.bCritical=Result.bCritical;Receipt.bKilled=Result.bKilled;PS->ClientConfirmHit(Receipt);}
            }
        }
    }
    BurstElement(Hit);
    if(Presentation.bMountainEcho){FinishMountainEchoHit(Hit);return false;}
    if(bCanPierce)
    {
        BurstAtPassThrough();
        --RemainingPenetrations;
        return true;
    }
    bResolved=true;
    SetActorLocation(Hit.ImpactPoint+Velocity.GetSafeNormal()*2.f);
    FinishStuck(Hit);
    return false;
}

void ABowArrow::MulticastAuroraPierce_Implementation(const FAuroraBeamContact& Contact)
{
    if(GetNetMode()==NM_DedicatedServer||AuroraBeamVisual::Clock(GetWorld())-Contact.At>.55)return;
    if(!AuroraBeam.IsValid())AuroraBeam=AAuroraBeamVisual::Open(this,Contact.Point);
    if(AuroraBeam.IsValid())
    {
        AuroraBeam->Burst(Contact);
        if(bAuroraFinished)AuroraBeam->Release();
    }
}

void ABowArrow::RecordAuroraContact(const FHitResult& Hit)
{
    if(!Presentation.bAuroraBeam||AuroraContact.At>=0.)return;
    AuroraContact.At=AuroraBeamVisual::Clock(GetWorld());
    AuroraContact.Point=Hit.ImpactPoint;
    AuroraContact.Normal=Hit.ImpactNormal;
    // On a near-wall release the initial camera-to-tip sweep can find a wall
    // behind the muzzle. Keep the visual entirely on the shooter's side.
    if(TravelledCM==0.f&&FVector::DotProduct(Hit.ImpactPoint-FVector(Presentation.AuroraOrigin),Velocity)<0.)
        Presentation.AuroraOrigin=Hit.ImpactPoint;
    UpdateAuroraBeam();
    ForceNetUpdate();
}

void ABowArrow::OnRep_AuroraContact()
{
    UpdateAuroraBeam();
}

void ABowArrow::UpdateAuroraBeam()
{
    if(!Presentation.bAuroraBeam||GetNetMode()==NM_DedicatedServer)return;
    Shaft->SetVisibility(false);
    Head->SetVisibility(false);
    FlightGlow->SetVisibility(false);
    if(bAuroraFinished||bEchoPending)return;
    const double Now=AuroraBeamVisual::Clock(GetWorld());
    const bool Hit=AuroraContact.At>=0.;
    if(Hit&&Now-AuroraContact.At>.55)
    {
        if(AuroraBeam.IsValid())AuroraBeam->Release();
        bAuroraFinished=true;
        return;
    }
    if(!Hit&&(bStuck||MountainContact.bHit||Now<Presentation.FlightStartServerTime))return;
    const FVector Start=Presentation.AuroraOrigin;
    if(!Hit&&GetActorLocation().Equals(Start,.05))return;
    if(!AuroraBeam.IsValid())AuroraBeam=AAuroraBeamVisual::Open(this,Start);
    if(!AuroraBeam.IsValid())return;
    if(Hit)
    {
        AuroraBeam->Finish(0,Start,Presentation.FlightStartServerTime,AuroraContact);
        AuroraBeam->Release();
        bAuroraFinished=true;
    }
    else AuroraBeam->Trace(0,Start,Presentation.FlightStartServerTime,GetActorLocation(),Now);
}

void ABowArrow::FinishStuck(const FHitResult& Hit)
{
    bStuck = true;
    RecordAuroraContact(Hit);
    FlightVisual->SetRelativeRotation(FQuat::Identity);
    bFlightSettling = false;
    FlightGlow->SetVisibility(false);
    UpdateIlluminationVisual(0);
    UpdateElementVisual(0);
    StopFlameVisual();
    Velocity = FVector::ZeroVector;
    SetActorTickEnabled(false);
    // Even an infinite-reserve arrow can be gathered out of the world. Only
    // an actually spent arrow exposes the manual pickup / ammo refund shape.
    SetActorEnableCollision(true);
    RecoveryShape->SetCollisionEnabled(bRecoverable ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision);
    SetLifeSpan(bRecoverable ? RecoverySeconds : StickSeconds);
    // 命中生物：跟着骨骼走，避免目标移动后箭悬在空中。
    if (auto* Component = Hit.GetComponent())
    {
        if (Hit.BoneName.IsNone()) AttachToComponent(Component, FAttachmentTransformRules::KeepWorldTransform);
        else AttachToComponent(Component, FAttachmentTransformRules::KeepWorldTransform, Hit.BoneName);
    }
    // Proximity collection and inventory ownership are separate. The overlap
    // timer still runs only near a player; virtual arrows never grant ammo.
    AutoRecovery->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
}

void ABowArrow::EndPlay(const EEndPlayReason::Type Reason)
{
    if(AuroraBeam.IsValid())AuroraBeam->Release();
    GetWorldTimerManager().ClearTimer(EchoDelay);
    ReleaseMountainEchoVisual();
    GetWorldTimerManager().ClearTimer(RecoveryTimer);
    StopFlameVisual();
    Super::EndPlay(Reason);
}

void ABowArrow::OnRecoveryOverlap(UPrimitiveComponent* OverlappedComponent,AActor* OtherActor,
    UPrimitiveComponent* OtherComponent,int32 OtherBodyIndex,bool bFromSweep,const FHitResult& SweepResult)
{
    const auto* Pawn=Cast<APawn>(OtherActor);
    if(bStuck&&!IsActorBeingDestroyed()&&Pawn&&Pawn->IsPlayerControlled()&&
        !GetWorldTimerManager().IsTimerActive(RecoveryTimer))
        GetWorldTimerManager().SetTimer(RecoveryTimer,this,&ABowArrow::RecoverNearby,.2f,true,.15f);
}

void ABowArrow::OnRecoveryEndOverlap(UPrimitiveComponent* OverlappedComponent,AActor* OtherActor,
    UPrimitiveComponent* OtherComponent,int32 OtherBodyIndex)
{
    RecoverNearby();
}

void ABowArrow::RecoverNearby()
{
    if(!bStuck||IsActorBeingDestroyed())
    {GetWorldTimerManager().ClearTimer(RecoveryTimer);return;}
    TArray<AActor*> Nearby;AutoRecovery->GetOverlappingActors(Nearby,APawn::StaticClass());
    bool bPlayerNearby=false;
    for(auto* Actor:Nearby)
    {
        auto* Pawn=Cast<APawn>(Actor);
        if(!Pawn||!Pawn->IsPlayerControlled())continue;
        if(GetNetMode()!=NM_Standalone&&bRecoverable&&!Pawn->IsLocallyControlled())continue;
        bPlayerNearby=true;
        if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())continue;
        // A nearby arrow behind a wall cannot be collected through that wall.
        FCollisionQueryParams Query(SCENE_QUERY_STAT(BowArrowRecovery),false,Pawn);Query.AddIgnoredActor(this);
        FHitResult Obstruction;const FVector End=AutoRecovery->GetComponentLocation();
        if(GetWorld()->LineTraceSingleByChannel(Obstruction,Pawn->GetActorLocation(),End,ECC_Visibility,Query)&&
            FVector::DistSquared(Obstruction.ImpactPoint,End)>FMath::Square(8.f))continue;
        if(bRecoverable)
        {
            if(GetNetMode()==NM_Client)
            {
                if(auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>())
                {
                    if(PS->InventoryRequestPending())continue;
                    PS->RequestInventoryAction(EColdSteelInventoryAction::RecoverArrow,FString(),this);
                }
            }
            else RecoverIntoPouch(Pawn);
        }
        else
        {
            // No pouch round was spent for this shot. Collect the visible
            // arrow without converting unlimited practice ammo into stock.
            if(HasAuthority()){bStuck=false;SetActorEnableCollision(false);Destroy();}
        }
        // On a save failure keep the arrow and retry on the next entry, without
        // retrying disk writes or notices five times per second.
        GetWorldTimerManager().ClearTimer(RecoveryTimer);
        return;
    }
    if(!bPlayerNearby)GetWorldTimerManager().ClearTimer(RecoveryTimer);
}

FString ABowArrow::RecoveryPrompt() const
{
    return CanRecover() ? RecoveryCaption : FString();
}

bool ABowArrow::TryRecover(APawn* Pawn)
{
    if(!Pawn||FVector::DistSquared(Pawn->GetActorLocation(),AutoRecovery->GetComponentLocation())>FMath::Square(250.f))return false;
    const bool Near=FVector::DistSquared(Pawn->GetActorLocation(),AutoRecovery->GetComponentLocation())<=FMath::Square(125.f)
        &&ColdSteelWorldInteraction::CanReachPickup(GetWorld(),Pawn,this,AutoRecovery->GetComponentLocation());
    if(!Near&&!ColdSteelWorldInteraction::IsFocused(Pawn,this))return false;
    if(GetNetMode()==NM_Client)
    {
        auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
        return PS&&PS->RequestInventoryAction(EColdSteelInventoryAction::RecoverArrow,FString(),this);
    }
    return RecoverIntoPouch(Pawn);
}

bool ABowArrow::RecoverIntoPouch(APawn* Pawn)
{
    if(!Pawn||!Pawn->IsPlayerControlled()||!CanRecover()||!HasAuthority())return false;
    auto* Player=Cast<AFPSGAMECharacter>(Pawn);
    auto* Profile=Player&&Player->GetNetShadowProfile()?Player->GetNetShadowProfile():Pawn->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Profile) return false;
    // Persist the exact fired type before removing the world arrow. Failed
    // saves/capacity leave it available; virtual training arrows never enter here.
    bRecoverable = false;
    // Overlap callbacks must not mistake an in-progress refund for a virtual
    // arrow if the inventory commit updates world state synchronously.
    bStuck = false;
    auto After=Profile->Snapshot();
    auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
    const bool Added=Profile->AddAmmoToState(After,AmmoId,1);
    const bool Saved=Added&&(GetNetMode()==NM_Standalone?Profile->CommitState(After)
        :Profile->CommitCampfireState(After,TEXT("Inventory"),Player&&Player->GetNetShadowProfile()&&PS?PS->CampfireGuestSlot():FString()));
    if (!Saved)
    {
        bRecoverable = true;
        bStuck = true;
    FlightGlow->SetVisibility(false);
        Profile->PostNotice(TEXT("箭支未拾回"), Profile->ResultMessage());
        return false;
    }
    SetActorEnableCollision(false);
    Destroy();
    return true;
}
void ABowArrow::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(ABowArrow,Presentation,COND_InitialOnly);
    DOREPLIFETIME(ABowArrow,bStuck);DOREPLIFETIME(ABowArrow,bRecoverable);
    DOREPLIFETIME(ABowArrow,bElementBurst);
    DOREPLIFETIME(ABowArrow,bEchoPending);
    DOREPLIFETIME(ABowArrow,MountainContact);
    DOREPLIFETIME(ABowArrow,AuroraContact);
}
void ABowArrow::OnRep_Presentation()
{
    bFlightSettling = !bStuck && !MountainContact.bHit;
    Configure(1,600,0,400,FColdSteelSkillShot{},Presentation.Shaft,Presentation.Head,
        Presentation.Radius,Presentation.Length,Presentation.Ammo,bRecoverable,120);
    ApplyEchoPresentation();OnRep_Stuck();OnRep_EchoPending();OnRep_MountainContact();
}
void ABowArrow::OnRep_Stuck()
{
    UpdateAuroraBeam();
    if(HasAuthority())return;
    SetActorEnableCollision(bStuck);
    RecoveryShape->SetCollisionEnabled(bStuck&&bRecoverable?ECollisionEnabled::QueryOnly:ECollisionEnabled::NoCollision);
    AutoRecovery->SetCollisionEnabled(bStuck?ECollisionEnabled::QueryOnly:ECollisionEnabled::NoCollision);
    if(bStuck){FlightGlow->SetVisibility(false);StopFlameVisual();}
    if(bStuck){UpdateElementVisual(0);UpdateIlluminationVisual(0);}
    if (bStuck) { FlightVisual->SetRelativeRotation(FQuat::Identity); bFlightSettling=false; }
    RefreshFlightTick();
}
