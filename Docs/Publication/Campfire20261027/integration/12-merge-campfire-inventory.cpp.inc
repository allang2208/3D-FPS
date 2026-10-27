        if(bCampfireInventoryChanged)
        {
            auto ServerItems=Save->Profile.Items;
            // Campfire materials never modify loaded ammunition. Preserve firing since upload.
            for(auto& I:ServerItems)if(const auto* Local=Merged.Items.FindByPredicate([&](const auto& E){return E.InstanceId==I.InstanceId;}))
            ColdSteelProfileRecovery::LoadedAmmo(I,*Local);
            Merged.Items=MoveTemp(ServerItems);Merged.CampfireInventoryRevision=Save->Profile.CampfireInventoryRevision;
            Merged.ActiveWeaponSlot=Save->Profile.ActiveWeaponSlot;Merged.ActiveProductionTool=Save->Profile.ActiveProductionTool;
            Merged.AmmoPouch=Save->Profile.AmmoPouch;
            Merged.CampfireWorldReceipts=Save->Profile.CampfireWorldReceipts;
        }
