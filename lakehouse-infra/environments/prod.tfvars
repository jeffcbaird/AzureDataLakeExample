# Production environment.
# Before applying: remove the validation block on deploy_expensive_resources in variables.tf.
environment                = "prod"
location                   = "westus2"
deploy_expensive_resources = false  # change to true after removing validation block

tags = {
  project     = "lakehouse"
  environment = "prod"
  managed_by  = "terraform"
}

# Azure DevOps — fill in your org/project to enable ADF Git integration
devops_account_name = ""
devops_project_name = "lakehouse"
