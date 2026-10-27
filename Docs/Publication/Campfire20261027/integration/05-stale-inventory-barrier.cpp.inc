        const bool KeepServerPouch=bRestoreGuestAmmo||Adopted.CampfireInventoryRevision!=Prev.CampfireInventoryRevision;
        if(Adopted.CampfireInventoryRevision!=Prev.CampfireInventoryRevision)
        {
            Adopted.Items=Prev.Items;
            // Capacity and layout belong to the same authoritative inventory,
            // including extra pages allocated by an earlier footprint migration.
            Adopted.WarehousePages=Prev.WarehousePages;
            Adopted.WarehouseLayoutVersion=Prev.WarehouseLayoutVersion;
            Adopted.StoragePages=Prev.StoragePages;
            Adopted.ActiveWeaponSlot=Prev.ActiveWeaponSlot;Adopted.ActiveProductionTool=Prev.ActiveProductionTool;
            Adopted.AmmoPouch=Prev.AmmoPouch;
            Adopted.Mana=Prev.Mana;Adopted.Stamina=Prev.Stamina;
            Adopted.UppercutStaminaSpent=Prev.UppercutStaminaSpent;
            Adopted.CampfireInventoryRevision=Prev.CampfireInventoryRevision;
        }
