terraform {
  required_version = ">= 1.5.0"

  # Remote state in R2 via the S3 backend; concrete settings live in
  # backend.hcl (terraform init -backend-config=backend.hcl).
  backend "s3" {}

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}

provider "cloudflare" {
  # If null, provider falls back to the CLOUDFLARE_API_TOKEN environment variable
  api_token = var.cloudflare_api_token
}
