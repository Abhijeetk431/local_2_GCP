import logging
import time
import subprocess
from threading import Lock
from flask import Flask, request, jsonify
from google.cloud import compute_v1

app = Flask(__name__)
app.name = 'flask-service'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(app.name)

PROJECT_ID = "vcc-assignment3-g24ai1005"
REGION = "us-central1"
INSTANCE_GROUP_NAME = "cloud-vm-group"
AUTOSCALAR_NAME = "vm-group-autoscaler"

def scaling_with_autoscalar(min, max):
    client = compute_v1.RegionAutoscalersClient()
    autoscaler  = client.get(
        project=PROJECT_ID,
        region=REGION,
        autoscaler=AUTOSCALAR_NAME
    )
    autoscaler.autoscaling_policy.min_num_replicas = min
    autoscaler.autoscaling_policy.max_num_replicas = max
    operation = client.update(
        project=PROJECT_ID,
        region=REGION,
        autoscaler_resource=autoscaler
    )
    # operation.result() # removed it to not wait and respond quickly
JOB_PROFILES = {
    'small': {'load': 40, 'duration': 5},    # 40% load for 5s
    'medium': {'load': 80, 'duration': 60},  # 80% load for 60s
    'large': {'load': 80, 'duration': 240}   # 80% load for 4m
}

# In-memory tracking
vm_load_tracker = {
    'virtualbox-vm': {'busy_until': 0}
}
tracker_lock = Lock()

def get_gcp_instances():
    """Get list of running GCP instances"""
    client = compute_v1.RegionInstanceGroupManagersClient()
    instances = client.list_managed_instances(
        project=PROJECT_ID,
        region=REGION,
        instance_group_manager=INSTANCE_GROUP_NAME
    )
    return [instance.instance.split('/')[-1] for instance in instances]

def find_available_vm():
    """Find first available VM (VirtualBox first, then GCP)"""
    with tracker_lock:
        # Check VirtualBox VM first
        if time.time() > vm_load_tracker['virtualbox-vm']['busy_until']:
            return 'virtualbox-vm'
        
        # Check GCP instances
        for instance in get_gcp_instances():
            if instance not in vm_load_tracker or time.time() > vm_load_tracker[instance]['busy_until']:
                return instance
    return None

def trigger_stress(vm_name, cpu_load, duration):
    """Execute stress command on target VM"""
    try:
        if vm_name == 'virtualbox-vm':
            cmd = [
                "sshpass", "-p", "vagrant",
                "ssh", "-o", "StrictHostKeyChecking=no",
                "vagrant@192.168.56.10",
                f"stress-ng --cpu 1 --timeout {duration} --cpu-load {cpu_load}"
            ]
        else:
            cmd = [
                "gcloud", "compute", "ssh", vm_name,
                f"--zone={REGION}-a",
                "--command", f"stress-ng --cpu 1 --cpu-load {cpu_load} --timeout {duration}"
            ]
        
        subprocess.Popen(cmd)
        with tracker_lock:
            vm_load_tracker[vm_name] = {
                'busy_until': time.time() + duration
            }
        return True
    except Exception as e:
        logger.error(f"Failed to stress {vm_name}: {str(e)}")
        return False

@app.route('/submit-job', methods=['POST'])
def submit_job():
    data = request.json
    job_type = data.get('job_type', 'small').lower()
    
    if job_type not in JOB_PROFILES:
        return jsonify({"error": "Invalid job type"}), 400
    
    profile = JOB_PROFILES[job_type]
    target_vm = find_available_vm()
    
    if not target_vm:
        logger.warning("No available VMs, returning 503")
        return jsonify({"status": "unavailable", "message": "No capacity"}), 503
    
    if trigger_stress(target_vm, profile['load'], profile['duration']):
        return jsonify({
            "status": "success",
            "vm": target_vm,
            "load": profile['load'],
            "duration": profile['duration']
        }), 200
    
    return jsonify({"status": "error", "message": "Failed to trigger stress"}), 500
@app.route('/scale', methods=['POST'])
def handle_alert():
    data = request.get_json()
    status = data['status']
    alert_name = data['commonLabels']['alertname']
    logger.info(f"Recieved alert: {alert_name} with status: {status}")
    if status == 'firing':
        logger.info(f"🚨 FIRING: {alert_name} - Trigger scaling up")
        scaling_with_autoscalar(1, 5)
        logger.info(f"Instance group resized to 1 instances")
    elif status == 'resolved':
        logger.info(f"✅ RESOLVED: {alert_name} - Trigger scaling down")
        scaling_with_autoscalar(0, 0)
        logger.info(f"Instance group resized to 0 instances")
    return 'OK', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
