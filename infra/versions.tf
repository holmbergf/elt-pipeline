terraform {
  required_version = ">= 1.5.0"

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
