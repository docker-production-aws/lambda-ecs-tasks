import sys, os
parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'vendor')
sys.path.append(vendor_dir)

import logging, datetime, json
from cfn_lambda_handler import Handler, CfnLambdaExecutionTimeout
from voluptuous import Invalid, MultipleInvalid
from lib import validate
from lib import EcsTaskManager, EcsTaskFailureError, EcsTaskExitCodeError
from hashlib import md5

# Configure logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(os.environ.get('LOG_LEVEL','INFO'))
def format_json(data):
  return json.dumps(data, default=lambda d: d.isoformat() if isinstance(d, datetime.datetime) else str(d))

# Set handler as the entry point for Lambda
handler = Handler()

# ECS task manager
task_mgr = EcsTaskManager()

# Creates a fixed length consist ID based from a given stack ID and resource ID
def get_task_id(stack_id, resource_id):
  m = md5()
  m.update(stack_id + resource_id)
  return m.hexdigest()

# Starts an ECS task
def start(task):
  log.info("Starting task: %s" % str(task))
  return task_mgr.start_task(
    cluster=task['Cluster'],
    task_definition=task['TaskDefinition'],
    started_by=task['StartedBy'],
    count=task['Count'],
    instances=task['Instances'],
    overrides=task['Overrides']
  )

# Create requests
@handler.create
def handle_create(event, context):
  log.info("Received create event: %s" % format_json(event))
  try:
    task = validate(event['ResourceProperties'])
    task['StartedBy'] = get_task_id(event.get('StackId'), event.get('LogicalResourceId'))
    task['TaskResult'] = start(task)
  except (Invalid, MultipleInvalid) as e:
    event['Status'] = "FAILED"
    event['Reason'] = "One or more invalid resource properties %s" % e
  return event

# Update requests
@handler.update
def handle_update(event, context):
  log.info("Received update event: %s" % format_json(event))
  return event

# Delete requests
@handler.delete
def handle_delete(event, context):
  log.info("Received delete event: %s" % format_json(event))
  return event