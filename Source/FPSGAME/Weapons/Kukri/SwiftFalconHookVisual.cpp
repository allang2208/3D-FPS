#include "SwiftFalconHookVisual.h"
#include "KukriWeaponComponent.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

USwiftFalconHookVisual::USwiftFalconHookVisual()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
    SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SetCastShadow(false);SetCanEverAffectNavigation(false);bVisibleInRayTracing=false;
    SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Mat(TEXT("/Game/Weapons/TacticalHatchet20261101/SwiftFalconLegendary/Hook/M_FalconHookFilament"));
    static ConstructorHelpers::FObjectFinder<USoundBase> Catch(TEXT("/Game/Weapons/TacticalHatchet20261101/SwiftFalconLegendary/Hook/SW_FalconHookBite"));
    static ConstructorHelpers::FObjectFinder<USoundBase> Release(TEXT("/Game/Weapons/TacticalHatchet20261101/SwiftFalconLegendary/Hook/SW_FalconHookSnap"));
    Filament=Mat.Object;Bite=Catch.Object;Snap=Release.Object;
}

void USwiftFalconHookVisual::FindHead()
{
    auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn)return;
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool WorldOnly=!Pawn->IsLocallyControlled()||(Body&&Body->IsThirdPersonViewEnabled());
    TArray<USceneComponent*> Parts;
    if(!WorldOnly)
        if(auto* K=Pawn->FindComponentByClass<UKukriWeaponComponent>())
            if(auto* Root=K->WeaponMesh(bLeft))
            {Parts.Add(Root);Root->GetChildrenComponents(true,Parts);}
    if(Body)
    {
        TArray<FFPSWeatherWeaponMesh> Equipment;
        Body->GetWeatherWeaponMeshes(Equipment,WorldOnly);
        for(const auto& E:Equipment)if(E.Instance==WeaponInstance)Parts.AddUnique(E.Mesh);
    }
    for(auto* Part:Parts)
    {
        auto* Mesh=Cast<UStaticMeshComponent>(Part);
        if(!Mesh||!Mesh->GetStaticMesh()||!Mesh->GetStaticMesh()->GetName().Equals(TEXT("SM_TacticalHatchet_Head_SwiftFalcon")))continue;
        Head=Mesh;PreviousSteel=Mesh->GetMaterial(0);
        Steel=Mesh->CreateDynamicMaterialInstance(0,PreviousSteel);
        return;
    }
}

void USwiftFalconHookVisual::Bind(AActor* Victim,FVector HitPoint,FName Bone,const FString& Weapon,float Hold,bool Left)
{
    Target=Victim;WeaponInstance=Weapon;HoldSeconds=FMath::Max(.05f,Hold);bLeft=Left;
    Skin=Victim->FindComponentByClass<USkeletalMeshComponent>();
    FTransform Surface=Victim->GetActorTransform();
    if(auto* Mesh=Skin.Get())
    {
        AnchorBone=Mesh->DoesSocketExist(Bone)?Bone:Mesh->FindClosestBone(HitPoint);
        Surface=Mesh->GetSocketTransform(AnchorBone);
    }
    LocalPoint=Surface.InverseTransformPosition(HitPoint);
    const FVector Normal=(GetOwner()->GetActorLocation()-Victim->GetActorLocation()).GetSafeNormal2D();
    LocalNormal=Surface.InverseTransformVectorNoScale(Normal);
    LocalAcross=Surface.InverseTransformVectorNoScale(FVector::CrossProduct(FVector::UpVector,Normal));
    SetWorldLocation(HitPoint);FindHead();
    if(Filament){Light=UMaterialInstanceDynamic::Create(Filament,this);SetMaterial(0,Light);}
    if(Bite)UGameplayStatics::PlaySoundAtLocation(this,Bite,HitPoint,.65f,bLeft?.94f:1.f);
}

FVector USwiftFalconHookVisual::Anchor() const
{
    if(auto* Mesh=Skin.Get())return Mesh->GetSocketTransform(AnchorBone).TransformPosition(LocalPoint);
    return Target->GetActorTransform().TransformPosition(LocalPoint);
}

void USwiftFalconHookVisual::Draw(float SecondsToSnap,bool Shared,bool PlaySnap,bool bTug)
{
    if(DrawAge>=0.f)return;
    DrawAge=0.f;SnapAt=FMath::Max(.02f,SecondsToSnap);bShared=Shared;bPlaySnap=PlaySnap;
    if(bTug&&Target.IsValid())
        if(auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>())
            Combat->ShowFalconTug(GetOwner()->GetActorLocation()-Target->GetActorLocation(),Anchor());
}

