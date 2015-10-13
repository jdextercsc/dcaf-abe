#!/usr/bin/python

DOCUMENTATION = '''
---
# If a key doesn't apply to your module (ex: choices, default, or
# aliases) you can use the word 'null', or an empty list, [], where
# appropriate.
module: hanlon_policy
short_description: Add a new policy to Hanlon
description:
    - A Hanlon policy describes the rules for binding a node to operating system model.
version_added: null
author: Joseph Callen, Russell Teague
notes: null
requirements:
    - Hanlon server
options:
    base_url:
        description:
            - The url to the Hanlon RESTful base endpoint
        required: true
        default: null
        aliases: []
    template:
        description:
            - The available policy templates for use with Hanlon.  From the CLI ./hanlon policy templates
        required: true
        default: null
        aliases: []
    label:
        description:
            - The name of the policy
        required: true
        default: null
        aliases: []
    model_uuid:
        description:
            - The model UUID to use for this policy
        required: true
        default: null
        aliases: []
    tags:
        description:
            - The tags which should match the node for binding
        required: true
        default: null
        aliases: []
    enabled:
        description:
            - The state of the policy
        required: false
        default: true
        aliases: []
    line_number:
        description:
            - The line number in the policy table the policy should exist
        required: false
        default: null
        aliases: []
    is_default:
        description:
            - Set policy as system default
        required: false
        default: null
        aliases: []
notes:
    - This module should run from a system that can access Hanlon directly. Either by using local_action, or using delegate_to.
'''

import requests


def state_create_policy(module):
    base_url = module.params['base_url']
    url = "%s/policy" % base_url
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    payload = {
        'template':   module.params['policy_template'],
        'label':      module.params['label'],
        'model_uuid': module.params['model_uuid'],
    }

    if None in payload.values():
        module.fail_json(msg="Missing required arguments for creating a new policy.")

    if module.params['enabled'] is not None:
        payload.update({
            'enabled': module.params['enabled']
        })
    if module.params['is_default'] is not None:
        payload.update({
            'is_default': module.params['is_default']
        })
    if module.params['tags'] is not None:
        payload.update({
            'tags': module.params['tags']
        })
    if module.params['maximum'] is not None:
        payload.update({
            'maximum': str(module.params['maximum'])
        })
    if module.params['line_number'] is not None:
        payload.update({'line_number': str(module.params['line_number'])})

    try:
        if not module.check_mode:
            req = requests.post(url, data=json.dumps(payload), headers=headers)
            if req.status_code == 201:
                json_result = req.json()
                uuid = json_result['response']['@uuid']
                module.exit_json(changed=True, uuid=uuid)
            else:
                module.fail_json(msg="Unknown Hanlon API error", apierror=req.text)
        module.exit_json(changed=True, uuid=None)
    except requests.ConnectionError as connect_error:
        module.fail_json(msg="Connection Error; confirm Hanlon base_url.", apierror=str(connect_error))
    except requests.Timeout as timeout_error:
        module.fail_json(msg="Timeout Error; confirm status of Hanlon server", apierror=str(timeout_error))
    except requests.RequestException as request_exception:
        module.fail_json(msg="Unknown Request library failure", apierror=str(request_exception))


def hanlon_get_request(uri):
    req = requests.get(uri)
    if req.status_code == 200:
        json_result = req.json()
        return json_result, True
    else:
        return None, False

def check_diff(policy_response, module):
    policy_name = module.params['label']
    if policy_response['@label'] == policy_name:
        module.params['uuid'] = policy_response['@uuid']

        # The Hanlon API is a little screwy with tags
        # the PUT/POST wants a comma delimited string
        # the JSON result from a Policy query is an array/list of
        # strings, adding to a complication when comparing.
        # Along with the fact that the return type of integers
        # is actually a string.

        if module.params['enabled'] is not None:
            if module.params['enabled'] != policy_response['@enabled']:
                return 'update'
        if module.params['line_number'] is not None:
            if str(module.params['line_number']) != str(policy_response['@line_number']):
                return 'update'
        if module.params['tags'] is not None:
            tags = module.params['tags'].split(",")
            if tags != policy_response['@tags']:
                return 'update'
        if module.params['maximum'] is not None:
            if str(module.params['maximum']) != str(policy_response['@maximum_count']):
                return 'update'
        return 'present'
    else:
        return 'absent'


