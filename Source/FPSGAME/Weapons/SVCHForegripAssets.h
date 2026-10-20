#pragma once
#include "SVCHWeaponAssets.h"
#include "SVDAttachments.h"

namespace SVCHForegripAssets
{
    inline FString ProfilePath(FName Family)
    {
        return Family==TEXT("base")?FString(SVCHWeaponAssets::ProfilePath)
            :TEXT("/Game/Weapons/SVCH/Replacement20261018/ForegripFit20261019/DA_SVCH_Grip_")+Family.ToString();
    }

    inline UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Rifle,
        UStaticMeshComponent* Part,const TCHAR* Family,bool Enabled)
    {
        if(!Enabled)
        {
            // Removed preview parts must not enter the replicated part schema.
            if(Part){Part->SetStaticMesh(nullptr);Part->SetVisibility(false);}
            return Part;
        }
        // Reuse the accepted grip bodies. The SVCH seat and hand profiles use
        // the same measured rigid transform; cancel the source root's 100x scale.
        auto* Asset=LoadObject<UStaticMesh>(nullptr,*SVDAttachments::MeshPath(Family));
        if(!Asset){if(Part)Part->SetVisibility(false);return Part;}
        if(!Part)
        {
            Part=NewObject<UStaticMeshComponent>(Owner);
            Part->SetupAttachment(Rifle,TEXT("WPN_root"));
            Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Part->SetCastShadow(false);Part->bReceivesDecals=false;Part->RegisterComponent();
        }
        if(Part->GetStaticMesh()!=Asset)Part->EmptyOverrideMaterials();
        Part->SetStaticMesh(Asset);
        Part->SetOnlyOwnerSee(Rifle->bOnlyOwnerSee);
        Part->SetFirstPersonPrimitiveType(Rifle->FirstPersonPrimitiveType);
        const FQuat SeatRotation(FVector::RightVector,FMath::DegreesToRadians(-5.f));
        const FVector SeatLocation=SeatRotation.RotateVector(FVector(-.305f,0.f,2.18f));
        Part->SetRelativeTransform(FTransform(SeatRotation,SeatLocation*.01f,FVector(.01f)));
        Part->SetVisibility(true);
        return Part;
    }
}
