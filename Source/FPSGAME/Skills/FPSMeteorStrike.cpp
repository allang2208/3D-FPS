#include "FPSMeteorStrike.h"
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
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"

AFPSMeteorStrike::AFPSMeteorStrike()
{
    PrimaryActorTick.bCanEverTick=true;
    Root=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));SetRootComponent(Root);
    Rock=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MeteorRock"));Rock->SetupAttachment(Root);Rock->SetCollisionEnabled(ECollisionEnabled::NoCollision);Rock->SetCastShadow(false);
    Mantle=CreateDefaultSubobject<UNiagaraComponent>(TEXT("MeteorFire"));Mantle->SetupAttachment(Rock);Mantle->SetAutoActivate(false);
    Trail=CreateDefaultSubobject<UNiagaraComponent>(TEXT("MeteorTrail"));Trail->SetupAttachment(Root);Trail->SetAutoActivate(false);
    GroundFlames=CreateDefaultSubobject<UNiagaraComponent>(TEXT("LavaField"));GroundFlames->SetupAttachment(Root);GroundFlames->SetAutoActivate(false);
    Glow=CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));Glow->SetupAttachment(Rock);Glow->SetCastShadows(false);Glow->SetLightColor(FLinearColor(1,.22f,.035f));
    Burning=CreateDefaultSubobject<UAudioComponent>(TEXT("Burning"));Burning->SetupAttachment(Root);Burning->bAutoActivate=false;
}
bool AFPSMeteorStrike::InitializeStrike(APawn* Caster,const FFireMagicCast& Spell,const FVector& Point,const FVector& SurfaceNormal)
{
    Shooter=Caster;CastSnapshot=Spell;Destination=Point;Normal=SurfaceNormal.GetSafeNormal();NextLavaTick=Spell.TickSeconds;
    SetActorLocation(Point);
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Skills/FireMagic20260921/RealisticV3/SM_MeteorNaturalRock.SM_MeteorNaturalRock"));
    auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/FireMagic20260921/RealisticV3/MI_MeteorNaturalRock.MI_MeteorNaturalRock"));
    auto* Fire=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/FireMagic20260921/RealisticV5/NS_MeteorNaturalMantle.NS_MeteorNaturalMantle"));
    auto* Tail=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/FireMagic20260921/RealisticV5/NS_MeteorNaturalWake.NS_MeteorNaturalWake"));
    auto* Ground=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/FireMagic20260921/RealisticV5/NS_MeteorNaturalAfterfire.NS_MeteorNaturalAfterfire"));
    ImpactSystem=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/FireMagic20260921/RealisticV5/NS_MeteorNaturalImpact.NS_MeteorNaturalImpact"));
    LandSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Skills/FireMagic20260921/S_MeteorLand.S_MeteorLand"));
    Burning->SetSound(LoadObject<USoundBase>(nullptr,TEXT("/Game/Skills/FireMagic20260921/S_MeteorBurn.S_MeteorBurn")));
    if(!Mesh||!Material||!Fire||!Tail||!Ground||!ImpactSystem||!LandSound||!Burning->Sound){Destroy();return false;}
    Rock->SetStaticMesh(Mesh);Rock->SetMaterial(0,Material);
    const float Diameter=FMath::Max(1.f,Mesh->GetBounds().BoxExtent.GetMax()*2);
    Rock->SetRelativeScale3D(FVector(80.f/Diameter));
    InitialRockRotation=FRotator(FMath::FRandRange(-30.f,30.f),FMath::FRandRange(-180.f,180.f),FMath::FRandRange(-25.f,25.f)).Quaternion();
    SpinAxis=FVector(.36f,.77f,.19f).GetSafeNormal();Rock->SetWorldRotation(InitialRockRotation);
    // The source's 880 px fall becomes 13.2 m. Inside a room, begin beneath its
    // ceiling instead of showing a rock passing through opaque geometry.
    Start=Point+FVector(0,0,1320);
    FHitResult Roof;
    if(FireMagic::TraceSurface(Caster,Point+Normal*60,Start,Roof))Start=Roof.ImpactPoint-FVector(0,0,45);
    Rock->SetWorldLocation(Start);Mantle->SetAsset(Fire);Mantle->SetAbsolute(false,true,true);Mantle->SetWorldRotation(FRotator::ZeroRotator);Mantle->SetWorldScale3D(FVector(1));Mantle->SetVariableFloat(TEXT("User.Fade"),0);
    Mantle->SetVariableVec3(TEXT("User.FlightDirection"),FVector(0,0,-1));Mantle->SetVariableFloat(TEXT("User.FlightSpeed"),0);Mantle->Activate(true);
    Trail->SetAsset(Tail);Trail->SetWorldLocation(Start);Trail->SetVariableVec3(TEXT("User.FlightDirection"),FVector(0,0,-1));Trail->SetVariableFloat(TEXT("User.FlightSpeed"),0);
    Trail->SetVariablePosition(TEXT("User.PreviousPosition"),Start);Trail->SetVariablePosition(TEXT("User.CurrentPosition"),Start);Trail->SetVariableFloat(TEXT("User.Fade"),1);Trail->Activate(true);
    GroundFlames->SetAsset(Ground);GroundFlames->SetWorldLocation(Point+Normal*4);GroundFlames->SetWorldRotation(FRotationMatrix::MakeFromZ(Normal).Rotator());
    GroundFlames->SetVariableFloat(TEXT("User.Radius"),Spell.AuraRadius);GroundFlames->SetVariableFloat(TEXT("User.Fade"),1);
    GroundFlames->SetVariableFloat(TEXT("User.Spread"),.22f);
    Glow->SetAttenuationRadius(380);Glow->SetIntensity(2600);
    return true;
}
void AFPSMeteorStrike::DamageArea(bool bExplosion)
{
    APawn* Caster=Shooter.Get();auto* M=Caster&&Caster->GetGameInstance()?Caster->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;if(!M)return;
    const float Radius=bExplosion?CastSnapshot.Radius:CastSnapshot.AuraRadius;
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
        const FVector Offset=Target->GetActorLocation()-Destination;
        const float Ratio=FMath::Clamp(FVector::VectorPlaneProject(Offset,Normal).Size()/FMath::Max(1.f,Radius),0.f,1.f);
        const float Amount=bExplosion?FMath::FloorToFloat(CastSnapshot.Damage*(1-.5f*Ratio)):CastSnapshot.AuraDamage;
        const int32 Before=Rewards.Hits;
        if(!M->ApplyFireMagicHit(Caster,Target,CastSnapshot,Amount,Rewards))continue;Hits+=Rewards.Hits-Before;
        if(auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();Combat&&!Combat->IsDead())
        {
            if(bExplosion&&CastSnapshot.StunSeconds>0)Combat->ReceiveStun(Caster,CastSnapshot.StunSeconds,0);
            const int32 Stacks=bExplosion?CastSnapshot.BurnStacks:CastSnapshot.AuraBurnStacks;
            if(Stacks>0)UCombatStatusFormula::GetOrAdd(Target)->AddBurn(Caster,CastSnapshot.MagicAttack,Stacks,bExplosion?CastSnapshot.BurnSeconds:CastSnapshot.AuraBurnSeconds,bExplosion?CastSnapshot.BurnMultiplier:CastSnapshot.AuraBurnMultiplier,CastSnapshot.TickSeconds);
        }
    }
    Rewards.bMultiHit|=Hits>=2;
}
void AFPSMeteorStrike::Impact()
{
    bImpacted=true;BreakRock();Rock->SetVisibility(false);Mantle->Deactivate();Trail->Deactivate();
    DamageArea(true);UGameplayStatics::PlaySoundAtLocation(this,LandSound,Destination);
    if(Shooter.IsValid())if(auto* FireMagic=Shooter->FindComponentByClass<UFPSFireMagicComponent>())FireMagic->NotifyMeteorImpact(Destination);
    if(auto* Heat=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/M_FireballHeatShockwave.M_FireballHeatShockwave")))
        if(auto* Wave=GetWorld()->SpawnActor<AFireballShockwave>(Destination+Normal*3,FRotationMatrix::MakeFromZ(Normal).Rotator()))Wave->Setup(Heat,CastSnapshot.Radius,true);
    const float Scale=CastSnapshot.Radius/210.375f;
    if(auto* FX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,ImpactSystem,Destination+Normal*6,FRotationMatrix::MakeFromZ(Normal).Rotator(),FVector(Scale*1.5f),true,false,ENCPoolMethod::AutoRelease))
    {FX->SetVariableFloat(TEXT("User.SurfaceHit"),1);FX->SetVariableVec3(TEXT("User.LocalUp"),FX->GetComponentTransform().InverseTransformVectorNoScale(FVector::UpVector));FX->SetVariableFloat(TEXT("User.ImpactGrowth"),Scale-1);if(auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())Budget->ConfigureSmoke(FX,12,bWaterContact);FX->Activate(true);}
    GroundFlames->Activate(true);Burning->Play();Glow->SetWorldLocation(Destination+Normal*60);Glow->SetAttenuationRadius(CastSnapshot.Radius*2);
}
void AFPSMeteorStrike::Tick(float Delta)
{
    Super::Tick(Delta);
    APawn* Caster=Shooter.Get();const auto* Health=Caster?Caster->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Caster||(Health&&Health->IsDead())){Destroy();return;}
    const float PreviousAge=Age;Age+=Delta;
    if(!bImpacted)
    {
        const float T=FMath::Clamp(Age/FMath::Max(.05f,CastSnapshot.FallSeconds),0.f,1.f);
        const FVector Previous=Rock->GetComponentLocation(),Position=FMath::Lerp(Start,Destination+Normal*30,.28f*T+.72f*T*T);
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
    AnimateFragments(FMath::Min(Delta,FMath::Max(0.f,Age-FMath::Max(PreviousAge,CastSnapshot.FallSeconds))));
    while(NextLavaTick<=FMath::Min(LavaAge,CastSnapshot.Duration)+UE_KINDA_SMALL_NUMBER)
    {DamageArea(false);NextLavaTick+=CastSnapshot.TickSeconds;}
    const float Fade=FMath::Clamp((CastSnapshot.Duration-LavaAge)/.45f,0.f,1.f);
    const float Spread=FMath::Clamp(LavaAge/.22f,0.f,1.f);
    GroundFlames->SetVariableFloat(TEXT("User.Spread"),FMath::Lerp(.22f,1.f,Spread*Spread*(3-2*Spread)));
    GroundFlames->SetVariableFloat(TEXT("User.Fade"),Fade);Glow->SetIntensity((800+4500*FMath::Exp(-LavaAge*9))*Fade);
    Burning->SetVolumeMultiplier(Fade);
    if(LavaAge>=CastSnapshot.Duration)Finish();
}
void AFPSMeteorStrike::Finish()
{
    if(bSettled)return;bSettled=true;
    if(auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())M->FinishFireMagicCast(TEXT("meteor"),Rewards);
    Destroy();
}
void AFPSMeteorStrike::EndPlay(EEndPlayReason::Type Reason)
{Burning->Stop();Super::EndPlay(Reason);}

