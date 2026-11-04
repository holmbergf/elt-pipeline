output "r2_bucket_name" {
  description = "The name of the warehouse R2 bucket"
  value       = cloudflare_r2_bucket.nfl.name
}

output "warehouse_bucket_name" {
  description = "Warehouse bucket (ingestion/ + data_warehouse/ zones)"
  value       = cloudflare_r2_bucket.nfl.name
}

output "warehouse_catalog_id" {
  description = "Basin Catalog activation ID for the warehouse bucket"
  value       = cloudflare_r2_data_catalog.nfl.id
}

output "warehouse_catalog_uri" {
  description = "Iceberg REST catalog URI for the warehouse bucket"
  value       = "https://catalog.cloudflarestorage.com/${var.cloudflare_account_id}/${cloudflare_r2_bucket.nfl.name}"
}

output "warehouse_warehouse" {
  description = "Basin Catalog warehouse name for the warehouse bucket"
  value       = "${var.cloudflare_account_id}_${cloudflare_r2_bucket.nfl.name}"
}
