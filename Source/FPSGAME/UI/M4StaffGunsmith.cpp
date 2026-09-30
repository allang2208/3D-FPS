#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "ColdSteelMeleePreview.h"
#include "ColdSteelStaffPreview.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "../Weapons/Staff/StaffAssembly.h"
#include "Engine/GameInstance.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"

bool UM4GunsmithWidget::IsStaffWorkbench() const{return Model()->IsStaff(Model()->Definition());}
void UM4GunsmithWidget::SyncStandaloneStaffPreview()
{
    if(!Capture||!StandaloneMelee||!StandaloneMelee->GetStaticMesh())return;
    const FBox B=ColdSteelStaffAssembly::Bounds(StandaloneMelee);const FQuat Base=ColdSteelMeleePreview::Rotation(B);
    const FQuat Turn(FVector::UpVector,FMath::DegreesToRadians(PreviewOrbit.X)),Tilt(FVector::RightVector,FMath::DegreesToRadians(PreviewOrbit.Y));
    StandaloneMelee->SetWorldTransform(ColdSteelMeleePreview::Pose(B,Turn*Tilt*Base));
    Capture->ShowOnlyComponents.Reset();for(auto* C:ColdSteelStaffAssembly::Components(StandaloneMelee))Capture->ShowOnlyComponent(C);
    Capture->SetWorldTransform(FTransform::Identity);Capture->ProjectionType=ECameraProjectionMode::Orthographic;
    const float Aspect=float(PreviewTarget->SizeX)/FMath::Max(1,PreviewTarget->SizeY);
    const FVector Size=B.TransformBy(FTransform(Base)).GetSize();
    Capture->OrthoWidth=FMath::Max(30.f,FMath::Max(float(Size.Y)/.84f,float(Size.Z)*Aspect/.6f))/PreviewZoom;
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;
    Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(Capture->OrthoWidth*.5f,Capture->OrthoWidth*.5f/Aspect,1.f/2000.f,-.1f);
}
void UM4GunsmithWidget::SetStandaloneStaffItem(const FColdSteelItem& Item)
{
    const auto R=ColdSteelStaff::Resolve(Item,&Model()->Draft());const FString Key=Item.InstanceId+TEXT("|")+R.Data;
    if(BowPreviewInputKey==Key)return;
    if(!StandaloneMelee||!StandaloneMelee->ComponentHasTag(TEXT("StaffAssembly")))
    {
        CloseStandalonePreview();InitializePreview();if(!Capture)return;
        StandaloneMelee=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
        StandaloneMelee->ComponentTags.Add(TEXT("StaffAssembly"));StandaloneMelee->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Studio->AddComponent(StandaloneMelee,FTransform::Identity);
    }
    if(BowPreviewLoad){BowPreviewLoad->CancelHandle();BowPreviewLoad.Reset();}
    BowPreviewInputKey=Key;TArray<FSoftObjectPath> Paths;ColdSteelStaffAssembly::Gather(R,Paths);
    Paths.AddUnique(ColdSteelStaffPreview::QuartzMaterialPath());
    BowPreviewLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Key,R]()
    {
        if(BowPreviewInputKey!=Key||!StandaloneMelee)return;
        if(!ColdSteelStaffAssembly::Apply(StandaloneMelee,R)){StatusText=TEXT("长杖部件未加载，请重新打开改造台重试");return;}
        if(!ColdSteelStaffPreview::ApplyMaterials(StandaloneMelee)){StatusText=TEXT("长杖预览水晶材质未加载，请重新打开改造台重试");return;}
        StandaloneKey=Key;bPreviewStreamingDirty=true;PreviewMotion=1;SetSidePreview(true);
    }));
}
void UM4GunsmithWidget::AppendStaffOverview(const FColdSteelItem& Item)
{
    auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();const auto Was=bCompareFactory?FGunsmithParts():Model()->Installed(Item);
    const auto A=ColdSteelStaff::Resolve(Item,&Was),B=ColdSteelStaff::Resolve(Item,&Model()->Draft());
    const TPair<const TCHAR*,const TCHAR*> Fields[]={
        {TEXT("magicDamagePercent"),TEXT("法术伤害加成")},{TEXT("fireDamagePercent"),TEXT("已激活火系加成")},
        {TEXT("iceDamagePercent"),TEXT("已激活冰系加成")},{TEXT("electricDamagePercent"),TEXT("已激活电系加成")},
        {TEXT("lightHealPercent"),TEXT("已激活光系治疗加成")},{TEXT("magicCritPercent"),TEXT("法术暴击加成")},
        {TEXT("magicMpCostPercent"),TEXT("法术耗蓝增减")},{TEXT("magicRangePercent"),TEXT("法术距离加成")},
        {TEXT("magicCooldownPercent"),TEXT("法术冷却缩减")},{TEXT("castSpeedPercent"),TEXT("施法速度加成")}};
    for(const auto& F:Fields)
    {const double X=E->CraftEffect(A,F.Key)*100,Y=E->CraftEffect(B,F.Key)*100;
        Overview.Add({F.Value,FString::Printf(TEXT("%g%%"),X),FString::Printf(TEXT("%g%%"),Y),FString::Printf(TEXT("%+g%%"),Y-X),0});}
    Overview.Add({TEXT("改造费用"),TEXT("免费"),TEXT("免费"),TEXT("应用后保存"),0});
    Overview.Add({TEXT("杖冠条件"),TEXT("匹配杖头专精"),TEXT("不匹配保留外观，数值不生效"),TEXT("—"),0});
    Overview.Add({TEXT("握持"),TEXT("单手主手"),TEXT("副手可持盾或魔法书"),TEXT("—"),0});
}
