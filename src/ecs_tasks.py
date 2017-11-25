import sys, os
parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'vendor')
sys.path.append(vendor_dir)

import logging, datetime, json
from cfn_lambda_handler import Handler, CfnLambdaExecutionTimeout
from voluptuous import Invalid, MultipleInvalid
from lib import validate

# Configure logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(os.environ.get('LOG_LEVEL','INFO'))
def format_json(data):
  return json.dumps(data, default=lambda d: d.isoformat() if isinstance(d, datetime.datetime) else str(d))

# Set handler as the entry point for Lambda
handler = Handler()

# Create requests
@handler.create
def handle_create(event, context):
  log.info("Received create event: %s" % format_json(event))
  try:
    task = validate(event['ResourceProperties'])
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