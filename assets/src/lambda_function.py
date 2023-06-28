from __future__ import print_function

import json
import logging
import sys

import boto3
import requests
from crhelper import CfnResource
from furl import furl
from opensearchpy import OpenSearch, RequestsHttpConnection
import re

from src.helpers.placeholder_resolver import resolve_placeholders
from src.helpers.service_settings import ServiceSettings
from src.helpers.solution_components import SolutionComponents

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
helper = CfnResource(json_logging=False, log_level='DEBUG', boto_level='CRITICAL')

try:
    aws_clients = {
        "waf": boto3.client('waf'),
        "wafRegional": boto3.client('waf-regional'),
        "wafv2_cloudfront": boto3.client('wafv2', region_name='us-east-1'),
        "wafv2_regional": boto3.client('wafv2'),
    }

    solution_components = SolutionComponents()
    service_settings = ServiceSettings(credentials=boto3.Session().get_credentials())

    logger.info("OpenSearch client URL %s", service_settings.host)

    opensearch_client = OpenSearch(
        hosts=[{'host': service_settings.host, 'port': 443}],
        http_auth=service_settings.aws_auth,
        use_ssl=True,
        verify_certs=True,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        connection_class=RequestsHttpConnection)

except Exception as e:
    helper.init_failure(e)
    logging.error(e)
    raise e


@helper.create
def create(event=None, context=None):
    logger.info("Got Create!")
    logger.debug("Sourcing additional settings from the event")

    service_settings.source_settings_from_event(event)
    import_index_templates(solution_components.templates)
    action_dashboard_objects('POST')

    return "MyResourceId"


@helper.update
def update(event=None, context=None):
    logger.info("Got Update.")
    logger.debug("Sourcing additional settings from the event")

    service_settings.source_settings_from_event(event)
    recycle_dashboards_objects()
    return "MyResourceId"


@helper.delete
def delete(event=None, context=None):
    logger.info("Got Delete")
    logger.debug("Sourcing additional settings from the event")

    service_settings.source_settings_from_event(event)
    delete_index_templates()
    delete_dashboards_objects()
    return True


@helper.poll_create
def poll_create(event=None, context=None):
    logger.info("Got create poll")
    return True


def handler(event, context):
    helper(event, context)


def action_dashboard_objects(method, ignored_objects=None):
    """
    Iterates through json objects in dashboards_definitions_json folder and makes API requests to OS Dashboards

    It's a generic method, that can take any HTTP verb and call OS Dashboards RESTful API.

    @param method: HTTP verb
    @param ignored_objects: A list of objects to ignore in this iteration, useful if we don't want to iterate through "visualizations" for example
    """
    logger.info(json.dumps(solution_components.__dict__, indent=4, sort_keys=True))

    if ignored_objects is None:
        ignored_objects = []

    for resource_type in vars(solution_components):
        logging.debug("TYPE: %s", resource_type)

        if resource_type == "templates" or resource_type in ignored_objects:
            continue
        else:
            for resource_name in solution_components.__getattribute__(resource_type):
                logging.debug("NAME: %s", resource_name)

                body = solution_components.__getattribute__(resource_type)[resource_name]

                if resource_type == "index_patterns":
                    body = resolve_placeholders(aws_clients, body)

                call_dashboards_api_for_resource(method, service_settings.dashboards_api_resource_types[resource_type], resource_name, body)


def call_dashboards_api_for_resource(method, resource_type, resource_name, resource_body):
    """
    Makes an actual HTTP request to OpenSearch Dashboards API

    The URL is constructed based on the arguments passed to this method and general settings stored in ServiceSettings object

    @param method: HTTP verb
    @param resource_type: type of OpenSearch resource, e.g. template/visualization/index_pattern
    @param resource_name: name of the resource to be created
    @param resource_body: stringified JSON body
    """
    f = furl(scheme="https", host=service_settings.host, port=service_settings.dashboards_port)
    f.add(path=['_dashboards', 'api', 'saved_objects', resource_type, resource_name])

    logging.info("Issuing %s to %s", method, f.url)

    response = requests.request(method, f.url, auth=service_settings.aws_auth, headers=service_settings.headers, data=resource_body)

    if response.ok:
        if re.search('^<!DOCTYPE html>', response.text, re.IGNORECASE):
            logging.warning("HTML response detected")
            if re.search('"cognitoSignInForm"', response.text):
                logging.error("Cognito Sign In Form detected")
        else:
            logging.info("Request was successful: %s", response.text)
    elif response.status_code == 404:
        logging.info("Request made but the resource was not found")
    elif response.status_code == 409:
        logging.error("Request made but the resource already exists: %s", response.text)
    else:
        raise Exception(response.text)


def import_index_templates(templates):
    """
    Imports index_templates to OpenSearch directly

    This method uses OpenSearch SDK client to make the call.
    @param templates: stringified JSON body
    """
    logger.info("Firing index_template")

    for template in templates:
        result = opensearch_client.indices.put_index_template("awswaf-logs",
                                                              body=templates[template],
                                                              params={'create': 'false', 'cause': 'Initial templates creation'})
        logging.info(result)


def delete_index_templates():
    """
    Removes ALL index templates in OpenSearch - USE WITH CAUTION
    """
    result = opensearch_client.indices.get_index_template()
    for template in result['index_templates']:
        opensearch_client.indices.delete_index_template(name=template["name"])


def recycle_dashboards_objects():
    """
    Recycles OpenSearch Dashboard items by first deleting them and next recreates them one by one.

    It might be useful to call this method to update some of the resolved strings in JSON documents
    """
    action_dashboard_objects('DELETE')
    action_dashboard_objects('POST')


def delete_dashboards_objects():
    action_dashboard_objects('DELETE')


def main():
    print("Hello World!")
    delete()


if __name__ == "__main__":
    main()
