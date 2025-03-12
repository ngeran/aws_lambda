from jnpr.junos.op.routes import RouteTable
import logging
import json
import boto3

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RouteMonitor:
    def __init__(self, device, s3_bucket, s3_key_prefix):
        """
        Initialize the Route Monitor for Lambda.

        Args:
            device: Connected Junos Device object
            s3_bucket (str): S3 bucket name for storing route state
            s3_key_prefix (str): S3 key prefix for this device's state
        """
        self.device = device
        self.s3 = boto3.client('s3')
        self.s3_bucket = s3_bucket
        self.s3_key = f"{s3_key_prefix}/{device.hostname}/previous_routes.json"

    def get_routes(self):
        """
        Fetch the current routing table from the device.

        Returns:
            list: List of route items if successful, None if error occurs
        """
        try:
            routes = RouteTable(self.device)
            routes.get()
            return routes.items()
        except Exception as e:
            logger.error(f"Error fetching routes from {self.device.hostname}: {str(e)}")
            return None

    def get_previous_routes(self):
        """
        Retrieve previous routing table from S3.

        Returns:
            list: Previous routes if found, None if not exists or error
        """
        try:
            response = self.s3.get_object(Bucket=self.s3_bucket, Key=self.s3_key)
            return json.loads(response['Body'].read().decode('utf-8'))
        except self.s3.exceptions.NoSuchKey:
            return None
        except Exception as e:
            logger.error(f"Error getting previous routes from S3: {str(e)}")
            return None

    def save_routes(self, routes):
        """
        Save current routes to S3.

        Args:
            routes (list): Current routing table to save
        """
        try:
            self.s3.put_object(
                Bucket=self.s3_bucket,
                Key=self.s3_key,
                Body=json.dumps(routes)
            )
        except Exception as e:
            logger.error(f"Error saving routes to S3: {str(e)}")

    def compare_routes(self, current_routes):
        """
        Compare current routing table with previous state from S3.

        Args:
            current_routes (list): Current routing table items

        Returns:
            list: List of changes detected (additions, modifications, deletions)
        """
        previous_routes = self.get_previous_routes()
        changes = []

        if previous_routes is None:
            self.save_routes(current_routes)
            return ["Initial routing table captured"]

        current_dict = dict(current_routes)
        previous_dict = dict(previous_routes)

        # Check for new or modified routes
        for route, attrs in current_routes:
            if route not in previous_dict:
                changes.append(f"New route added: {route} -> {attrs}")
            elif previous_dict[route] != attrs:
                changes.append(f"Route modified: {route} -> {attrs}")

        # Check for removed routes
        for route in previous_dict:
            if route not in current_dict:
                changes.append(f"Route removed: {route}")

        # Save current state
        self.save_routes(current_routes)
        return changes

    def check_once(self):
        """
        Perform a single routing table check.

        Returns:
            dict: Results including hostname and any changes detected
        """
        try:
            current_routes = self.get_routes()
            if current_routes is None:
                return {
                    'hostname': self.device.hostname,
                    'status': 'error',
                    'message': 'Failed to fetch routes'
                }

            changes = self.compare_routes(current_routes)
            return {
                'hostname': self.device.hostname,
                'status': 'success',
                'changes': changes
            }
        except Exception as e:
            logger.error(f"Check error on {self.device.hostname}: {str(e)}")
            return {
                'hostname': self.device.hostname,
                'status': 'error',
                'message': str(e)
            }
        finally:
            if self.device:
                self.device.close()