void AFPSMeteorStrike::BreakRock()
{
    FragmentMaterial=UMaterialInstanceDynamic::Create(Rock->GetMaterial(0),this);
    const float Diameter=FMath::Max(1.f,Rock->GetStaticMesh()->GetBounds().BoxExtent.GetMax()*2);
    FVector Tangent,Bitangent;Normal.FindBestAxisVectors(Tangent,Bitangent);
    for(int32 I=0;I<12;++I)
    {
        const float Angle=I*UE_TWO_PI/12.f+FMath::FRandRange(-.16f,.16f);
        const FVector Side=Tangent*FMath::Cos(Angle)+Bitangent*FMath::Sin(Angle);
        auto* Piece=NewObject<UStaticMeshComponent>(this);Piece->SetupAttachment(Root);
        Piece->SetStaticMesh(Rock->GetStaticMesh());Piece->SetMaterial(0,FragmentMaterial);
        Piece->SetCollisionEnabled(ECollisionEnabled::NoCollision);Piece->SetCastShadow(false);Piece->RegisterComponent();
        Piece->SetWorldLocation(Destination+Normal*24+Side*FMath::FRandRange(6.f,19.f));
        Piece->SetWorldRotation(FRotator(FMath::FRandRange(-180.f,180.f),Angle*180/PI,FMath::FRandRange(-180.f,180.f)));
        const float Size=FMath::FRandRange(7.f,15.f)/Diameter;
        const FVector Shape(Size*FMath::FRandRange(.5f,.9f),Size,Size*FMath::FRandRange(.55f,1.15f));
        Piece->SetWorldScale3D(Shape);Fragments.Add(Piece);FragmentScales.Add(Shape);
        FragmentVelocities.Add(Side*FMath::FRandRange(150.f,300.f)+Normal*FMath::FRandRange(130.f,255.f));
        FragmentSpins.Add(FRotator(FMath::FRandRange(-240.f,240.f),FMath::FRandRange(-180.f,180.f),FMath::FRandRange(-210.f,210.f)));
    }
}
void AFPSMeteorStrike::AnimateFragments(float Delta)
{
    if(FragmentMaterial)FragmentMaterial->SetScalarParameterValue(TEXT("Heat"),FMath::Exp(-LavaAge*1.5f));
    const float Shrink=1-FMath::Clamp((LavaAge-1.15f)/.55f,0.f,1.f);
    for(int32 I=0;I<Fragments.Num();++I)
    {
        auto* Piece=Fragments[I].Get();if(!Piece)continue;
        if(Shrink<=0){Piece->DestroyComponent();Fragments[I]=nullptr;continue;}
        FVector& Velocity=FragmentVelocities[I];Velocity.Z-=680*Delta;
        FVector Position=Piece->GetComponentLocation()+Velocity*Delta;
        const float Height=FVector::DotProduct(Position-Destination,Normal);
        if(Height<4){Position+=Normal*(4-Height);Velocity=FVector::VectorPlaneProject(Velocity,Normal)*.48f+Normal*FMath::Abs(FVector::DotProduct(Velocity,Normal))*.20f;FragmentSpins[I]*=.65f;}
        Piece->SetWorldLocation(Position);Piece->AddLocalRotation(FragmentSpins[I]*Delta);Piece->SetWorldScale3D(FragmentScales[I]*Shrink);
    }
}
