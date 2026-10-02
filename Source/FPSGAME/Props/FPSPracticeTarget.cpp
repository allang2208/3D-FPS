#include "FPSPracticeTarget.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    /** 命中数字默认色；大额命中（>=80）改橙；靶心暴击走猩红+放大。 */
    const FColor HitTextColor(255,196,64);
    const FColor HitTextColorBig(255,120,40);
    const FColor HitTextColorCrit(255,48,24);
    const FColor SignColor(240,235,220);
    constexpr float SignHeight=235.f;
    constexpr float FloatingRise=48.f;
    constexpr float FloatingFadeStart=.65f;
}

AFPSPracticeTarget::AFPSPracticeTarget()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.bStartWithTickEnabled=true;
    Root=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));SetRootComponent(Root);
    TargetMesh=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TargetMesh"));TargetMesh->SetupAttachment(Root);
    // 命中走 ECC_Visibility 弹道扫掠/射线 + ECC_Pawn 近战扫掠：BlockAll 同仓库宝箱的命中盒约定。
    TargetMesh->SetCollisionProfileName(TEXT("BlockAll"));
    TargetMesh->SetGenerateOverlapEvents(false);
    ConstructorHelpers::FObjectFinderOptional<UStaticMesh> MeshFinder(TEXT("/Game/Props/PracticeTarget20261002/SM_PracticeTarget.SM_PracticeTarget"));
    if(MeshFinder.Succeeded())TargetMesh->SetStaticMesh(MeshFinder.Get());
    DpsSign=CreateDefaultSubobject<UTextRenderComponent>(TEXT("DpsSign"));DpsSign->SetupAttachment(Root);
    DpsSign->SetRelativeLocation(FVector(0,0,SignHeight));
    DpsSign->SetHorizontalAlignment(EHorizTextAligment::EHTA_Center);
    DpsSign->SetVerticalAlignment(EVerticalTextAligment::EVRTA_TextBottom);
    DpsSign->SetWorldSize(13.f);
    DpsSign->SetTextRenderColor(SignColor);
    DpsSign->SetText(FText::FromString(TEXT("PRACTICE TARGET")));
    SetCanBeDamaged(true);
    SetReplicates(false);
}

