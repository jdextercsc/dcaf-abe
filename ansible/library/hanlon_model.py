#!/usr/bin/python
DOCUMENTATION = '''
---
module: hanlon_model
short_description: Add a new model to Hanlon
description:
    - A Hanlon model describes how a bare metal server operating system should be configured when provisioned.
    This module adds a model to Hanlon.
version_added: 2.0
author: Joseph Callen
requirements:
    - requests
    - Hanlon server
options:
    base_url:
        description:
            - The url to the Hanlon RESTful base endpoint
        required: true
    template:
        description:
            - The available OS templates for use with Hanlon.  From the CLI ./hanlon model templates
        required: true
    label:
        description:
            - Name of the model
        required: true
notes:
    - This module should run from a system that can access Hanlon directly. Either by using local_action, or using delegate_to.
    - The options for this module are dynamic based on the template type.  The req_metadata_hash and opt_metadata_hash keys map to options
'''

import requests


def _jsonify(data):
    """
    Since I am doing things a little different as certain points in code execution I cannot use
    the provided AnsibleModule methods.  Instead I am modifying for specific use.
    https://github.com/ansible/ansible/blob/devel/lib/ansible/module_utils/basic.py
    :param data:
    :return json:

    """
    for encoding in ("utf-8", "latin-1", "unicode_escape"):
        try:
            return json.dumps(data, encoding=encoding)
        # Old systems using simplejson module does not support encoding keyword.
        except TypeError, e:
            return json.dumps(data)
        except UnicodeDecodeError, e:
            continue
    _fail_json(msg='Invalid unicode encoding encountered')


def _fail_json(**kwargs):
    """
    :param kwargs:
    :return:
    """

    kwargs['failed'] = True
    print _jsonify(kwargs)
    sys.exit(1)


def peek_params():
    """
    Copied code from _load_params(self) - https://github.com/ansible/ansible/blob/devel/lib/ansible/module_utils/basic.py
    So we are going to cheat a little.  In order to use the AnsibleModule we will peek at
    the MODULE_ARGS to determine the basic configuration, model template being used and the URI of the Hanlon server.

    :returns base_url, template
    """
    base_url = ""
    template = ""
    args = MODULE_ARGS
    items = shlex.split(args)

    for x in items:
        try:
            (k, v) = x.split("=", 1)
            if k == 'base_url':
                base_url = v
            elif k == 'template':
                template = v
        except Exception, e:
            _fail_json(msg="this module requires key=value arguments (%s)" % items)

    if len(base_url) == 0:
        _fail_json(msg="missing base_url argument")
    if len(template) == 0:
        _fail_json(msg="missing template argument")

    return base_url, template


def create_new_hanlon_model(module):
    """
    This function creates the body of the POST request to the Hanlon server creating the model via the
    parameters provided by the AnsibleModule

    :param module:
    :param metadata_hash:
    :return json_result:
    """
    metadata_hash = module.params['metadata_hash']
    req_metadata_params = dict()

    base_url = module.params['base_url']
    url = "%s/model" % base_url
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    # We need to generate the req_metadata_params to POST into Hanlon
    for metadata in metadata_hash:
        # Because we have optional metadata we only want to include params
        # that have values assigned
        if metadata in module.params:
            if module.params[metadata]:
                if len(module.params[metadata]) != 0:
                    req_metadata_params.update({metadata: module.params[metadata]})

    payload = {
        'label': module.params['label'],
        'template': module.params['template'],
        'req_metadata_params': req_metadata_params
    }

    # If we are using the boot_local and discover_only models
    # we do not want the image_uuid as its not required.
    # All other models it is required
    if (module.params['template'] != 'boot_local') or (module.params['template'] != 'discover_only'):
        payload.update({'image_uuid': module.params['image_uuid']})

    try:
        req = requests.post(url, data=json.dumps(payload), headers=headers)
        json_result = req.json()
    except requests.ConnectionError as connect_error:
        module.fail_json(msg="Connection Error; confirm Hanlon base_url.", apierror=str(connect_error))
    except requests.Timeout as timeout_error:
        module.fail_json(msg="Timeout Error; confirm status of Hanlon server", apierror=str(timeout_error))
    except requests.RequestException as request_exception:
        module.fail_json(msg="Unknown Request library failure", apierror=str(request_exception))

    return json_result


