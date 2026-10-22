#include "FPSMeteorStrike.h"
#include "MeteorAssets.h"
#include "../Weapons/ThermalTargetSubsystem.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "../WorldGeneration/RiverPilotFXSubsystem.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "../WorldGeneration/GrassDeform/GrassDeformSubsystem.h"
#include "FireMagicArea.h"
#include "FPSFireMagicComponent.h"
#include "FPSFireballProjectile.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"
#include "Net/UnrealNetwork.h"
#include "NetCastUtils.h"

namespace
{
// Original level-one radii (cm). Geometry follows the same replicated snapshot
// as damage/preview, so the new 3x range also produces a 3x level-one rock.
float MeteorBodyScale(const FFireMagicCast& Spell){return Spell.Radius/217.5f;}
}

AFPSMeteorStrike::AFPSMeteorStrike()
{
    PrimaryActorTick.bCanEverTick=true;
    Root=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));SetRootComponent(Root);
    Rock=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MeteorRock"));Rock->SetupAttachment(Root);Rock->SetCollisionEnabled(ECollisionEnabled::NoCollision);Rock->SetCastShadow(false);
    Mantle=CreateDefaultSubobject<UNiagaraComponent>(TEXT("MeteorFire"));Mantle->SetupAttachment(Rock);Mantle->SetAutoActivate(false);
    Trail=CreateDefaultSubobject<UNiagaraComponent>(TEXT("MeteorTrail"));Trail->SetupAttachment(Root);Trail->SetAutoActivate(false);
    GroundFlames=CreateDefaultSubobject<UNiagaraComponent>(TEXT("LavaField"));GroundFlames->SetupAttachment(Root);GroundFlames->SetAutoActivate(false);
    Glow=CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));Glow->SetupAttachment(Rock);Glow->SetCastShadows(false);Glow->SetLightColor(FLinearColor(1,.22f,.035f));
    Glow->SetVisibility(false);
    Burning=CreateDefaultSubobject<UAudioComponent>(TEXT("Burning"));Burning->SetupAttachment(Root);Burning->bAutoActivate=false;
    bReplicates=true; // 联机：服务端权威伤害；远端副本重演坠落/撞击/熔岩表现
}
void AFPSMeteorStrike::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AFPSMeteorStrike,NetCaster);
    DOREPLIFETIME(AFPSMeteorStrike,NetCast);
    DOREPLIFETIME(AFPSMeteorStrike,NetDestination);
    DOREPLIFETIME(AFPSMeteorStrike,NetNormal);
    DOREPLIFETIME(AFPSMeteorStrike,NetStartedAt);
}
double AFPSMeteorStrike::ServerClock() const
{const auto* State=GetWorld()->GetGameState();return State?State->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();}
// Late replicas resume the server timeline; assets never gate damage or restart age.
void AFPSMeteorStrike::NetInit()
{
    if(bNetInit||!NetCaster||NetCast.Damage<=0||NetStartedAt<0.)return;
    if(InitializeStrike(NetCaster,NetCast,NetDestination,NetNormal))bNetInit=true;
}
bool AFPSMeteorStrike::InitializeStrike(APawn* Caster,const FFireMagicCast& Spell,const FVector& Point,const FVector& SurfaceNormal)
{
    Shooter=Caster;CastSnapshot=Spell;Destination=Point;Normal=SurfaceNormal.GetSafeNormal();NextLavaTick=Spell.TickSeconds;
    if(HasAuthority())
    {
        NetCaster=Caster;NetCast=Spell;NetDestination=Point;NetNormal=Normal;NetStartedAt=ServerClock();
        RewardModel=NetCast::AuthorityModel(Caster,GetGameInstance());
    }
    SetActorLocation(Point);
    Start=Point+FVector(0,0,1320);Rock->SetWorldLocation(Start);
    if(GetNetMode()!=NM_DedicatedServer)
    {
        TArray<FSoftObjectPath> Paths;bool Ready=true;
        for(const TCHAR* Path:MeteorSpellAssets::Visuals){Paths.Add(FSoftObjectPath(Path));Ready&=Paths.Last().ResolveObject()!=nullptr;}
        if(Ready)PrepareVisuals();
        else VisualLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this](){PrepareVisuals();}));
    }
    return true;
}
void AFPSMeteorStrike::PrepareVisuals()
{
    if(IsActorBeingDestroyed()||bVisualsReady)return;
    auto* Mesh=Cast<UStaticMesh>(FSoftObjectPath(MeteorSpellAssets::Rock).ResolveObject());
    auto* Material=Cast<UMaterialInterface>(FSoftObjectPath(MeteorSpellAssets::RockMaterial).ResolveObject());
    auto* Fire=Cast<UNiagaraSystem>(FSoftObjectPath(MeteorSpellAssets::Mantle).ResolveObject());
    auto* Tail=Cast<UNiagaraSystem>(FSoftObjectPath(MeteorSpellAssets::Trail).ResolveObject());
    auto* Ground=Cast<UNiagaraSystem>(FSoftObjectPath(MeteorSpellAssets::GroundFire).ResolveObject());
    ImpactSystem=Cast<UNiagaraSystem>(FSoftObjectPath(MeteorSpellAssets::Impact).ResolveObject());
    LandSound=Cast<USoundBase>(FSoftObjectPath(MeteorSpellAssets::LandSound).ResolveObject());
    Burning->SetSound(Cast<USoundBase>(FSoftObjectPath(MeteorSpellAssets::BurnSound).ResolveObject()));
    HeatMaterial=Cast<UMaterialInterface>(FSoftObjectPath(MeteorSpellAssets::HeatMaterial).ResolveObject());
    ScorchMaterial=Cast<UMaterialInterface>(FSoftObjectPath(MeteorSpellAssets::Scorch).ResolveObject());
    if(!Mesh||!Material||!Fire||!Tail||!Ground||!ImpactSystem)return;
    const auto& Spell=CastSnapshot;const FVector Point=Destination;
    bVisualsReady=true;
    Glow->SetVisibility(true);
    Rock->SetStaticMesh(Mesh);Rock->SetMaterial(0,Material);
    const float Diameter=FMath::Max(1.f,Mesh->GetBounds().BoxExtent.GetMax()*2);
    const float BodyScale=MeteorBodyScale(Spell);
    Rock->SetRelativeScale3D(FVector(80.f*BodyScale/Diameter));
    InitialRockRotation=FRotator(FMath::FRandRange(-30.f,30.f),FMath::FRandRange(-180.f,180.f),FMath::FRandRange(-25.f,25.f)).Quaternion();
    SpinAxis=FVector(.36f,.77f,.19f).GetSafeNormal();Rock->SetWorldRotation(InitialRockRotation);
    // Always fall from 13.2 m above the marked point, including indoors.
    // The non-colliding rock reaches Destination without roof/wall interception.
    const float T=FMath::Clamp(float(ServerClock()-NetStartedAt)/FMath::Max(.05f,Spell.FallSeconds),0.f,1.f);
    Rock->SetWorldLocation(FMath::Lerp(Start,Destination+Normal*(30*BodyScale),.28f*T+.72f*T*T));Mantle->SetAsset(Fire);Mantle->SetAbsolute(false,true,true);Mantle->SetWorldRotation(FRotator::ZeroRotator);Mantle->SetWorldScale3D(FVector(BodyScale));Mantle->SetVariableFloat(TEXT("User.Fade"),0);
    Mantle->SetVariableVec3(TEXT("User.FlightDirection"),FVector(0,0,-1));Mantle->SetVariableFloat(TEXT("User.FlightSpeed"),0);Mantle->Activate(true);
    Trail->SetAsset(Tail);Trail->SetWorldLocation(Start);Trail->SetVariableVec3(TEXT("User.FlightDirection"),FVector(0,0,-1));Trail->SetVariableFloat(TEXT("User.FlightSpeed"),0);
    // World-space trail particles need an explicit size/width input; component
    // scaling would not scale their world-space births along the swept path.
    Trail->SetVariableFloat(TEXT("User.VisualScale"),BodyScale);
    Trail->SetVariablePosition(TEXT("User.PreviousPosition"),Start);Trail->SetVariablePosition(TEXT("User.CurrentPosition"),Start);Trail->SetVariableFloat(TEXT("User.Fade"),1);Trail->Activate(true);
    PrepareGroundFire(Ground);
    Glow->SetAttenuationRadius(380*BodyScale);Glow->SetIntensity(2600);
    UThermalTargetSubsystem::RegisterFire(Mantle,FVector(52*BodyScale));
    if(bImpacted)PresentImpact(false);
}
void AFPSMeteorStrike::DamageArea(bool bExplosion)
{
    if(!HasAuthority())return; // 伤害只在权威端结算；远端副本只演撞击特效
    APawn* Caster=Shooter.Get();auto* M=RewardModel.Get();if(!M||!Caster)return;
    const float Radius=bExplosion?CastSnapshot.Radius:CastSnapshot.AuraRadius;
    if((bExplosion?CastSnapshot.Damage:CastSnapshot.AuraDamage)>0)
        UWardBreakableGlass::BreakInRadius(GetWorld(),Destination+Normal*5.f,Radius,Caster);
    // Only the impact flattens grass. The burning field re-enters this function every
    // CastSnapshot.TickSeconds while it lives, so hooking the aura branch would stamp a fresh
    // flatten and a fresh wavefront into the render target several times a second for the whole
    // Duration - a permanent scorch ring instead of one shockwave. Anchored on Destination with
    // the same normal the decal, fragments and impact FX use, so grass and fire share a frame.
    if(bExplosion)
        if(auto* GrassDeform=GetWorld()->GetSubsystem<UGrassDeformSubsystem>())
            GrassDeform->AddImpulse(Destination,Radius*GrassDeformTuning::MeteorRadiusMultiplier,
                GrassDeformTuning::MeteorImpulseStrength,GrassDeformTuning::MeteorImpulseWaveSpeed);
    int32 Hits=0;
    for(AActor* Target:FireMagic::GroundTargets(Caster,Destination,Normal,Radius))
    {
        // Use the same ground contact as inclusion/preview. Tall creatures on
        // a slope must not receive extra falloff merely because their torso is high.
        const FVector Offset=FireMagic::GroundPoint(Target)-Destination;
        const float Ratio=FMath::Clamp(FVector::VectorPlaneProject(Offset,Normal).Size()/FMath::Max(1.f,Radius),0.f,1.f);
        const float Amount=bExplosion?FMath::FloorToFloat(CastSnapshot.Damage*(1-.5f*Ratio)):CastSnapshot.AuraDamage;
        const int32 Before=Rewards.Hits;
        if(!M->ApplyFireMagicHit(Caster,Target,CastSnapshot,Amount,Rewards))continue;Hits+=Rewards.Hits-Before;
        if(auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();Combat&&!Combat->IsDead())
        {
            if(bExplosion)
            {
                const FVector Away=Offset.GetSafeNormal2D();
                const bool bLaunched=Combat->ReceiveKnockdown(Caster,Away*FMath::Lerp(520.f,260.f,Ratio)+
                    FVector(0,0,FMath::Lerp(360.f,220.f,Ratio)),FMath::Max(.8f,CastSnapshot.StunSeconds));
                if(!bLaunched&&CastSnapshot.StunSeconds>0)Combat->ReceiveStun(Caster,CastSnapshot.StunSeconds,0);
            }
            const int32 Stacks=bExplosion?CastSnapshot.BurnStacks:CastSnapshot.AuraBurnStacks;
            if(Stacks>0)UCombatStatusFormula::GetOrAdd(Target)->AddBurn(Caster,CastSnapshot.MagicAttack,Stacks,bExplosion?CastSnapshot.BurnSeconds:CastSnapshot.AuraBurnSeconds,bExplosion?CastSnapshot.BurnMultiplier:CastSnapshot.AuraBurnMultiplier,CastSnapshot.TickSeconds);
        }
    }
    Rewards.bMultiHit|=Hits>=2;
}
void AFPSMeteorStrike::Impact()
{
    if(bImpacted)return;
    bImpacted=true;DamageArea(true);
    if(bVisualsReady)PresentImpact(Age-CastSnapshot.FallSeconds<.25f);
}
void AFPSMeteorStrike::PresentImpact(bool Transient)
{
    // Brief contact hold precedes fracture; damage stays on the exact
    // impact frame. The server clock also skips this hold on late presentation.
    bImpactBreakPending=Transient;
    Rock->SetVisibility(Transient);Mantle->Deactivate();Trail->Deactivate();
    PrepareScorch();
    // Late joining/loading restores only the remaining field, never an old hit cue.
    if(Transient)
    {
    UGameplayStatics::PlaySoundAtLocation(this,LandSound,Destination);
    // Each replica notifies only its local viewers, including when another
    // player cast the meteor. No camera RPC or duplicate owner notification.
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PC=It->Get();PC&&PC->IsLocalController())
            if(APawn* LocalPawn=PC->GetPawn())
                if(auto* FireMagic=LocalPawn->FindComponentByClass<UFPSFireMagicComponent>())FireMagic->NotifyMeteorImpact(Destination);
    if(HeatMaterial)
        if(auto* Wave=GetWorld()->SpawnActor<AFireballShockwave>(Destination+Normal*3,FRotationMatrix::MakeFromZ(Normal).Rotator()))Wave->Setup(HeatMaterial,CastSnapshot.Radius,true);
    // V4 owns its horizontal radius in centimetres. Keep component scale at one
    // so larger damage areas do not also stretch blast height and smoke speed.
    if(auto* FX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,ImpactSystem,Destination+Normal*6,FRotationMatrix::MakeFromZ(Normal).Rotator(),FVector::OneVector,true,false,ENCPoolMethod::AutoRelease))
    {
        FX->SetVariableFloat(TEXT("User.ImpactRadius"),CastSnapshot.Radius);
        FX->SetVariableFloat(TEXT("User.SurfaceHit"),1);
        FX->SetVariableVec3(TEXT("User.LocalUp"),FX->GetComponentTransform().InverseTransformVectorNoScale(FVector::UpVector));
        if(auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())Budget->ConfigureSmoke(FX,18,bWaterContact);
        FX->Activate(true);
    }
    }
    UpdateGroundFire(FMath::Max(0.f,Age-CastSnapshot.FallSeconds),0.f);
    GroundFlames->Activate(true);Burning->Play();Glow->SetWorldLocation(Destination+Normal*60);Glow->SetAttenuationRadius(CastSnapshot.Radius*2);
}
void AFPSMeteorStrike::Tick(float Delta)
{
    Super::Tick(Delta);
    if(!HasAuthority()){NetInit();if(!bNetInit)return;}
    APawn* Caster=Shooter.Get();const auto* Health=Caster?Caster->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Caster||(Health&&Health->IsDead())){Finish();return;}
    const float PreviousAge=Age;Age=FMath::Max(Age,float(ServerClock()-NetStartedAt));
    if(!HasAuthority()&&Age>=CastSnapshot.FallSeconds+CastSnapshot.Duration){Destroy();return;}
    UpdateGroundFire(FMath::Max(0.f,Age-CastSnapshot.FallSeconds),Delta);
    if(!bImpacted)
    {
        const float T=FMath::Clamp(Age/FMath::Max(.05f,CastSnapshot.FallSeconds),0.f,1.f);
        const FVector Previous=Rock->GetComponentLocation(),Position=FMath::Lerp(Start,Destination+Normal*(30*MeteorBodyScale(CastSnapshot)),.28f*T+.72f*T*T);
        if(!bWaterContact)
            if(auto* Water=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>())
                bWaterContact=Water->TryFireCrossing(Previous,T>=1?Destination:Position,CastSnapshot.Radius,true);
        Rock->SetWorldLocation(Position);Rock->SetWorldRotation(FQuat(SpinAxis,FMath::DegreesToRadians(28*T+17*T*T))*InitialRockRotation);
        const float Onset=FMath::Clamp(Age/.075f,0.f,1.f);Mantle->SetVariableFloat(TEXT("User.Fade"),Onset*Onset*(3-2*Onset));
        const FVector FlightDirection=(Position-Previous).GetSafeNormal();
        const float FlightSpeed=(Position-Previous).Size()/FMath::Max(.001f,Delta);
        Mantle->SetVariableVec3(TEXT("User.FlightDirection"),FlightDirection);Mantle->SetVariableFloat(TEXT("User.FlightSpeed"),FlightSpeed);
        Glow->SetIntensity(FMath::Lerp(1300.f,2800.f,T)*(.93f+.045f*FMath::Sin(Age*31)+.025f*FMath::Sin(Age*53)));
        Trail->SetWorldLocation(Position);Trail->SetVariablePosition(TEXT("User.PreviousPosition"),Previous);Trail->SetVariablePosition(TEXT("User.CurrentPosition"),Position);
        Trail->SetVariableVec3(TEXT("User.FlightDirection"),FlightDirection);Trail->SetVariableFloat(TEXT("User.FlightSpeed"),FlightSpeed);
        if(T<1)return;Impact();
    }
    // Include the fractional time after impact, without counting falling time.
    LavaAge+=FMath::Max(0.f,Age-FMath::Max(PreviousAge,CastSnapshot.FallSeconds));
    UpdateImpactPresentation();
    AnimateFragments(FMath::Min(Delta,FMath::Max(0.f,Age-FMath::Max(PreviousAge,CastSnapshot.FallSeconds))));
    while(NextLavaTick<=FMath::Min(LavaAge,CastSnapshot.Duration)+UE_KINDA_SMALL_NUMBER)
    {DamageArea(false);NextLavaTick+=CastSnapshot.TickSeconds;}
    const float Fade=FMath::Clamp((CastSnapshot.Duration-LavaAge)/.45f,0.f,1.f);
    // Reuse the existing unshadowed light: one short impact flash, then a dim
    // residual fire. No additional light or repeated impact pulse.
    Glow->SetIntensity((500+18000*FMath::Exp(-LavaAge*18)+2600*FMath::Exp(-LavaAge*4))*Fade);
    Glow->SetLightColor(FMath::Lerp(FLinearColor(1,.18f,.025f),FLinearColor(1,.58f,.22f),FMath::Exp(-LavaAge*12)));
    Burning->SetVolumeMultiplier(Fade);
    if(LavaAge>=CastSnapshot.Duration)Finish();
}
void AFPSMeteorStrike::SettleRewards()
{
    if(bSettled)return;bSettled=true;
    auto* M=RewardModel.Get();RewardModel=nullptr;
    const auto Completed=Rewards;Rewards={};
    if(HasAuthority()&&M)M->FinishFireMagicCast(TEXT("meteor"),Completed);
}
void AFPSMeteorStrike::Finish(){SettleRewards();Destroy();}
void AFPSMeteorStrike::FinishForRemoval(){if(HasAuthority())Finish();}
void AFPSMeteorStrike::EndPlay(EEndPlayReason::Type Reason)
{
    // Death/cleanup can destroy the actor before its normal duration expires.
    // Preserve already-earned training, with the same authority/once guard.
    SettleRewards();
    if(VisualLoad)VisualLoad->CancelHandle();VisualLoad.Reset();Burning->Stop();Super::EndPlay(Reason);
}

