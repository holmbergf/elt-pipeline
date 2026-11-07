# Bootstrap: creates the R2 bucket that holds the main configuration's
# remote Terraform state. This module intentionally keeps its OWN local
# state (chicken-and-egg) and is applied once, by hand:
#   terraform -chdir=infra/bootstrap init && terraform -chdir=infra/bootstrap apply
# Its state file is tiny (one bucket) and gitignored like all *.tfstate.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}

variable "cloudflare_account_id" {
  description = "The Cloudflare Account ID that owns the R2 storage resource"
  type        = string
}

resource "cloudflare_r2_bucket" "tfstate" {
  account_id = var.cloudflare_account_id
  name       = "elt-tfstate"
}

output "tfstate_bucket" {
  value = cloudflare_r2_bucket.tfstate.name
}
