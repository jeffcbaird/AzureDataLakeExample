environment                = "dev"
location                   = "westus2"
deploy_expensive_resources = false

tags = {
  project     = "lakehouse"
  environment = "dev"
  managed_by  = "terraform"
}

# Azure DevOps — fill in your org/project to enable ADF Git integration
devops_account_name = ""
devops_project_name = "lakehouse"
