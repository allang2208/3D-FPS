void UStaffWeaponComponent::ConfigureIllumination(const FColdSteelItem& Resolved)
{
    // Resolve the actual installed head once, so every crystal option works and
    // wood, bindings and other copies of shared elemental materials stay unchanged.
    bCanIlluminate=Resolved.Definition==TEXT("ue_apprentice_staff");
    if(!bCanIlluminate||!Staff)return;
    const FString HeadPath=ColdSteelInventory::Text(Resolved,TEXT("staff_part_head_crystal_mesh"));
    UStaticMeshComponent* Head=nullptr;
    for(auto* Part:ColdSteelStaffAssembly::Components(Staff))
        if(Part->GetStaticMesh()&&Part->GetStaticMesh()->GetPathName()==HeadPath){Head=Part;break;}
    if(!Head){bCanIlluminate=false;return;}
    for(int32 Slot=0;Slot<Head->GetNumMaterials();++Slot)
    {
        auto* Material=Head->GetMaterial(Slot);float Value=0.f;
        if(!Material||!Material->GetScalarParameterValue(FMaterialParameterInfo(StaffIllumination::AmountParameter),Value))continue;
        if(auto* Dynamic=Head->CreateDynamicMaterialInstance(Slot))
        {
            Dynamic->SetScalarParameterValue(StaffIllumination::AmountParameter,0.f);
            CrystalLightMaterials.Add(Dynamic);
        }
    }
    if(!CrystalLight)
    {
        CrystalLight=NewObject<UPointLightComponent>(GetOwner(),TEXT("StaffCrystalLight"));
        GetOwner()->AddInstanceComponent(CrystalLight);
        CrystalLight->SetupAttachment(Staff);
        CrystalLight->SetMobility(EComponentMobility::Movable);
        UStaffIlluminationProfile::ApplyToPointLight(CrystalLight, 0.f);
        CrystalLight->SetVisibility(false);
        CrystalLight->RegisterComponent();
    }
    const FVector HeadCenter=Head->GetRelativeTransform().TransformPosition(Head->GetStaticMesh()->GetBoundingBox().GetCenter());
    CrystalLight->SetRelativeLocation(HeadCenter);
    PublishedIllumination=-1.f;
    UpdateIllumination(0.f);
    PublishIllumination();
}
