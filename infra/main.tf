# Warehouse bucket: ingestion/ (raw landing + state) and data_warehouse/
# (silver/gold Iceberg) zones. Application code owns the prefixes; Terraform
# owns the bucket and its Basin Catalog.
resource "cloudflare_r2_bucket" "nfl" {
  account_id = var.cloudflare_account_id
  name       = var.warehouse_bucket_name
  location   = var.r2_bucket_location
}

resource "cloudflare_r2_data_catalog" "nfl" {
  account_id  = var.cloudflare_account_id
  bucket_name = cloudflare_r2_bucket.nfl.name
}
