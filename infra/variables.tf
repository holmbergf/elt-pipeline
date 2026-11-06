variable "cloudflare_account_id" {
  description = "The Cloudflare Account ID that owns the R2 storage resource"
  type        = string
}

variable "cloudflare_api_token" {
  description = "Cloudflare API Token with R2 permissions (can also be set via CLOUDFLARE_API_TOKEN environment variable)"
  type        = string
  sensitive   = true
  default     = null
}

variable "warehouse_bucket_name" {
  description = "Warehouse R2 bucket holding ingestion/ and data_warehouse/ zones."
  type        = string
  default     = "nfl"
}

variable "r2_bucket_location" {
  description = "Optional location hint for the R2 bucket ('wnam', 'enam', 'weur', 'eeur', 'apac', 'oc')"
  type        = string
  default     = null
}

variable "ncaaf_bucket_name" {
  description = "NCAAF R2 bucket holding ingestion/ and data_warehouse/ zones."
  type        = string
  default     = "ncaaf"
}
