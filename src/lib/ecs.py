from functools import partial
import boto3

# Used for failures where ECS task could not be scheduled
class EcsTaskFailureError(Exception):
  def __init__(self,tasks):
    self.tasks = tasks
    self.failures = tasks.get('failures')

# Used for ECS tasks where container(s) exit with a non-zero exit code
class EcsTaskExitCodeError(Exception):
  def __init__(self,tasks,non_zero):
    self.tasks = tasks
    self.non_zero = non_zero

class EcsTaskManager:
  def __init__(self):
    self.client = boto3.client('ecs')

  # Returns a paginated response for paginated operations
  # The result_key is used to define the concatenated results that are combined from each paginated response.
  def paginated_response(self, func, result_key, next_token=None):
    args=dict()
    if next_token:
        args['NextToken'] = next_token
    response = func(**args)
    result = response.get(result_key)
    next_token = response.get('NextToken')
    if not next_token:
       return result
    return result + self.paginated_response(func, result_key, next_token)

  # Lists ECS tasks
  def list_tasks(self, cluster, **kwargs):
    func = partial(self.client.list_tasks,cluster=cluster,**kwargs)
    return self.paginated_response(func, 'taskArns')

  # Stops ECS tasks
  def stop_task(self, cluster, task, reason='unknown'):
    return self.client.stop_task(cluster=cluster, task=task, reason=reason)

  # Describes ECS tasks
  def describe_tasks(self, cluster, tasks):
    return self.client.describe_tasks(cluster=cluster, tasks=tasks)

  # Starts or runs an ECS task
  def start_task(self, cluster, task_definition, started_by, count=1, instances=[], overrides={}):
    if instances:
      return self.client.start_task(
        cluster=cluster, 
        taskDefinition=task_definition, 
        overrides=overrides, 
        containerInstances=instances, 
        startedBy=started_by
      )
    else:
      return self.client.run_task(
        cluster=cluster, 
        taskDefinition=task_definition, 
        overrides=overrides, 
        count=count, 
        startedBy=started_by
      )