def check_policy_state(module):
    base_url = module.params['base_url']
    uri = "%s/policy" % base_url
    module.params['uuid'] = None
    state = 'absent'
    
    try:
        json_result, http_success = hanlon_get_request(uri)

        for response in json_result['response']:
            uri = response['@uri']

            # if this is run in a play concurrently with inventory
            # objects the uri may no longer exist if the
            # task is defined as state: absent.  If 
            # the result is not available skip it.

            policy, http_success = hanlon_get_request(uri)
            if http_success:
                policy_response = policy['response']
                state = check_diff(policy_response, module)
                if state is not 'absent':
                    break
        return state

    except requests.ConnectionError as connect_error:
        module.fail_json(msg="Connection Error; confirm Hanlon base_url.", apierror=str(connect_error))
    except requests.Timeout as timeout_error:
        module.fail_json(msg="Timeout Error; confirm status of Hanlon server", apierror=str(timeout_error))
    except requests.RequestException as request_exception:
        module.fail_json(msg="Unknown Request library failure", apierror=str(request_exception))


def state_update_policy(module):
    base_url = module.params['base_url']
    uuid = module.params['uuid']
    url = "%s/policy/%s" % (base_url, uuid)
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    payload = {'enabled': module.params['enabled']}

    if module.params['line_number'] is not None:
        payload.update({'new_line_number': str(module.params['line_number'])})
    if module.params['tags'] is not None:
        payload.update({'tags': module.params['tags']})
    if module.params['maximum'] is not None:
        payload.update({'maximum': str(module.params['maximum'])})

    try:
        if not module.check_mode:
            req = requests.put(url, data=json.dumps(payload), headers=headers)
            if req.status_code == 200:
                module.exit_json(changed=True, uuid=uuid)
            else:
                module.fail_json(msg="Unknown Hanlon API error", apierror=req.text)
        module.exit_json(changed=True, uuid=uuid)
    except requests.ConnectionError as connect_error:
        module.fail_json(msg="Connection Error; confirm Hanlon base_url.", apierror=str(connect_error))
    except requests.Timeout as timeout_error:
        module.fail_json(msg="Timeout Error; confirm status of Hanlon server", apierror=str(timeout_error))
    except requests.RequestException as request_exception:
        module.fail_json(msg="Unknown Request library failure", apierror=str(request_exception))


def state_exit_unchanged(module):
    uuid = module.params['uuid']
    module.exit_json(changed=False, uuid=uuid)


def state_destroy_policy(module):
    base_url = module.params['base_url']
    uuid = module.params['uuid']

    uri = "%s/policy/%s" % (base_url, uuid)

    try:
        if not module.check_mode:
            req = requests.delete(uri)
            if req.status_code == 200:
                module.exit_json(changed=True)
            else:
                module.fail_json(msg="Unknown error", apierror=req.text)
        module.exit_json(changed=True)
    except requests.ConnectionError as connect_error:
        module.fail_json(msg="Connection Error; confirm Hanlon base_url.", apierror=str(connect_error))
    except requests.Timeout as timeout_error:
        module.fail_json(msg="Timeout Error; confirm status of Hanlon server", apierror=str(timeout_error))
    except requests.RequestException as request_exception:
        module.fail_json(msg="Unknown Request library failure", apierror=str(request_exception))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            base_url=dict(required=True, type='str'),
            policy_template=dict(required=False, type='str'),
            label=dict(required=True, type='str'),
            model_uuid=dict(required=False, type='str'),
            tags=dict(required=False, type='str'),
            enabled=dict(required=False, type='bool', default=True),
            line_number=dict(required=False, type='int'),
            is_default=dict(required=False, type='bool'),
            maximum=dict(required=False, type='int'),
            state=dict(required=False, default='present', choices=['present', 'absent'], type='str')
        ), supports_check_mode=True
    )

    hanlon_policy_states = {
        'absent': {
            'absent': state_exit_unchanged,
            'present': state_destroy_policy
        },
        'present': {
            'absent': state_create_policy,
            'present': state_exit_unchanged,
            'update': state_update_policy
        }
    }
    policy_state = check_policy_state(module)

    hanlon_policy_states[module.params['state']][policy_state](module)


from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