void AFPSMeteorStrike::BreakRock()
{
    FragmentMaterial=UMaterialInstanceDynamic::Create(Rock->GetMaterial(0),this);
    const float Diameter=FMath::Max(1.f,Rock->GetStaticMesh()->GetBounds().BoxExtent.GetMax()*2);
    const float SizeScale=FMath::Clamp(FMath::Sqrt(MeteorBodyScale(CastSnapshot)/3.f),.9f,1.25f);
    FRandomStream Random(GetTypeHash(NetStartedAt)); // Cosmetic stream, shared replicated seed.
    FVector Tangent,Bitangent;Normal.FindBestAxisVectors(Tangent,Bitangent);
    for(int32 I=0;I<12;++I)
    {
        const bool Heavy=I<2,Medium=I>=2&&I<6;
        const float Angle=I*2.39996323f+Random.FRandRange(-.45f,.45f);
        const FVector Side=Tangent*FMath::Cos(Angle)+Bitangent*FMath::Sin(Angle);
        auto* Piece=NewObject<UStaticMeshComponent>(this);Piece->SetupAttachment(Root);
        Piece->SetStaticMesh(Rock->GetStaticMesh());Piece->SetMaterial(0,FragmentMaterial);
        Piece->SetCollisionEnabled(ECollisionEnabled::NoCollision);Piece->SetCastShadow(false);Piece->RegisterComponent();
        const float Cm=(Heavy?Random.FRandRange(28.f,40.f):Medium?Random.FRandRange(13.f,23.f):Random.FRandRange(5.f,10.f))*SizeScale;
        FFragmentMotion Motion;
        Motion.Radius=Cm*.48f;
        Motion.TraceFrom=Destination+Normal*(Motion.Radius+18.f)+Side*Random.FRandRange(12.f,48.f);
        Motion.Scale=FVector(Random.FRandRange(.55f,.9f),1.f,Random.FRandRange(.55f,.9f))*(Cm/Diameter);
        const float Speed=Heavy?Random.FRandRange(160.f,250.f):Medium?Random.FRandRange(260.f,430.f):Random.FRandRange(400.f,640.f);
        const float Lift=Heavy?Random.FRandRange(65.f,110.f):Medium?Random.FRandRange(130.f,210.f):Random.FRandRange(180.f,300.f);
        Motion.Velocity=Side*Speed+Normal*Lift;
        const float Spin=Heavy?90.f:Medium?220.f:420.f;
        Motion.Spin=FRotator(Random.FRandRange(-Spin,Spin),Random.FRandRange(-Spin,Spin),Random.FRandRange(-Spin,Spin));
        Motion.Lifetime=(Heavy?2.4f:Medium?1.8f:1.1f)+Random.FRandRange(0.f,.4f);
        Motion.Bounce=Heavy?.08f:Medium?.14f:.22f;Motion.Retain=Heavy?.32f:Medium?.48f:.60f;
        Piece->SetWorldLocation(Motion.TraceFrom);
        Piece->SetWorldRotation(FRotator(Random.FRandRange(-180.f,180.f),Angle*180/PI,Random.FRandRange(-180.f,180.f)));
        Piece->SetWorldScale3D(Motion.Scale);Fragments.Add(Piece);FragmentMotion.Add(Motion);
    }
}
void AFPSMeteorStrike::AnimateFragments(float Delta)
{
    if(Fragments.IsEmpty())return;
    if(FragmentMaterial)FragmentMaterial->SetScalarParameterValue(TEXT("Heat"),FMath::Exp(-LavaAge*1.5f));
    auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(MeteorDebris),false,this);Query.AddIgnoredActor(Shooter.Get());
    const FCollisionObjectQueryParams StaticGeometry(FCollisionObjectQueryParams::AllStaticObjects);
    for(int32 I=0;I<Fragments.Num();++I)
    {
        auto* Piece=Fragments[I].Get();if(!Piece)continue;
        FFragmentMotion& Motion=FragmentMotion[I];Motion.Age+=Delta;
        const float Shrink=FMath::Clamp((Motion.Lifetime-Motion.Age)/.35f,0.f,1.f);
        if(Shrink<=0){Piece->DestroyComponent();Fragments[I]=nullptr;continue;}
        if(!Motion.bSettled)
        {
            FVector Position=Piece->GetComponentLocation()+Motion.Velocity*Delta+FVector(0,0,-490.f*Delta*Delta);
            Motion.Velocity.Z-=980.f*Delta;Motion.TraceAge+=Delta;
            // Smooth visual integration every frame; bounded static-geometry
            // contact sweeps at about 20 Hz, using the shared decoration budget.
            if(Motion.TraceAge>=.05f&&(!Budget||Budget->ReserveGeometryQueries(1,false)))
            {
                FHitResult Hit;
                if(GetWorld()->SweepSingleByObjectType(Hit,Motion.TraceFrom,Position,FQuat::Identity,StaticGeometry,
                    FCollisionShape::MakeSphere(Motion.Radius),Query))
                {
                    const FVector HitNormal=Hit.ImpactNormal.GetSafeNormal();
                    Position=Hit.Location+HitNormal*(Hit.bStartPenetrating?Hit.PenetrationDepth+1.f:1.f);
                    Motion.Velocity=FVector::VectorPlaneProject(Motion.Velocity,HitNormal)*Motion.Retain
                        +HitNormal*FMath::Abs(FVector::DotProduct(Motion.Velocity,HitNormal))*Motion.Bounce;
                    Motion.Spin*=.4f;
                    Motion.bSettled=HitNormal.Z>.45f&&Motion.Velocity.SizeSquared()<FMath::Square(60.f);
                }
                Motion.TraceFrom=Position;Motion.TraceAge=0.f;
            }
            Piece->SetWorldLocation(Position);Piece->AddLocalRotation(Motion.Spin*Delta);
        }
        Piece->SetWorldScale3D(Motion.Scale*Shrink);
    }
}
