terraform {
  required_version = ">= 1.5.0"

  # Remote state in R2 via the S3 backend; copy backend.hcl.example to
  # backend.hcl first (terraform init -backend-config=backend.hcl).
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
