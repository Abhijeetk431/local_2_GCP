provider "google" {
  credentials = file("credentials.json")
  project     = var.project_id
  region      = var.region
}

# Instance Template with stress-ng
resource "google_compute_instance_template" "default" {
  name_prefix  = "instance-template-"
  machine_type = "e2-micro"

  metadata = {
    startup-script = <<-EOF
      #!/bin/bash
      apt update
      apt install -y stress-ng
    EOF
  }

  disk {
    boot        = true
    auto_delete = true
    source_image = "debian-cloud/debian-11"
  }

  network_interface {
    network = "default"
    access_config {}
  }

  tags = ["ssh"]
}

# Instance Group Manager
resource "google_compute_region_instance_group_manager" "default" {
  name               = "cloud-vm-group"
  region             = "us-central1"
  base_instance_name = "vm"
  target_size        = 0  # Start with 0 instances

  version {
    instance_template = google_compute_instance_template.default.id
  }
}

# Autoscaler
resource "google_compute_region_autoscaler" "default" {
  name   = "vm-group-autoscaler"
  region = "us-central1"
  target = google_compute_region_instance_group_manager.default.id

  autoscaling_policy {
    max_replicas    = 5
    min_replicas    = 0
    cpu_utilization {
      target = 0.75  # Scale when CPU >75%
    }
  }
}

# Firewall Rule for SSH
resource "google_compute_firewall" "ssh" {
  name    = "allow-ssh"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
}