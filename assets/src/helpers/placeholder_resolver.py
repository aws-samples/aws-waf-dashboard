import logging
import sys

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def resolve_placeholders(clients, template):
    """
    Resolves placeholders in JSON files to an actual string.

    Some of the JSON files contain placeholders for the internal scripts used by OpenSearch Dashboards.
    These get resolved to actual user's AWS ARNs/ResourceIDs and names of ACL Rules. The method makes AWS API calls to get resources and
    then iterates through each of them creating a predefined script components to be injected into the placeholders.
    Lastly the placeholders are replaced in the entire template
    @param clients: reference to a dictionary of boto3 aws clients for WAF and WAF v2
    @param template: template to resolve the PLACEHOLDERS in
    @return: template with resolved placeholders
    """
    rules_mappings = ""
    webacls_mappings = ""

    mappings = {
        "rules": [
            clients["wafRegional"].list_rules()["Rules"],
            clients["waf"].list_rules()["Rules"]],
        "webacl": [
            clients["wafRegional"].list_web_acls()["WebACLs"],
            clients["waf"].list_web_acls()["WebACLs"]],
        "webacl-v2": [
            clients["wafv2_cloudfront"].list_web_acls(Scope='CLOUDFRONT')['WebACLs'],
            clients["wafv2_regional"].list_web_acls(Scope='REGIONAL')['WebACLs']]}

    mappings["rules"] = [item for sublist in mappings["rules"] for item in sublist]
    mappings["webacl"] = [item for sublist in mappings["webacl"] for item in sublist]
    mappings["webacl-v2"] = [item for sublist in mappings["webacl-v2"] for item in sublist]

    logging.info("Rules detected %s", mappings)

    for element_type in mappings:
        for element in mappings[element_type]:
            if element_type == "rules":
                rules_mappings = rules_mappings + placeholder_resolver("rule", element["RuleId"], element["Name"])
            elif element_type == "webacl":
                webacls_mappings = webacls_mappings + placeholder_resolver(element_type, element["WebACLId"], element["Name"])
            elif element_type == "webacl-v2":
                webacls_mappings = webacls_mappings + placeholder_resolver("webacl", element["ARN"], element["Name"])
            else:
                raise Exception("Unrecognized rule/webacl set")

    template = template.replace("WEBACL_CUSTOM_MAPPINGS", webacls_mappings)
    template = template.replace("RULE_CUSTOM_MAPPINGS", rules_mappings)

    logging.info("Full template: %s", template)

    return template


def placeholder_resolver(condition_var, condition_val, return_val):
    """
    Method generating a single script component to be interpolated
    @param condition_var: variable to be used in the script's if statement
    @param condition_val: value to which script's if statement should compare with
    @param return_val: return component in the script
    @return: Interpolated string
    """
    return "if ({condition_var} == \\\\\\\"{condition_val}\\\\\\\") {{ return \\\\\\\"{return_val}\\\\\\\";}}\\\\n ".format(
        condition_var=condition_var,
        condition_val=condition_val,
        return_val=return_val)
