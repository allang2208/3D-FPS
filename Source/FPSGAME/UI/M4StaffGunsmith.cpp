#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "ColdSteelMeleePreview.h"
#include "ColdSteelStaffPreview.h"
#include "ColdSteelStaffModificationUI.h"
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
    for(const auto& Field:ColdSteelStaffUI::Fields)
    {
        const double X=E->CraftEffect(A,Field.Key)*Field.Scale,Y=E->CraftEffect(B,Field.Key)*Field.Scale;
        if(!Field.bAlwaysInOverview&&FMath::IsNearlyZero(X,.00001)&&FMath::IsNearlyZero(Y,.00001))continue;
        const double Delta=Y-X;const bool Same=FMath::IsNearlyZero(Delta,.00001);
        const bool Lower=ColdSteelStaffUI::LowerBetter(Field,X,Y);
        Overview.Add({Field.Label,FString::Printf(TEXT("%.*f%s"),Field.Digits,X,Field.Unit),FString::Printf(TEXT("%.*f%s"),Field.Digits,Y,Field.Unit),
            Same?TEXT("—"):FString::Printf(TEXT("%+.*f%s"),Field.Digits,Delta,Field.Unit),Same?0:((Delta>0)!=Lower?1:-1)});
    }
    const FString BeforeSpecialty=ColdSteelStaffUI::SpecialtyName(ColdSteelStaffUI::Specialty(Was));
    const FString AfterSpecialty=ColdSteelStaffUI::SpecialtyName(ColdSteelStaffUI::Specialty(Model()->Draft()));
    Overview.Add({TEXT("杖头专精"),BeforeSpecialty,AfterSpecialty,BeforeSpecialty==AfterSpecialty?TEXT("—"):TEXT("已变更"),0});
    const auto BeforeCrown=ColdSteelStaffUI::Crown(Was),AfterCrown=ColdSteelStaffUI::Crown(Model()->Draft());
    Overview.Add({TEXT("杖冠状态"),BeforeCrown.Text,AfterCrown.Text,BeforeCrown.Text==AfterCrown.Text?TEXT("—"):TEXT("已变更"),
        BeforeCrown.bActive==AfterCrown.bActive?0:AfterCrown.bActive?1:-1});
    Overview.Add({TEXT("改造费用"),TEXT("免费"),TEXT("免费"),TEXT("—"),0});
    Overview.Add({TEXT("握持"),TEXT("单手主手"),TEXT("单手主手"),TEXT("—"),0});
}
