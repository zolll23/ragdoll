#!/usr/bin/env python3
"""
Script to add project path mount to docker-compose.yml
Uses text-based approach to preserve file structure
"""
import os
import sys
from pathlib import Path


def add_mount_to_compose(base_path: str):
    """Add volume mount to docker-compose.yml"""
    
    # Convert to absolute path
    abs_path = os.path.abspath(base_path)
    
    if not os.path.isdir(abs_path):
        print(f"Error: Directory does not exist: {abs_path}")
        sys.exit(1)
    
    compose_file = Path("docker-compose.yml")
    
    if not compose_file.exists():
        print(f"Error: {compose_file} not found")
        sys.exit(1)
    
    # Read docker-compose.yml
    with open(compose_file, 'r') as f:
        lines = f.readlines()
    
    # Check if path is already mounted
    if any(abs_path in line for line in lines):
        print(f"Path {abs_path} is already mounted in docker-compose.yml")
        return
    
    # Services that need the mount
    services = ['backend', 'celery_worker']
    mount_line = f"      - {abs_path}:{abs_path}:ro\n"
    new_lines = []
    i = 0
    modified = False
    
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # Check if we're entering a service that needs mounting
        for service_name in services:
            if line.strip() == f"{service_name}:":
                # Look for volumes section in this service
                j = i + 1
                in_volumes = False
                last_volume_idx = -1
                
                while j < len(lines):
                    next_line = lines[j]
                    stripped = next_line.strip()
                    
                    # Stop if we hit next top-level service/key (not indented)
                    if stripped and not next_line.startswith(' ') and not next_line.startswith('\t'):
                        if ':' in stripped and not stripped.startswith('#'):
                            break
                    
                    # Found volumes: line
                    if 'volumes:' in next_line:
                        in_volumes = True
                        new_lines.append(next_line)
                        j += 1
                        continue
                    
                    # If we're in volumes section
                    if in_volumes:
                        # Check if this is a volume line (starts with -)
                        if stripped.startswith('-'):
                            new_lines.append(next_line)
                            last_volume_idx = len(new_lines) - 1
                            j += 1
                            continue
                        elif stripped and not stripped.startswith('#'):
                            # End of volumes section, insert mount before this line
                            if last_volume_idx >= 0:
                                new_lines.insert(last_volume_idx + 1, mount_line)
                                modified = True
                            in_volumes = False
                            new_lines.append(next_line)
                            j += 1
                            continue
                        # Empty line or comment
                        new_lines.append(next_line)
                        j += 1
                        continue
                    
                    new_lines.append(next_line)
                    j += 1
                
                # If we found volumes but didn't insert yet, add at the end
                if in_volumes:
                    if last_volume_idx >= 0:
                        new_lines.insert(last_volume_idx + 1, mount_line)
                    else:
                        # No volumes yet, add after volumes: line
                        new_lines.append(mount_line)
                    modified = True
                
                i = j
                break
        
        i += 1
    
    if not modified:
        print("Warning: Could not find volumes sections for target services")
        return
    
    # Write back to file
    with open(compose_file, 'w') as f:
        f.writelines(new_lines)
    
    # Validate docker-compose file
    exit_code = os.system("docker-compose config > /dev/null 2>&1")
    if exit_code != 0:
        print("Error: docker-compose.yml is invalid after modification!")
        print("Please check the file manually or restore from git")
        sys.exit(1)
    
    print(f"✓ Added mount: {abs_path} -> {abs_path} (read-only)")
    print(f"✓ Updated docker-compose.yml")
    print("")
    print("Restarting containers...")
    
    # Restart containers
    exit_code = os.system("docker-compose down > /dev/null 2>&1")
    if exit_code != 0:
        print("Warning: docker-compose down failed")
    
    exit_code = os.system("docker-compose up -d")
    if exit_code != 0:
        print("Error: docker-compose up failed")
        sys.exit(1)
    
    print("")
    print(f"✓ Done! Path {abs_path} is now mounted in containers.")
    print(f"  You can now create a project with path: {abs_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: make add BASE_PATH=/path/to/project")
        sys.exit(1)
    
    base_path = sys.argv[1]
    add_mount_to_compose(base_path)
