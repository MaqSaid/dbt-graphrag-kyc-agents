terraform {
  backend "s3" {
    bucket         = "kyc-pipeline-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "kyc-pipeline-terraform-locks"
    encrypt        = true
  }
}