def create_argument_spec(base_url, model_template):
    """

    :param base_url:
    :param model_template:
    :returns argument_spec, metadata_hash:
    """

    # Hanlon has two types of metadata: required and optional
    metadata_types = "@req_metadata_hash", "@opt_metadata_hash"
    metadata_hash = []
    argument_spec = dict()

    # Each OS template is defined, lets GET the current model template that we are working with
    url = "%s/model/templates/%s" % (base_url, model_template)

    # There is no image when we are using boot_local or discover_only models
    if (model_template == 'boot_local') or (model_template == 'discover_only'):
        argument_spec.update(image_uuid=dict(required=False))
    else:
        argument_spec.update(image_uuid=dict(required=True))

    argument_spec.update(
        base_url=dict(required=True),
        template=dict(required=True),
        label=dict(required=True),
        state=dict(default='present', choices=['present', 'absent'], type='str')
    )

    try:
        req = requests.get(url)
        if req.status_code != 200:
            _fail_json(msg=req.text)

        template = req.json()
    except requests.ConnectionError as connect_error:
        _fail_json(msg="Connection Error; confirm Hanlon base_url.", apierror=str(connect_error))
    except requests.Timeout as timeout_error:
        _fail_json(msg="Timeout Error; confirm status of Hanlon server", apierror=str(timeout_error))
    except requests.RequestException as request_exception:
        _fail_json(msg="Unknown Request library failure", apierror=str(request_exception))

    try:
        for md_type in metadata_types:
            for metadata in template['response'][md_type]:
                # When we generate the req_metadata_params I will only want module.params key values
                # from the metadata.
                metadata_hash.append(metadata[1:])
                argument_spec.update({
                    metadata[1:]: dict(
                        {'required': template['response'][md_type][metadata]['required']}
                    )})
    except Exception as e:
        _fail_json(msg=e.message)

    return argument_spec, metadata_hash


def state_exit_unchanged(module):
    uuid = module.params['uuid']
    module.exit_json(changed=False, uuid=uuid)


def state_destroy_model(module):
    base_url = module.params['base_url']
    uuid = module.params['uuid']

    uri = "%s/model/%s" % (base_url, uuid)

    try:
        req = requests.delete(uri)
        if req.status_code == 200:
            module.exit_json(changed=True)
    except requests.ConnectionError as connect_error:
        module.fail_json(msg="Connection Error; confirm Hanlon base_url.", apierror=str(connect_error))
    except requests.Timeout as timeout_error:
        module.fail_json(msg="Timeout Error; confirm status of Hanlon server", apierror=str(timeout_error))
    except requests.RequestException as request_exception:
        module.fail_json(msg="Unknown Request library failure", apierror=str(request_exception))

    module.exit_json(changed=False)


def state_create_model(module):
    new_model = create_new_hanlon_model(module)
    uuid = new_model['response']['@uuid']
    module.exit_json(changed=True, uuid=uuid)


def hanlon_get_request(uri):
    req = requests.get(uri)
    if req.status_code == 200:
        json_result = req.json()
        return json_result


def check_model_state(module):
    base_url = module.params['base_url']
    model_name = module.params['label']

    uri = "%s/model" % base_url
    try:
        json_result = hanlon_get_request(uri)

        for response in json_result['response']:
            uri = response['@uri']
            model = hanlon_get_request(uri)
            model_response = model['response']
            if model_response['@label'] == model_name:
                return 'present', model_response['@uuid']
    except requests.ConnectionError as connect_error:
        module.fail_json(msg="Connection Error; confirm Hanlon base_url.", apierror=str(connect_error))
    except requests.Timeout as timeout_error:
        module.fail_json(msg="Timeout Error; confirm status of Hanlon server", apierror=str(timeout_error))
    except requests.RequestException as request_exception:
        module.fail_json(msg="Unknown Request library failure", apierror=str(request_exception))

    return 'absent', None


def main():
    (base_url, model_template) = peek_params()
    argument_spec, metadata_hash = create_argument_spec(base_url, model_template)
    module = AnsibleModule(argument_spec=argument_spec)
    module.params['metadata_hash'] = metadata_hash

    hanlon_model_states = {
        'absent': {
            'absent': state_exit_unchanged,
            'present': state_destroy_model
        },
        'present': {
            'absent': state_create_model,
            'present': state_exit_unchanged
        }
    }
    model_state, uuid = check_model_state(module)
    module.params['uuid'] = uuid
    hanlon_model_states[module.params['state']][model_state](module)


from ansible.module_utils.basic import *


if __name__ == '__main__':
    main()