from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

# GCP Configuration
PROJECT_ID = "your-gcp-project-id"
ZONE = "your-gcp-zone"
INSTANCE_GROUP_NAME = "your-instance-group-name"

@app.route('/scale', methods=['POST'])
def scale_up():
    """Triggered by Prometheus alert to scale VM instances."""
    data = request.json
    print(f"Received alert: {data}")

    try:
        command = [
            "gcloud", "compute", "instance-groups", "managed", "resize",
            INSTANCE_GROUP_NAME,
            "--size", "1",
            "--zone", ZONE,
            "--project", PROJECT_ID
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return jsonify({"message": "Scaling triggered successfully", "output": result.stdout}), 200

    except subprocess.CalledProcessError as e:
        return jsonify({"error": "Scaling failed", "details": e.stderr}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