void USwiftFalconHookVisual::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    Age+=Delta;
    if(DrawAge>=0.f)DrawAge+=Delta;
    if(!Target.IsValid()||!GetOwner()||Age>HoldSeconds+1.f||DrawAge>SnapAt+.15f)
    {DestroyComponent();return;}
    if(!Head.IsValid()&&DrawAge<0.f&&Age>=NextHeadLookup)
    {FindHead();NextHeadLookup=Age+.08f;}
    if(Steel)Steel->SetScalarParameterValue(TEXT("FalconHookPhase"),DrawAge<0?FMath::Clamp(Age/HoldSeconds,0.f,1.f):1.f);
    const FVector Point=Anchor();SetWorldLocation(Point);
    FVector Eye;FRotator View;GetOwner()->GetActorEyesViewPoint(Eye,View);
    FVector Tip=Eye+View.Vector()*30.+FRotationMatrix(View).GetUnitAxis(EAxis::Y)*(bLeft?-16.:16.);
    if(auto* Blade=Head.Get())Tip=Blade->GetComponentTransform().TransformPosition(FVector(17.05,0,27.03));
    const FVector Toward=(Eye-Point).GetSafeNormal();
    const FTransform Surface=Skin.IsValid()?Skin->GetSocketTransform(AnchorBone):Target->GetActorTransform();
    const FVector Normal=Surface.TransformVectorNoScale(LocalNormal);
    const FVector Across=Surface.TransformVectorNoScale(LocalAcross);
    const FVector Up=FVector::CrossProduct(Normal,Across);
    // Make the claws follow the hit bone. The thin arc has a single tension bend and snaps into tapered chips.
    UE::Geometry::FDynamicMesh3 Geometry;
    auto Strip=[&](FVector A,FVector B,double WidthA,double WidthB)
    {
        FVector Side=FVector::CrossProduct((B-A).GetSafeNormal(),Toward).GetSafeNormal();
        if(Side.IsNearlyZero())Side=Across;
        const int32 I=Geometry.AppendVertex(A+Side*WidthA);
        Geometry.AppendVertex(A-Side*WidthA);Geometry.AppendVertex(B+Side*WidthB);Geometry.AppendVertex(B-Side*WidthB);
        Geometry.AppendTriangle(I,I+1,I+2);Geometry.AppendTriangle(I+2,I+1,I+3);
    };
    const float After=FMath::Max(0.f,DrawAge-SnapAt);
    const float Fade=1.f-FMath::Clamp(After/.15f,0.f,1.f);
    const FVector Lift=Normal*1.7;
    for(int32 I=0;I<2;++I)
    {
        const FVector Base=Lift+Across*((I-.5)*2.5+(bLeft?-1.:1.)*1.7);
        const FVector Bend=Base+Across*1.2;
        Strip(Base+Up*5.-Across,Bend,.06,.65*Fade);
        Strip(Bend,Base-Up*2.8-Across*1.3,.65*Fade,.04);
    }
    if(DrawAge>=0.f && DrawAge<SnapAt)
    {
        const FVector End=Tip-Point;
        const FVector Bend=End*.55+Up*(2.5*(1.-DrawAge/SnapAt));
        Strip(Lift,Bend,.25,.60);Strip(Bend,End,.60,.12);
    }
    if(DrawAge>=SnapAt)
    {
        if(!bSnapped && bPlaySnap && Snap)
            UGameplayStatics::PlaySoundAtLocation(this,Snap,Point,bShared?1.f:.78f,bShared?.76f:1.f);
        bSnapped=true;
        for(int32 I=0;I<5;++I)
        {
            const FVector Direction=((Tip-Point).GetSafeNormal()+Across*((I-2)*.30)+Up*(.45*FMath::Cos(I*2.4))).GetSafeNormal();
            const FVector Chip=Lift+Direction*(After*(120.+I*20.))-FVector::UpVector*(230.*After*After);
            Strip(Chip,Chip+Direction*(2.8*Fade),.37*Fade,.02);
        }
    }
    if(Light)Light->SetVectorParameterValue(TEXT("Light"),FLinearColor(.11f,3.8f,3.4f)*Fade*(DrawAge>=0.f?1.45f:1.f));
    SetMesh(MoveTemp(Geometry));
}

void USwiftFalconHookVisual::OnComponentDestroyed(bool bDestroyingHierarchy)
{
    if(auto* Mesh=Head.Get(); Mesh&&Steel&&Mesh->GetMaterial(0)==Steel)Mesh->SetMaterial(0,PreviousSteel);
    Super::OnComponentDestroyed(bDestroyingHierarchy);
}
