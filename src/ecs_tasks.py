import sys, os
parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'vendor')
sys.path.append(vendor_dir)

import logging, datetime, json, time
from cfn_lambda_handler import Handler, CfnLambdaExecutionTimeout
from voluptuous import Invalid, MultipleInvalid
from lib import validate
from lib import EcsTaskManager, EcsTaskFailureError, EcsTaskExitCodeError
from hashlib import md5
from lib import error_handler

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

# Checks ECS task has completed
def check_complete(task_result):
  if task_result.get('failures'):
    raise EcsTaskFailureError(task_result)
  tasks = task_result.get('tasks')
  return all(t.get('lastStatus') == 'STOPPED' for t in tasks)

# Updates ECS task status
def describe_tasks(cluster, task_result):
  tasks = task_result['tasks']
  task_arns = [t.get('taskArn') for t in tasks]
  return task_mgr.describe_tasks(cluster=cluster, tasks=task_arns)

# Checks ECS task exit codes
def check_exit_codes(task_result):
  tasks = task_result['tasks']
  non_zero = [
    c.get('taskArn') 
    for t in tasks for c in t.get('containers') 
    if c.get('exitCode') != 0
  ]
  if non_zero:
    raise EcsTaskExitCodeError(tasks, non_zero)

# Polls an ECS task for completion
def poll(task, remaining_time):
  poll_interval = 10
  while True:
    if remaining_time() < (poll_interval + 5) * 1000:
      raise CfnLambdaExecutionTimeout(task)
    if not check_complete(task['TaskResult']):
      log.info("Task(s) not yet completed, checking again in %s seconds..." % poll_interval)
      time.sleep(poll_interval)
      task['TaskResult'] = describe_tasks(task['Cluster'], task['TaskResult'])
    else:
      # Task completed
      check_exit_codes(task['TaskResult'])
      return task['TaskResult']

# Starts and ECS task and polls for the task result
def start_and_poll(task, context):
  task['TaskResult'] = start(task)
  task['TaskResult'] = poll(task, context.get_remaining_time_in_millis)
  log.info("Task completed successfully with result: %s" % format_json(task['TaskResult']))

# Creates a task object from event data
def create_task(event, context):
  task = validate(event.get('ResourceProperties'))
  task['StartedBy'] = get_task_id(event.get('StackId'), event.get('LogicalResourceId'))
  log.info('Received task %s' % format_json(task))
  return task

# Create requests
@handler.create
@error_handler
def handle_create(event, context):
  log.info("Received create event: %s" % format_json(event))
  task = create_task(event, context)
  if task['Count'] > 0:
    start_and_poll(task, context)
    event['PhysicalResourceId'] = next(t['taskArn'] for t in task['TaskResult']['tasks'])
  return event

# Update requests
@handler.update
@error_handler
def handle_update(event, context):
  log.info("Received update event: %s" % format_json(event))
  task = create_task(event, context)
  if task['RunOnUpdate'] and task['Count'] > 0:
    start_and_poll(task, context)
    event['PhysicalResourceId'] = next(t['taskArn'] for t in task['TaskResult']['tasks'])
  return event

# Delete requests
@handler.delete
@error_handler
def handle_delete(event, context):
  log.info("Received delete event: %s" % format_json(event))
  task = create_task(event, context)
  tasks = task_mgr.list_tasks(cluster=task['Cluster'], startedBy=task['StartedBy'])
  for t in tasks:
    task_mgr.stop_task(
      cluster=task['Cluster'],
      task=t,
      reason='Delete request for stack %s' % event['StackId']
    )
  return event