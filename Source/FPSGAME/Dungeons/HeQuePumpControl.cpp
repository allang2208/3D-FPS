#include "HeQuePumpControl.h"
#include "../Monsters/HeQueMonster.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"
#include "UObject/ConstructorHelpers.h"

namespace HeQuePumpControlTiming {constexpr double WarningSeconds=2.5, VentSeconds=2., CooldownSeconds=30.;constexpr float Radius=600.f;}

AHeQuePumpControl::AHeQuePumpControl()
{
    bReplicates=true;bAlwaysRelevant=true;SetReplicateMovement(true);
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.bStartWithTickEnabled=false;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    auto* Bounds=CreateDefaultSubobject<UBoxComponent>(TEXT("UseBounds"));Bounds->SetupAttachment(RootComponent);
    Bounds->SetRelativeLocation(FVector(0,-67,0));Bounds->SetBoxExtent(FVector(31,10,31));
    Bounds->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Bounds->SetCollisionResponseToAllChannels(ECR_Ignore);
    Bounds->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);Bounds->SetGenerateOverlapEvents(false);Bounds->SetCanEverAffectNavigation(false);
    Valve=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Valve"));Valve->SetupAttachment(RootComponent);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Mesh(TEXT("/Game/Dungeons/IndustrialV1/Meshes/SM_ValveWheel.SM_ValveWheel"));
    if(Mesh.Succeeded())Valve->SetStaticMesh(Mesh.Object);
    Warning=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PressureWarning"));Warning->SetupAttachment(RootComponent);
    Release=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PressureRelease"));Release->SetupAttachment(RootComponent);
    for(auto* Component:{Valve.Get(),Warning.Get(),Release.Get()})
    {Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);Component->SetCanEverAffectNavigation(false);}
    Warning->SetCastShadow(false);Release->SetCastShadow(false);Warning->SetVisibility(false);Release->SetVisibility(false);
}

double AHeQuePumpControl::Clock() const
{
    if(const auto* State=GetWorld()->GetGameState())return State->GetServerWorldTimeSeconds();
    return GetWorld()->GetTimeSeconds();
}

void AHeQuePumpControl::Configure(AHeQueMonster* InBoss,const FVector& InVentOrigin)
{Boss=InBoss;VentOrigin=InVentOrigin;OnRep_State();ForceNetUpdate();}

bool AHeQuePumpControl::CanActivate() const
{return IsValid(Boss)&&!Boss->Dead()&&Clock()>=Boss->PumpCooldownUntil;}

FString AHeQuePumpControl::Prompt() const
{
    if(!IsValid(Boss)||Boss->Dead())return TEXT("泄压阀 · 泵机停机");
    const double Age=ActivatedAt<0.?-1.:Clock()-ActivatedAt;
    if(Age>=0.&&Age<HeQuePumpControlTiming::WarningSeconds)return TEXT("泄压预警 · 将合阙引入地面圆环");
    if(Age>=HeQuePumpControlTiming::WarningSeconds&&Age<HeQuePumpControlTiming::WarningSeconds+HeQuePumpControlTiming::VentSeconds)return bCaught?TEXT("合阙失衡 · 趁机攻击悬心"):TEXT("正在泄压 · 引导合阙进入圆环");
    const int32 Remaining=FMath::CeilToInt(Boss->PumpCooldownUntil-Clock());
    return Remaining>0?FString::Printf(TEXT("泄压阀 · 共用冷却 %d 秒"),Remaining):TEXT("开启泄压阀 · 2.5 秒后释放压力");
}

bool AHeQuePumpControl::ActivateFrom(APlayerController* Controller)
{
    if(!HasAuthority()||!IsValid(Controller)||!CanActivate()||ColdSteelWorldInteraction::TraceTarget(Controller)!=this)return false;
    const APawn* Pawn=Controller->GetPawn();
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Health||Health->IsDead())return false;
    ActivatedAt=Clock();bCaught=false;bSoundPlayed=false;
    Boss->PumpCooldownUntil=ActivatedAt+HeQuePumpControlTiming::CooldownSeconds;Boss->ForceNetUpdate();
    OnRep_State();ForceNetUpdate();return true;
}

