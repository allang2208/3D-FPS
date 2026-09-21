#include "FPSHolyLightEffect.h"
#include "Components/SplineComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"

namespace
{
    using namespace UE::Geometry;
    constexpr float FadeInSeconds=.24f;
    constexpr float MinimumFadeOutSeconds=.75f;
    void Vertex(FDynamicMesh3& Mesh,const FVector3d& Position,const FVector3f& Normal,const FVector2f& UV)
    {Mesh.AppendVertex(Position);Mesh.Attributes()->PrimaryNormals()->AppendElement(Normal);Mesh.Attributes()->PrimaryUV()->AppendElement(UV);}
    void Triangle(FDynamicMesh3& Mesh,int32 A,int32 B,int32 C)
    {const int32 Id=Mesh.AppendTriangle(A,B,C);Mesh.Attributes()->PrimaryNormals()->SetTriangle(Id,FIndex3i(A,B,C));Mesh.Attributes()->PrimaryUV()->SetTriangle(Id,FIndex3i(A,B,C));}
    FDynamicMesh3 Column(float Bottom,float Top,float Height)
    {
        FDynamicMesh3 Mesh;Mesh.EnableAttributes();constexpr int32 Sides=48;
        for(int32 Row=0;Row<=1;++Row)for(int32 I=0;I<=Sides;++I)
        {
            const float U=float(I)/Sides,A=U*2*PI,R=Row?Top:Bottom;
            const FVector3f N(FMath::Cos(A),FMath::Sin(A),0);
            Vertex(Mesh,FVector3d(N.X*R,N.Y*R,Row*Height),N,FVector2f(U,Row));
        }
        for(int32 I=0;I<Sides;++I){Triangle(Mesh,I,I+1,I+Sides+2);Triangle(Mesh,I,I+Sides+2,I+Sides+1);}
        return Mesh;
    }
    FDynamicMesh3 Disc(float Radius)
    {
        FDynamicMesh3 Mesh;Mesh.EnableAttributes();
        Vertex(Mesh,{-Radius,-Radius,2},{0,0,1},{0,0});Vertex(Mesh,{Radius,-Radius,2},{0,0,1},{1,0});
        Vertex(Mesh,{Radius,Radius,2},{0,0,1},{1,1});Vertex(Mesh,{-Radius,Radius,2},{0,0,1},{0,1});
        Triangle(Mesh,0,1,2);Triangle(Mesh,0,2,3);return Mesh;
    }
}
AFPSHolyLightEffect::AFPSHolyLightEffect()
{
    PrimaryActorTick.bCanEverTick=true;SetActorEnableCollision(false);
    Path=CreateDefaultSubobject<USplineComponent>(TEXT("HolyMotePath"));SetRootComponent(Path);
    Beam=CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("GoldenBeam"));
    Core=CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("PlatinumCore"));
    Pool=CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("GroundPool"));
    for(auto* Mesh:{Beam.Get(),Core.Get(),Pool.Get()})
    {Mesh->SetupAttachment(Path);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCastShadow(false);Mesh->SetGenerateOverlapEvents(false);}
    Motes=CreateDefaultSubobject<UNiagaraComponent>(TEXT("RisingMotes"));Motes->SetupAttachment(Path);Motes->SetAutoActivate(false);
    Light=CreateDefaultSubobject<UPointLightComponent>(TEXT("HolyFill"));Light->SetupAttachment(Path);Light->SetCastShadows(false);Light->SetIntensity(0);Light->SetAttenuationRadius(300);
    Light->SetLightColor(FLinearColor(1,.68f,.24f));Light->SetRelativeLocation(FVector(0,0,70));
}
void AFPSHolyLightEffect::InitializeLight(AActor* Target,UNiagaraSystem* System,const FHolyLightCast& Spell)
{
    FollowTarget=Target;Settings=Spell;Age=0;
    // The longer visual tail does not change the spell's contact or gameplay clock.
    Settings.Fade=FMath::Max(Settings.Fade,MinimumFadeOutSeconds);
    if(auto* Capsule=Target->FindComponentByClass<UCapsuleComponent>())FootOffset=-Capsule->GetScaledCapsuleHalfHeight();
    else {FVector Origin,Extent;Target->GetActorBounds(true,Origin,Extent);FootOffset=Origin.Z-Extent.Z-Target->GetActorLocation().Z;}
    SetActorLocation(Target->GetActorLocation()+FVector(0,0,FootOffset));
    // The outer shell carries soft spill; the broad, dimmer core avoids a laser-like line.
    Beam->SetMesh(Column(Spell.BottomWidth*.6f,Spell.TopWidth*.6f,Spell.Height));
    Core->SetMesh(Column(Spell.BottomWidth*.28f,Spell.TopWidth*.28f,Spell.Height));Pool->SetMesh(Disc((Spell.BottomWidth+60)*.5f));
    auto Bind=[&](UDynamicMeshComponent* Mesh,const TCHAR* Name,FLinearColor Color,float Opacity,float Intensity)
    {
        auto* Source=LoadObject<UMaterialInterface>(nullptr,*FString::Printf(TEXT("/Game/Skills/HolyLight/%s.%s"),Name,Name));
        if(!Source)return;
        auto* MID=UMaterialInstanceDynamic::Create(Source,this);Mesh->SetMaterial(0,MID);Materials.Add(MID);
        MID->SetVectorParameterValue(TEXT("HolyColor"),Color);MID->SetScalarParameterValue(TEXT("OpacityScale"),Opacity);
        MID->SetScalarParameterValue(TEXT("Intensity"),Intensity);MID->SetScalarParameterValue(TEXT("DissolveRatio"),Spell.DissolveRatio);
        MID->SetScalarParameterValue(TEXT("Fade"),0);MID->SetScalarParameterValue(TEXT("EffectAge"),0);
    };
    Bind(Beam,TEXT("M_HolyBeam"),FLinearColor(1,.66f,.24f),.23f,8);
    Bind(Core,TEXT("M_HolyBeam"),FLinearColor(1,.92f,.70f),.18f,8);
    Bind(Pool,TEXT("M_HolyPool"),FLinearColor(1,.68f,.28f),.24f,7);
    Path->ClearSplinePoints(false);
    for(int32 I=0;I<16;++I){const float A=2*PI*I/16;Path->AddSplinePoint(FVector(FMath::Cos(A),FMath::Sin(A),0)*Spell.BottomWidth*.3f+FVector(0,0,75),ESplineCoordinateSpace::Local,false);}
    Path->SetClosedLoop(true,true);
    Motes->SetAsset(System);Motes->SetVariableBool(TEXT("User._AdaptTerrain"),false);
    Motes->SetVariableBool(TEXT("User.AddDetail"),true);Motes->SetVariableBool(TEXT("User.DecalON"),false);Motes->SetVariableBool(TEXT("User.LightON"),false);
    Motes->SetVariableFloat(TEXT("User.Progress"),0);Motes->SetVariableFloat(TEXT("User._Brightness"),0);
    Motes->SetVariableFloat(TEXT("User._Size"),1);Motes->SetVariableFloat(TEXT("User.Extent"),10);Motes->SetVariableFloat(TEXT("User.Tall"),1);
    Light->SetIntensity(0);
    Motes->Activate(true);SetLifeSpan(Settings.Duration+Settings.Fade+.1f);
}
void AFPSHolyLightEffect::Tick(float Delta)
{
    Super::Tick(Delta);Age+=Delta;
    if(FollowTarget.IsValid())SetActorLocation(FollowTarget->GetActorLocation()+FVector(0,0,FootOffset));
    const float FadeIn=FMath::SmoothStep(0.f,FadeInSeconds,Age);
    const float FadeOut=1-FMath::SmoothStep(Settings.Duration,Settings.Duration+Settings.Fade,Age);
    const float Fade=FadeIn*FadeOut;
    const float Pulse=.97f+.03f*FMath::Sin(Age*2.2f);
    for(auto& MID:Materials)if(MID)
    {MID->SetScalarParameterValue(TEXT("Fade"),Fade*Pulse);MID->SetScalarParameterValue(TEXT("EffectAge"),Age);}
    Motes->SetVariableFloat(TEXT("User._Brightness"),20*Fade);
    Motes->SetVariableFloat(TEXT("User.Progress"),Age<Settings.Duration?FadeIn:0);
    Light->SetIntensity(1200*Fade*Pulse);
    if(Age>=Settings.Duration+Settings.Fade)Destroy();
}
