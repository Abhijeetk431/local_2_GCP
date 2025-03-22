# variables.tf
variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "us-central1"
}

variable "credentials_file_path" {
  type        = string
  description = "Path to the service account key file"
}
