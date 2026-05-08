terraform {
  backend "azurerm" {
    resource_group_name  = "rg-lakehouse-tfstate"
    storage_account_name = "stlakehousetfstate"
    container_name       = "tfstate"
    key                  = "lakehouse.tfstate"
  }
}
