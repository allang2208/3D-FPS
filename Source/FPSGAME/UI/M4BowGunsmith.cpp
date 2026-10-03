#include "ColdSteelWeaponText.h"
#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelMeleePreview.h"
#include "../Weapons/Bow/BowAssembly.h"
#include "../Weapons/Bow/BowStats.h"
#include "Engine/GameInstance.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"

bool UM4GunsmithWidget::IsBowWorkbench() const{return Model()->IsBow(Model()->Definition());}
void UM4GunsmithWidget::SetStandaloneBowItem(const FColdSteelItem& Item)
{
    const bool Draft=Model()->IsOpen()&&Model()->Instance()==Item.InstanceId;
    const auto Parts=Draft?Model()->Draft():Model()->Installed(Item);
    TArray<FString> Names;Parts.GetKeys(Names);Names.Sort();
    FString Input=Item.InstanceId+FString::Printf(TEXT("|%u"),GetTypeHash(Item.Data));
    for(const auto& N:Names)Input+=TEXT("|")+N+TEXT("=")+Parts[N];
    if(Input==BowPreviewInputKey)return;
    const bool Created=!ColdSteelBowAssembly::IsBowRoot(StandaloneMelee);
    if(Created)
    {
        CloseStandalonePreview();InitializePreview();if(!Capture)return;
        StandaloneMelee=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
        StandaloneMelee->ComponentTags.Add(TEXT("BowAssembly"));StandaloneMelee->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Studio->AddComponent(StandaloneMelee,FTransform::Identity);
    }
    if(BowPreviewLoad){BowPreviewLoad->CancelHandle();BowPreviewLoad.Reset();}
    BowPreviewInputKey=Input;
    const auto Resolved=Model()->ResolveBowVisual(Item,&Parts);
    TArray<FSoftObjectPath> Paths;ColdSteelBowAssembly::GatherResources(Resolved,Paths);
    BowPreviewLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Input,Resolved,Parts,Created]()
    {
        if(Input!=BowPreviewInputKey||!Studio||!StandaloneMelee)return;
        if(!ColdSteelBowAssembly::Apply(StandaloneMelee,Resolved)){StatusText=TEXT("弓部件资源尚未加载，重新打开改造台可重试");return;}
        StandaloneKey=Resolved.InstanceId+TEXT("|")+ColdSteelBowAssembly::Key(Resolved);StandaloneParts=Parts;
        bPreviewStreamingDirty=true;PreviewMotion=1.f;CaptureAccumulator=1.f;
        if(Created)SetSidePreview(true);else SyncStandaloneBowPreview();
    }));
}
void UM4GunsmithWidget::SyncStandaloneBowPreview()
{
    if(!Capture||!ColdSteelBowAssembly::IsBowRoot(StandaloneMelee))return;
    const FBox Bounds=ColdSteelBowAssembly::LocalBounds(StandaloneMelee);const FQuat Base=ColdSteelBowAssembly::Rotation();
    if(!Bounds.IsValid)return;
    const FQuat Turn(FVector::UpVector,FMath::DegreesToRadians(PreviewOrbit.X)),Tilt(FVector::RightVector,FMath::DegreesToRadians(PreviewOrbit.Y));
    StandaloneMelee->SetWorldTransform(ColdSteelMeleePreview::Pose(Bounds,Turn*Tilt*Base));
    Capture->ShowOnlyComponents.Reset();for(auto* C:ColdSteelBowAssembly::Components(StandaloneMelee))Capture->ShowOnlyComponent(C);
    Capture->SetWorldTransform(FTransform::Identity);Capture->ProjectionType=ECameraProjectionMode::Orthographic;
    const float Aspect=float(PreviewTarget->SizeX)/FMath::Max(1,PreviewTarget->SizeY);
    const FVector Size=Bounds.TransformBy(FTransform(Base)).GetSize();
    Capture->OrthoWidth=FMath::Max(30.f,FMath::Max(float(Size.Y)/.84f,float(Size.Z)*Aspect/.60f))/PreviewZoom;
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;
    Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(Capture->OrthoWidth*.5f,Capture->OrthoWidth*.5f/Aspect,1.f/2000.f,-.1f);
}
void UM4GunsmithWidget::AppendBowOverview(const FColdSteelItem& Item)
{
    const auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto Parts=bCompareFactory?FGunsmithParts():Model()->Installed(Item);
    const auto A=ColdSteelBow::Evaluate(Item,P,&Parts),B=ColdSteelBow::Evaluate(Item,P,&Model()->Draft());
    auto Row=[&](const TCHAR* Name,double Before,double After,int32 Digits,const TCHAR* Unit,bool Lower=false)
    {
        const double D=After-Before;const bool Same=FMath::Abs(D)<.00001;
        Overview.Add({Name,FString::Printf(TEXT("%.*f%s"),Digits,Before,Unit),FString::Printf(TEXT("%.*f%s"),Digits,After,Unit),
            Same?TEXT("—"):FString::Printf(TEXT("%+.*f%s"),Digits,D,Unit),Same?0:((D>0)!=Lower?1:-1)});
    };
    Row(ColdSteelWeaponText::TotalDamage,A.Damage.Total(),B.Damage.Total(),2,TEXT(""));
    Row(ColdSteelWeaponText::BasePhysical,A.Damage.BasePhysical,B.Damage.BasePhysical,2,TEXT(""));
    if(A.Damage.AddedPhysical>0||B.Damage.AddedPhysical>0)Row(ColdSteelWeaponText::AddedPhysical,A.Damage.AddedPhysical,B.Damage.AddedPhysical,2,TEXT(""));
    if(A.Damage.AddedMagic>0||B.Damage.AddedMagic>0)Row(ColdSteelWeaponText::AddedMagic,A.Damage.AddedMagic,B.Damage.AddedMagic,2,TEXT(""));
    Row(ColdSteelWeaponText::DrawTime,A.Draw,B.Draw,2,TEXT(" s"),true);Row(ColdSteelWeaponText::NockTime,A.Nock,B.Nock,2,TEXT(" s"),true);
    Row(TEXT("拉弓速度加成"),A.DrawSpeedBonus*100.,B.DrawSpeedBonus*100.,1,TEXT("%"));
    Row(ColdSteelWeaponText::ProjectileSpeed,A.Speed,B.Speed,1,TEXT(" m/s"));Row(ColdSteelWeaponText::StaminaCost,A.Stamina,B.Stamina,2,TEXT(""),true);
    Row(ColdSteelWeaponText::HoldTime,A.Hold,B.Hold,2,TEXT(" s"));Row(ColdSteelWeaponText::Sway,A.Sway,B.Sway,2,TEXT(""),true);
    Row(ColdSteelWeaponText::HipSpreadAngle,FMath::RadiansToDegrees(FMath::Atan(A.Spread)),FMath::RadiansToDegrees(FMath::Atan(B.Spread)),2,TEXT("°"),true);
    Row(ColdSteelWeaponText::ADS,A.ADS*1000,B.ADS*1000,0,TEXT(" ms"),true);
    Overview.Add({TEXT("伤害条件"),TEXT("满弓单箭"),TEXT("满弓单箭"),TEXT("—"),0});
    Overview.Add({TEXT("握持"),TEXT("双手 · 占用副手"),TEXT("双手 · 占用副手"),TEXT("—"),0});
}
