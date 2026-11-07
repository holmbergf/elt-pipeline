# Remote state: S3 backend on Cloudflare R2 (bucket created by infra/bootstrap).
# Credentials come from AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY in the
# environment (locally: the .env R2 keys; in Actions: repo secrets).
bucket       = "elt-tfstate"
key          = "elt-pipeline/infra/terraform.tfstate"
region       = "auto"
endpoints    = { s3 = "https://c9137e5ad23e1f207bb5e9042c3a6284.r2.cloudflarestorage.com" }
use_lockfile = true

skip_credentials_validation = true
skip_metadata_api_check     = true
skip_region_validation      = true
skip_requesting_account_id  = true
skip_s3_checksum            = true
use_path_style              = true
