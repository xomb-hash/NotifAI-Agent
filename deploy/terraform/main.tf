# NotifAI Enterprise - Terraform Configuration for GCP
# Alternative to deploy.sh for infrastructure-as-code deployment
#
# Usage:
#   cd deploy/terraform
#   terraform init
#   terraform plan -var="project_id=YOUR_PROJECT" -var="region=us-central1"
#   terraform apply
#
# Expected monthly cost: ~$0.60-5.20 (see deploy.sh for breakdown)

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "notifai-api"
}

variable "google_api_key" {
  description = "Gemini API key (stored in Secret Manager)"
  type        = string
  sensitive   = true
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# === Enable APIs ===
resource "google_project_service" "run" {
  project = var.project_id
  service = "run.googleapis.com"
}

resource "google_project_service" "artifactregistry" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"
}

resource "google_project_service" "secretmanager" {
  project = var.project_id
  service = "secretmanager.googleapis.com"
}

resource "google_project_service" "cloudbuild" {
  project = var.project_id
  service = "cloudbuild.googleapis.com"
}

# === Artifact Registry ===
resource "google_artifact_registry_repository" "notifai" {
  project       = var.project_id
  location      = var.region
  repository_id = "notifai-repo"
  format        = "DOCKER"
  description   = "NotifAI Docker images"

  depends_on = [google_project_service.artifactregistry]
}

# === Secret Manager ===
resource "google_secret_manager_secret" "google_api_key" {
  project   = var.project_id
  secret_id = "google-api-key"

  replication {
    automatic = true
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "google_api_key" {
  secret      = google_secret_manager_secret.google_api_key.id
  secret_data = var.google_api_key
}

# === Cloud Run Service ===
resource "google_cloud_run_service" "notifai" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.notifai.repository_id}/notifai-api:latest"

        ports {
          container_port = 8080
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name  = "GOOGLE_GENAI_USE_ENTERPRISE"
          value = "false"
        }

        env {
          name = "GOOGLE_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.google_api_key.secret_id
              key  = "latest"
            }
          }
        }
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "0"
        "autoscaling.knative.dev/maxScale" = "10"
        "run.googleapis.com/cpu-throttling" = "false"
      }
    }
  }

  depends_on = [
    google_project_service.run,
    google_secret_manager_secret_version.google_api_key,
  ]
}

# === Allow public access ===
resource "google_cloud_run_service_iam_member" "public" {
  project  = google_cloud_run_service.notifai.project
  location = google_cloud_run_service.notifai.location
  service  = google_cloud_run_service.notifai.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# === Outputs ===
output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_service.notifai.status[0].url
}

output "artifact_registry" {
  description = "Artifact Registry repository"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.notifai.repository_id}"
}