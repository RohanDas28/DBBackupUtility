import os
import subprocess
import time
from datetime import datetime, timedelta
from discord_webhook import DiscordWebhook

USE_GIT = False # Set to True to use git to store backups 
# (if set to True, you need to have git installed on your system)
# (if set to True, you need to have a remote repository set up)
USE_DISCORD = True  # Set to True to send backups via Discord webhook

db_user = ""  # Change this to your database username
db_password = ""  # Change this to your database password
db_name = "" # Change this to your database name
export_dir = "" # Change this to your folder to store sql files
webhook_url = ""  # Replace with your Discord webhook URL

# Backup interval (in minutes) - set your desired time here
backup_interval_hours = 1
backup_interval_minutes =  backup_interval_hours * 60

# Retention period for backups (in houts)
retention_period_hours = 12

# Create export directory if it doesn't exist
if not os.path.exists(export_dir):
    os.makedirs(export_dir)

def cleanup_old_backups():
    """Delete old backups older than the retention period."""
    now = datetime.now()
    cutoff_time = now - timedelta(hours=retention_period_hours)

    for file_name in os.listdir(export_dir):
        file_path = os.path.join(export_dir, file_name)
        if os.path.isfile(file_path):
            # Get the file's last modified time
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_mtime < cutoff_time:
                try:
                    os.remove(file_path)
                    print(f"Deleted old backup: {file_path}")
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")

def create_backup():
    """Creates a database backup and returns the file path."""
    # Generate the filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_file = f"{export_dir}/{db_name}_{timestamp}.sql"

    # Build the mysqldump command (SSL disabled)
    command = [
        "mysqldump",
        "--ssl=0",
        "-u", db_user,
        f"--password={db_password}",
        db_name
    ]

    try:
        # Run mysqldump command to export the database
        with open(export_file, "w") as output_file:
            subprocess.run(command, stdout=output_file, check=True)

        print(f"Database exported successfully: {export_file}")
        return export_file
    except subprocess.CalledProcessError as e:
        print(f"Error exporting database: {e}")
        return None

def send_to_discord(file_path):
    """Sends the backup file to Discord via webhook."""
    try:
        webhook = DiscordWebhook(url=webhook_url, username="Database Exporter")
        with open(file_path, "rb") as f:
            webhook.add_file(file=f.read(), filename=os.path.basename(file_path))

        response = webhook.execute()
        if response.status_code == 200:
            print("Database export sent to Discord successfully!")
        else:
            print(f"Failed to send database export to Discord: {response.status_code}")
    except Exception as e:
        print(f"Unexpected error sending to Discord: {e}")

def commit_to_git(file_path):
    """Commits the backup file to a Git repository and pushes the changes."""
    try:
        os.chdir(export_dir)  # Change directory to the backup folder

        # Initialize the Git repository if not already initialized
        if not os.path.exists(os.path.join(export_dir, ".git")):
            subprocess.run(["git", "init"], check=True)
            print("Initialized a new Git repository.")
            
            # Add the remote repository if it's not set up
            subprocess.run(["git", "remote", "add", "origin", "https://github.com/zaid-ahmed-001/DatabaseBackup-test"], check=True)
            print("Remote repository added successfully.")

        # Add the new backup file
        subprocess.run(["git", "add", file_path], check=True)

        # Commit the changes with a timestamp message
        commit_message = f"Backup created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print("Backup committed to Git successfully!")

        # Push the changes to the remote repository
        subprocess.run(["git", "push", "origin", "main"], check=True)  # Assuming 'main' as the default branch
        print("Changes pushed to the remote Git repository successfully!")

    except subprocess.CalledProcessError as e:
        print(f"Error committing or pushing to Git: {e}")

def main():
    while True:
        print("Starting backup process...")

        # Create a backup
        backup_file = create_backup()

        if backup_file:
            # Choose where to store the backup
            if USE_GIT:
                commit_to_git(backup_file)
            if USE_DISCORD:
                send_to_discord(backup_file)

            # Cleanup old backups
            print("Cleaning up old backups...")
            cleanup_old_backups()

        print(f"Waiting {backup_interval_minutes} minutes for the next backup...")
        time.sleep(backup_interval_minutes * 60)  # Convert minutes to seconds

if __name__ == "__main__":
    main()
