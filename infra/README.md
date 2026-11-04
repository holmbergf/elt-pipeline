# Infrastructure (Terraform)

This directory contains Terraform definitions for provisioning Cloudflare infrastructure for `elt-pipeline`.

## Resources Provisioned

- **Cloudflare R2 Bucket**: `nfl` (plus its Basin Catalog, `cloudflare_r2_data_catalog.nfl`)

---

## Prerequisites

1. **Terraform CLI**: Ensure Terraform (or OpenTofu) is installed:
   ```bash
   brew tap hashicorp/tap
   brew install hashicorp/tap/terraform
   # or with OpenTofu:
   # brew install opentofu
   ```
2. **Cloudflare Account ID**: Locate your Account ID in the Cloudflare Dashboard (found in the URL or in the overview sidebar).
3. **Cloudflare API Token**: Create an API Token in Cloudflare dashboard with:
   - **Account** -> **Workers R2 Storage** -> **Edit**
   - Alternatively, a token with Custom Permissions for R2 Admin.

---

## Setup & Deployment

1. **Set Authentication Credentials**:
   Export your API token in your shell (recommended):
   ```bash
   export CLOUDFLARE_API_TOKEN="your-api-token-here"
   ```

2. **Configure Variables**:
   Copy the example variables file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```
   Set your `cloudflare_account_id` in `terraform.tfvars`.

3. **Initialize Terraform**:
   ```bash
   terraform init
   ```

4. **Review Execution Plan**:
   ```bash
   terraform plan
   ```

5. **Apply Infrastructure**:
   ```bash
   terraform apply
   ```
