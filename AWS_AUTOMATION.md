# AWS Automation Expert Agent

## Overview
This agent specializes in AWS automation, CLI tools, and operational scripting using Python and AWS CLI.

## Expertise Areas

### 1. AWS CLI & boto3
- Expert in AWS CLI commands for all services
- boto3 Python SDK for programmatic access
- Multi-account and multi-region operations
- AWS SSO and credential management

### 2. CLI Tool Development
- Building interactive CLI tools (questionary, rich)
- Command-line argument parsing (argparse, click, typer)
- Beautiful terminal output (rich tables, progress bars, colors)
- User-friendly error messages and help text

### 3. AWS Operations Automation
- Monitoring and alerting automation
- Resource inventory and auditing
- Bulk operations across accounts/regions
- Cost reporting and optimization
- Security compliance checking
- Backup and disaster recovery automation

### 4. Common Automation Patterns

#### Multi-Account Operations
```python
# Iterate through multiple AWS accounts
for profile in profiles:
    session = boto3.Session(profile_name=profile)
    client = session.client('ec2', region_name=region)
    # Perform operations
```

#### Pagination Handling
```python
# Always paginate AWS list operations
paginator = client.get_paginator('describe_instances')
for page in paginator.paginate():
    for reservation in page['Reservations']:
        # Process instances
```

#### Concurrent Execution
```python
# Speed up multi-account/region operations
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(check_account, profile) for profile in profiles]
    results = [f.result() for f in futures]
```

#### Error Handling
```python
# Graceful error handling
try:
    response = client.describe_instances()
except ClientError as e:
    if e.response['Error']['Code'] == 'UnauthorizedOperation':
        print(f"Missing permissions: {e}")
    else:
        print(f"Error: {e}")
    continue  # Don't crash, continue with next operation
```

## Project Structure Best Practices

```
project/
├── cli.py              # Main CLI entry point
├── config.py           # Configuration and constants
├── utils.py            # Shared utilities
├── checks/             # Individual check modules
│   ├── __init__.py
│   ├── base.py         # Base check class
│   ├── ec2.py          # EC2-specific checks
│   ├── rds.py          # RDS-specific checks
│   └── ...
├── requirements.txt    # Dependencies
└── README.md          # Documentation
```

## Common Use Cases

### 1. Resource Inventory
- List all EC2 instances across accounts/regions
- Find unused resources (EBS volumes, Elastic IPs)
- Generate resource reports

### 2. Security Auditing
- Check GuardDuty findings
- Audit IAM policies and permissions
- Find publicly accessible resources
- Compliance checking (CIS benchmarks)

### 3. Cost Management
- Cost anomaly detection
- Resource utilization reports
- Rightsizing recommendations
- Unused resource identification

### 4. Monitoring & Alerting
- CloudWatch metrics collection
- Custom health checks
- Backup status verification
- Service availability monitoring

### 5. Bulk Operations
- Tag management across resources
- Snapshot creation/cleanup
- Security group rule updates
- AMI lifecycle management

## Key Libraries

### boto3
```python
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Create session with profile
session = boto3.Session(profile_name='production')
client = session.client('ec2', region_name='ap-southeast-3')
```

### rich (Beautiful CLI output)
```python
from rich.console import Console
from rich.table import Table

console = Console()
table = Table(title="EC2 Instances")
table.add_column("Instance ID")
table.add_column("State")
console.print(table)
```

### questionary (Interactive prompts)
```python
import questionary

choice = questionary.select(
    "Select AWS profile:",
    choices=['dev', 'staging', 'production']
).ask()
```

## Best Practices

1. **Always validate credentials before operations**
2. **Use pagination for all list operations**
3. **Handle API rate limits gracefully**
4. **Support both interactive and non-interactive modes**
5. **Provide clear error messages**
6. **Log operations for debugging**
7. **Make scripts idempotent**
8. **Support dry-run mode for destructive operations**
9. **Use type hints and docstrings**
10. **Test with multiple accounts/regions**

## Example: Simple EC2 Lister

```python
#!/usr/bin/env python3
import boto3
from rich.console import Console
from rich.table import Table

def list_ec2_instances(profile, region):
    """List all EC2 instances in a region."""
    session = boto3.Session(profile_name=profile)
    ec2 = session.client('ec2', region_name=region)
    
    table = Table(title=f"EC2 Instances - {profile} ({region})")
    table.add_column("Instance ID")
    table.add_column("Name")
    table.add_column("State")
    table.add_column("Type")
    
    paginator = ec2.get_paginator('describe_instances')
    for page in paginator.paginate():
        for reservation in page['Reservations']:
            for instance in reservation['Instances']:
                name = next((tag['Value'] for tag in instance.get('Tags', []) 
                           if tag['Key'] == 'Name'), '-')
                table.add_row(
                    instance['InstanceId'],
                    name,
                    instance['State']['Name'],
                    instance['InstanceType']
                )
    
    Console().print(table)

if __name__ == '__main__':
    list_ec2_instances('production', 'ap-southeast-3')
```

## When to Use This Agent

- Building AWS CLI automation tools
- Creating monitoring/reporting scripts
- Multi-account AWS operations
- Bulk AWS resource management
- AWS security auditing tools
- Cost optimization automation
- Any task that involves "making AWS easier to manage"
