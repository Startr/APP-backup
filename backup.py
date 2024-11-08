#!/usr/bin/env python3
import logging
import yaml
from fabric import Connection, task

# Set up logging
logging.basicConfig(filename='backup.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def load_config(yaml_file):
    with open(yaml_file, 'r') as file:
        return yaml.safe_load(file)

@task
def backup(c, partial_container_names=None):
    # Get a list of running containers
    running_containers = c.run("docker ps --format '{{.Names}}'", echo=True).stdout.splitlines()

    # Use specified partial container names if provided, otherwise use all running containers
    if partial_container_names:
        # Filter to only include running containers that match any of the partial names
        containers_to_backup = [name for name in running_containers
                                if any(partial in name for partial in partial_container_names)]
    else:
        containers_to_backup = running_containers

    if not containers_to_backup:
        logging.warning(f"No matching containers found on {c.host}.")
        return

    # Iterate over the containers
    for container in containers_to_backup:
        logging.info(f"Connecting to container {container} on {c.host}")
        try:
            # Execute the backup script inside the container
            c.run(f'docker exec -i {container} bash -c "./restore_backup_start.sh backup"', echo=True)
            logging.info(f"Backup script completed successfully on {c.host} in container {container}")
        except Exception as e:
            logging.error(f"Error running backup script on {c.host} in container {container}: {e}")

# Load configuration from YAML
config = load_config('config.yaml')

# Set default values from config
default_user = config.get('default_user')
default_key_filename = config.get('default_key_filename')
default_forward_agent = config.get('default_forward_agent', False)

# Generate connections from domains
connections = [
    Connection(
        host=item['domain'],
        user=item.get('user', default_user),
        connect_kwargs={
            "key_filename": item.get('key_filename', default_key_filename)
        },
        forward_agent=item.get('forward_agent', default_forward_agent)
    )
    for item in config['connections']
]

# Get partial container names
partial_container_names = config.get('partial_container_names', [])

for conn in connections:
    backup(conn, partial_container_names)

