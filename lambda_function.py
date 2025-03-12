import json
import boto3
import logging
from connect_to_host import is_reachable, connect_to_device
from route_monitor import RouteMonitor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ssm = boto3.client('ssm')

def get_config(parameter_name='/route-monitor/config'):
    """
    Load configuration from AWS SSM Parameter Store.

    Args:
        parameter_name (str): SSM parameter name containing config

    Returns:
        dict: Configuration data if successful, None if error occurs
    """
    try:
        response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
        return json.loads(response['Parameter']['Value'])
    except Exception as e:
        logger.error(f"Error loading config from SSM: {str(e)}")
        return None

def lambda_handler(event, context):
    """
    AWS Lambda handler function.

    Args:
        event: Lambda event data
        context: Lambda context object

    Returns:
        dict: Response with monitoring results
    """
    # Load configuration from SSM
    config = get_config()
    if not config or 'devices' not in config:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Invalid or missing configuration'})
        }

    devices = config['devices']
    results = []
    s3_bucket = config.get('s3_bucket', 'route-monitor-state')

    # Process each device
    for device_info in devices:
        hostname = device_info.get('hostname')
        username = device_info.get('username')
        password = device_info.get('password')

        if not all([hostname, username, password]):
            results.append({
                'hostname': hostname or 'unknown',
                'status': 'error',
                'message': 'Missing required parameters'
            })
            continue

        # Check reachability
        if not is_reachable(hostname):
            results.append({
                'hostname': hostname,
                'status': 'error',
                'message': 'Device not reachable'
            })
            continue

        # Connect and check routes
        device = connect_to_device(hostname, username, password)
        if device:
            monitor = RouteMonitor(device, s3_bucket, 'route-states')
            result = monitor.check_once()
            results.append(result)
        else:
            results.append({
                'hostname': hostname,
                'status': 'error',
                'message': 'Connection failed'
            })

    return {
        'statusCode': 200,
        'body': json.dumps({
            'results': results,
            'timestamp': context.aws_request_id
        })
    }
