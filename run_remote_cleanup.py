import paramiko
import time

host = "ssh-achal.alwaysdata.net"
user = "achal"
password = "Aman@4899"

print(f"Connecting to {host}...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(host, username=user, password=password, timeout=10)
    print("Connected successfully!")

    commands = [
        "echo 'Killing python processes...'",
        "pkill -u achal -9 -f python || true",
        "echo 'Deleting all project files...'",
        "rm -rf /home/achal/amazon-affiliate-telegram-bot /home/achal/bot /home/achal/.venv /home/achal/venv /home/achal/.cache /home/achal/.local /home/achal/logs",
        "echo 'Checking remaining files in home directory:'",
        "ls -la /home/achal/",
        "echo 'Disk space:'",
        "df -h /home/achal",
        "echo 'Processes:'",
        "ps aux | grep achal"
    ]

    for cmd in commands:
        print(f"\n> {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode().strip())
        err = stderr.read().decode().strip()
        if err:
            print(f"STDERR: {err}")
        time.sleep(1)

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
