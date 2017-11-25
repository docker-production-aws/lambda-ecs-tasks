import logging
from ecs import EcsTaskFailureError, EcsTaskExitCodeError
from voluptuous import MultipleInvalid, Invalid
from cfn_lambda_handler import CfnLambdaExecutionTimeout

log = logging.getLogger()

def error_handler(func):
  def handle_task_result(event, context):
    try:
      event = func(event, context)
    except EcsTaskFailureError as e:
      event['Status'] = "FAILED"
      event['Reason'] = "A task failure occurred: %s" % e.failures
    except EcsTaskExitCodeError as e:
      event['Status'] = "FAILED"
      event['Reason'] = "A container failed with a non-zero exit code: %s" % e.non_zero
    except (Invalid, MultipleInvalid) as e:
      event['Status'] = "FAILED"
      event['Reason'] = "One or more invalid event properties: %s" % e
    except CfnLambdaExecutionTimeout as e:
      event['Status'] = "FAILED"
      event['Reason'] = "Lambda function reached maximum execution time"
    if event.get('Status') == "FAILED":
      log.error(event['Reason'])
    return event
  return handle_task_result