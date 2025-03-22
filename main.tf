provider "google" {
  credentials = file("credentials.json")
  project     = var.project_id
  region      = var.region
}

resource "google_compute_instance_template" "default" {
  name_prefix = "instance-template-"
  machine_type = "e2-micro"
  network_interface {
    network = "default"
  }
  disk {
    boot        = true
    auto_delete = true
    source_image = "debian-cloud/debian-11"
  }
}

resource "google_compute_region_instance_group_manager" "default" {
  name               = "cloud-vm-group"
  region             = "us-central1"
  base_instance_name = "vm"
  version {
    instance_template = google_compute_instance_template.default.id
  }

  target_size = 0 # Start with 0 instances
}

resource "google_compute_region_autoscaler" "default" {
  name   = "vm-group-autoscaler"
  region = "us-central1"
  target = google_compute_region_instance_group_manager.default.id

  autoscaling_policy {
    max_replicas    = 5
    min_replicas    = 0
    cpu_utilization {
      target = 0.75
    }
  }
}
