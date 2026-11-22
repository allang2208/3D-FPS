        else if(const auto* Scene=Cast<AColdSteelSceneContainer>(WarehouseAnchor.Get()))
        {
            if(!Scene->IsWithinPanelReach(GetOwningPlayer()))CloseWarehouse();
        }
