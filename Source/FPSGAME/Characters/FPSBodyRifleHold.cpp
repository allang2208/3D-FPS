#include "FPSBodyRifleHold.h"
#include "FPSBodyRifleStockContacts.h"
#include "FPSPlayerBodyTypes.h"
#include "../Weapons/AKMSovietCalibration.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Math/RotationMatrix.h"

FFPSBodyRifleHold BuildFPSBodyRifleHold(USkeletalMeshComponent& Weapon,const FFPSBodyWeapon& Definition)
{
    FFPSBodyRifleHold Hold;
    const auto* Asset=Weapon.GetSkeletalMeshAsset();
    if(!Asset||Definition.PoseFamily!=TEXT("Gun"))return Hold;
    const FVector* StockRoot=FPSBodyRifleStock::Find(Asset->GetPathName());
    if(!StockRoot||!Weapon.DoesSocketExist(TEXT("WPN_root"))||!Weapon.DoesSocketExist(TEXT("WPN_FrontSight"))||!Weapon.DoesSocketExist(TEXT("WPN_RearSight")))return Hold;
    const FTransform Root=Weapon.GetSocketTransform(TEXT("WPN_root"),RTS_Component);
    const FVector Up=Root.GetRotation().GetUpVector();
    const FVector Front=AKMSoviet::Matches(&Weapon)?Root.TransformPosition(AKMSoviet::Front):Weapon.GetSocketTransform(TEXT("WPN_FrontSight"),RTS_Component).GetLocation();
    const FVector Rear=AKMSoviet::Matches(&Weapon)?Root.TransformPosition(AKMSoviet::Rear):Weapon.GetSocketTransform(TEXT("WPN_RearSight"),RTS_Component).GetLocation();
    const FVector Forward=FVector::VectorPlaneProject(Front-Rear,Up).GetSafeNormal();
    if(Forward.IsNearlyZero())return Hold;
    FVector Stock=Root.TransformPosition(*StockRoot);
    const FVector Side=FVector::CrossProduct(Up,Forward).GetSafeNormal();
    for(const auto& Part:Definition.Parts)
    {
        const FString Name=Part.Mesh.ToSoftObjectPath().GetAssetName();
        if(!Part.bVisible||!Name.Contains(TEXT("Stock"))||Name.Contains(TEXT("Cheek")))continue;
        const auto* Mesh=Part.Mesh.LoadSynchronous();if(!Mesh)continue;
        // Replacement stocks are authored along their own axes. Project their
        // local bounds through the actual mount, including the FBX root scale.
        const FTransform Mount=Part.Socket.IsNone()?Part.RelativeTransform:
            Part.RelativeTransform*Weapon.GetSocketTransform(Part.Socket,RTS_Component);
        const FBox Box=Mesh->GetBoundingBox();FBox Projected(ForceInit);
        for(int32 I=0;I<8;++I)
        {
            const FVector V=Mount.TransformPosition(FVector(I&1?Box.Max.X:Box.Min.X,I&2?Box.Max.Y:Box.Min.Y,I&4?Box.Max.Z:Box.Min.Z));
            Projected+=FVector(FVector::DotProduct(V,Forward),FVector::DotProduct(V,Side),FVector::DotProduct(V,Up));
        }
        const FVector Center=Projected.GetCenter();
        Stock=Forward*Projected.Min.X+Side*Center.Y+Up*Center.Z;
        break;
    }
    const FTransform Mount=Weapon.GetRelativeTransform();
    Hold.StockInHand=Mount.TransformPosition(Stock);
    Hold.BarrelInHand=(Mount.GetRotation()*FRotationMatrix::MakeFromXZ(Forward,Up).ToQuat()).GetNormalized();
    Hold.bValid=true;
    return Hold;
}