void AHeQuePumpControl::OnRep_State()
{
    if(IsValid(Boss)&&GetNetMode()!=NM_DedicatedServer)
    {
        Warning->SetStaticMesh(Boss->JumpWaveMesh);Release->SetStaticMesh(Boss->JumpImpactMesh);
        if(!WarningMID&&Boss->JumpWaveMaterial)WarningMID=Warning->CreateDynamicMaterialInstance(0,Boss->JumpWaveMaterial);
        if(!ReleaseMID&&Boss->JumpImpactMaterial)ReleaseMID=Release->CreateDynamicMaterialInstance(0,Boss->JumpImpactMaterial);
    }
    const double Age=Clock()-ActivatedAt;
    SetActorTickEnabled(ActivatedAt>=0.&&Age<HeQuePumpControlTiming::WarningSeconds+HeQuePumpControlTiming::VentSeconds);
    Present();
}

void AHeQuePumpControl::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const double Age=Clock()-ActivatedAt;
    if(HasAuthority()&&IsValid(Boss)&&!Boss->Dead()&&!bCaught&&Age>=HeQuePumpControlTiming::WarningSeconds&&Age<HeQuePumpControlTiming::WarningSeconds+HeQuePumpControlTiming::VentSeconds
        &&Boss->GetCharacterMovement()->IsMovingOnGround()
        &&FMath::Abs(Boss->GetNavAgentLocation().Z-VentOrigin.Z)<160.f
        &&FVector::DistSquared2D(Boss->GetActorLocation(),VentOrigin)<=FMath::Square(HeQuePumpControlTiming::Radius))
    {bCaught=true;Boss->ReceivePumpRelease();ForceNetUpdate();}
    Present();
    if(!IsValid(Boss)||Boss->Dead()||Age>=HeQuePumpControlTiming::WarningSeconds+HeQuePumpControlTiming::VentSeconds)SetActorTickEnabled(false);
}

void AHeQuePumpControl::Present()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const float Age=float(Clock()-ActivatedAt);
    const bool Active=IsValid(Boss)&&!Boss->Dead()&&ActivatedAt>=0.&&Age>=0.f&&Age<HeQuePumpControlTiming::WarningSeconds+HeQuePumpControlTiming::VentSeconds;
    Warning->SetVisibility(Active&&WarningMID);Release->SetVisibility(Active&&Age>=HeQuePumpControlTiming::WarningSeconds&&ReleaseMID);
    const FVector Point=VentOrigin+FVector(0,0,4);
    if(Active&&WarningMID)
    {
        Warning->SetWorldLocationAndRotation(Point,FRotator::ZeroRotator);Warning->SetWorldScale3D(FVector(HeQuePumpControlTiming::Radius/100.f,HeQuePumpControlTiming::Radius/100.f,1.f));
        WarningMID->SetScalarParameterValue(TEXT("WaveRadiusCm"),HeQuePumpControlTiming::Radius);
        WarningMID->SetScalarParameterValue(TEXT("PulseAlpha"),Age<HeQuePumpControlTiming::WarningSeconds?.55f+.2f*FMath::Sin(Age*10.f):.35f);
        WarningMID->SetScalarParameterValue(TEXT("PulsePhase"),Age);
        WarningMID->SetVectorParameterValue(TEXT("WaveOrigin"),FLinearColor(Point.X,Point.Y,Point.Z,0));
        WarningMID->SetVectorParameterValue(TEXT("GroundNormal"),FLinearColor(0,0,1,0));
    }
    if(Active&&Age>=HeQuePumpControlTiming::WarningSeconds&&ReleaseMID)
    {
        const float VentAge=Age-HeQuePumpControlTiming::WarningSeconds;
        Release->SetWorldLocationAndRotation(Point,FRotator::ZeroRotator);Release->SetWorldScale3D(FVector(6.f,6.f,2.f));
        ReleaseMID->SetScalarParameterValue(TEXT("PulseAlpha"),1.f-FMath::SmoothStep(1.2f,2.f,VentAge));
        ReleaseMID->SetScalarParameterValue(TEXT("PulsePhase"),VentAge);
        if(!bSoundPlayed&&VentAge<.35f&&Boss->RiftImpactSound)
        {UGameplayStatics::PlaySoundAtLocation(this,Boss->RiftImpactSound,Point,.65f,1.f,0.f,Boss->RiftAttenuation);bSoundPlayed=true;}
    }
    if(!Active)bSoundPlayed=false;
}

void AHeQuePumpControl::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AHeQuePumpControl,Boss);DOREPLIFETIME(AHeQuePumpControl,VentOrigin);
    DOREPLIFETIME(AHeQuePumpControl,ActivatedAt);DOREPLIFETIME(AHeQuePumpControl,bCaught);
}