void AFPSPracticeTarget::BeginPlay()
{
    Super::BeginPlay();
    if(MeshOverride)TargetMesh->SetStaticMesh(MeshOverride);
    else if(!TargetMesh->GetStaticMesh())
        if(auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Props/PracticeTarget20261002/SM_PracticeTarget.SM_PracticeTarget")))TargetMesh->SetStaticMesh(Mesh);
    OnTakePointDamage.AddDynamic(this,&AFPSPracticeTarget::OnPointDamage);
    OnTakeRadialDamage.AddDynamic(this,&AFPSPracticeTarget::OnRadialDamage);
    OnTakeAnyDamage.AddDynamic(this,&AFPSPracticeTarget::OnAnyDamage);
    UpdateSign();
}

void AFPSPracticeTarget::OnPointDamage(AActor*,float Damage,AController*,FVector HitLocation,UPrimitiveComponent*,FName,FVector ShotFromDirection,const UDamageType*,AActor*)
{
    LastTypedDamageFrame=GFrameCounter;
    RecordHit(Damage,HitLocation,IsBullseyeLocation(HitLocation));
    const FVector ToHit=(HitLocation-GetActorLocation()).GetSafeNormal();
    RockSign=FVector::DotProduct(ToHit,GetActorForwardVector())>=0.f?-1.f:1.f;
    RockAmplitude=FMath::Min(7.f,1.5f+Damage*.06f);
    RockPhase=0.f;
}

void AFPSPracticeTarget::OnRadialDamage(AActor*,float Damage,const UDamageType*,FVector Origin,const FHitResult& HitInfo,AController*,AActor*)
{
    LastTypedDamageFrame=GFrameCounter;
    // 爆炸/范围伤害：落点取命中分量点，缺失时退化为爆炸原点贴近靶面。
    const FVector Point=HitInfo.bBlockingHit?FVector(HitInfo.ImpactPoint):(Origin+GetActorForwardVector()*30.f);
    RecordHit(Damage,Point,IsBullseyeLocation(Point));
}

void AFPSPracticeTarget::OnAnyDamage(AActor*,float Damage,const UDamageType*,AController*,AActor*)
{
    // TakeDamage 同帧先派 Point/Radial 再派 Any——Any 只补非点/径向路径（通用 ApplyDamage、DoT）。
    if(LastTypedDamageFrame==GFrameCounter)return;
    RecordHit(Damage,GetActorLocation()+GetActorForwardVector()*30.f+FVector(0,0,140),false);
}

bool AFPSPracticeTarget::IsBullseyeLocation(const FVector& WorldPoint) const
{
    if(!TargetMesh)return false;
    const FVector Local=TargetMesh->GetComponentTransform().InverseTransformPosition(WorldPoint);
    const float Dz=Local.Z-BullseyeCenterZ;
    const float Radial=FMath::Sqrt(Local.Y*Local.Y+Dz*Dz);
    return Radial<=BullseyeRadius&&Local.X>=BullseyeMinX;
}

bool AFPSPracticeTarget::IsBullseyeHit(const FHitResult& Hit) const
{ return IsBullseyeLocation(Hit.ImpactPoint); }

void AFPSPracticeTarget::RecordHit(float Damage,const FVector& Point,bool bBullseye)
{
    if(Damage<=0.f)return;
    const double Now=GetWorld()?GetWorld()->GetTimeSeconds():0.;
    if(LastHitTime<0.||Now-LastHitTime>IdleResetSeconds)
    {TotalDamage=0.f;HitCount=0;SessionStart=Now;} // 空闲超时后重新开节
    LastHitTime=Now;
    TotalDamage+=Damage;++HitCount;
    RecentHits.Add({Now,Damage});
    while(RecentHits.Num()&&Now-RecentHits[0].Time>WindowSeconds)RecentHits.RemoveAt(0,1,EAllowShrinking::No);
    SpawnDamageText(Damage,Point,bBullseye);
    UpdateSign();
}

void AFPSPracticeTarget::SpawnDamageText(float Damage,const FVector& Point,bool bBullseye)
{
    auto* Text=NewObject<UTextRenderComponent>(this);
    Text->SetWorldLocation(Point+FVector(0,0,4));
    Text->SetText(FText::FromString(FString::Printf(TEXT("%.0f"),FMath::Max(1.f,Damage))));
    Text->SetTextRenderColor(bBullseye?HitTextColorCrit:Damage>=80.f?HitTextColorBig:HitTextColor);
    Text->SetHorizontalAlignment(EHorizTextAligment::EHTA_Center);
    Text->SetVerticalAlignment(EVerticalTextAligment::EVRTA_TextCenter);
    Text->SetWorldSize(bBullseye?21.f:15.f);
    Text->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Text->AttachToComponent(RootComponent,FAttachmentTransformRules::KeepWorldTransform);
    Text->RegisterComponent();
    Floating.Add({Text,Point,GetWorld()->GetTimeSeconds(),FMath::FRandRange(-14.f,14.f)});
    while(Floating.Num()>MaxFloatingTexts)
    {
        if(Floating[0].Text)Floating[0].Text->DestroyComponent();
        Floating.RemoveAt(0,1,EAllowShrinking::No);
    }
}

void AFPSPracticeTarget::UpdateSign()
{
    const double Now=GetWorld()?GetWorld()->GetTimeSeconds():0.;
    if(HitCount==0||SessionStart<0.){DpsSign->SetText(FText::FromString(TEXT("PRACTICE TARGET")));return;}
    const float Elapsed=FMath::Max(.25f,float(Now-SessionStart));
    const float Window=FMath::Min(WindowSeconds,Elapsed);
    float Sum=0;for(const auto& H:RecentHits)Sum+=H.Damage;
    const float Dps=Sum/FMath::Max(.1f,Window);
    DpsSign->SetText(FText::FromString(FString::Printf(TEXT("DPS %.0f  |  TOTAL %.0f  |  HITS %d"),Dps,TotalDamage,HitCount)));
}

void AFPSPracticeTarget::FaceCamera(USceneComponent* Component) const
{
    const APlayerCameraManager* Camera=UGameplayStatics::GetPlayerCameraManager(this,0);
    if(!Camera||!Component)return;
    const FVector Delta=Camera->GetCameraLocation()-Component->GetComponentLocation();
    if(Delta.SizeSquared2D()<1.f)return;
    // TextRender 可读面法线为本地 +X（顶点 TangentZ=(1,0,0)）：look-at 的 +X 对准相机即可。
    Component->SetWorldRotation(FRotator(0,Delta.Rotation().Yaw,0));
}

void AFPSPracticeTarget::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);
    UWorld* World=GetWorld();
    if(!World)return;
    const double Now=World->GetTimeSeconds();
    for(int32 Index=Floating.Num()-1;Index>=0;--Index)
    {
        auto& F=Floating[Index];
        const float T=F.Text?float(Now-F.SpawnTime)/FMath::Max(.01f,FloatingLifeSeconds):1.f;
        if(T>=1.f||!F.Text)
        {
            if(F.Text)F.Text->DestroyComponent();
            Floating.RemoveAt(Index,1,EAllowShrinking::No);
            continue;
        }
        F.Text->SetWorldLocation(F.Base+FVector(0,0,4.f+FloatingRise*T)+FVector(0,F.Drift*T,0));
        if(T>FloatingFadeStart)
        {
            const float A=1.f-(T-FloatingFadeStart)/(1.f-FloatingFadeStart);
            FColor Color=F.Text->TextRenderColor;Color.A=uint8(FMath::Clamp(A,0.f,1.f)*255.f);F.Text->SetTextRenderColor(Color);
        }
        FaceCamera(F.Text);
    }
    if(RockAmplitude>.01f)
    {
        RockPhase+=DeltaTime*30.f;RockAmplitude*=FMath::Exp(-6.f*DeltaTime);
        TargetMesh->SetRelativeRotation(FRotator(RockSign*RockAmplitude*FMath::Sin(RockPhase),0,0));
    }
    SignAccum+=DeltaTime;
    if(SignAccum>=.25f){SignAccum=0.f;UpdateSign();}
    FaceCamera(DpsSign);
}

void AFPSPracticeTarget::ResetSession()
{
    SessionStart=-1.;LastHitTime=-1.;TotalDamage=0.f;HitCount=0;RecentHits.Reset();
    for(auto& F:Floating)if(F.Text)F.Text->DestroyComponent();
    Floating.Reset();
    RockAmplitude=0.f;TargetMesh->SetRelativeRotation(FRotator::ZeroRotator);
    UpdateSign();
}
