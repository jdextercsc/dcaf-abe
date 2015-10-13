#!/usr/bin/python
__author__ = 'jcallen'
DOCUMENTATION = '''
---
module: hanlon_active_model_facts
short_description: Get the current status of the active_model associated with
description:
    - A Hanlon model describes how a bare metal server operating system should be configured when provisioning
    this module adds a model to Hanlon.
version_added: null
author: Joseph Callen
requirements:
    - requests
    - Hanlon server
options:
    base_url:
        description:
            - The url to the Hanlon RESTful base endpoint
        required: true
        default: null
        aliases: []
    smbios_uuid:
        description:
            - The UUID or hardware ID from the system BIOS
        required: true
        default: null
        aliases: []
'''

import requests


def state_destroy_active_model(module):
    base_url = module.params['base_url']
    uuid = module.params['uuid']

    uri = "%s/active_model/%s" % (base_url, uuid)

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


def check_active_model_state(module):

    base_url = module.params['base_url']
    smbios_uuid = module.params['smbios_uuid']

    url = "%s/active_model?hw_id=%s" % (base_url, smbios_uuid)

    try:
        req = requests.get(url)
        if req.status_code == 200:
            active_model = req.json()
            if 'response' in active_model:
                if '@model' in active_model['response']:
		    if '@label' in active_model['response']['@model']:
			model_label = active_model['response']['@model']['@label']
		    else:
			model_label = ""
                    if '@current_state' in active_model['response']['@model']:
                        current_state = active_model['response']['@model']['@current_state']
                    else:
                        current_state = ""
                    if '@node_ip' in active_model['response']['@model']:
                        node_ip = active_model['response']['@model']['@node_ip']
                    else:
                        node_ip = ""
                    module.params['uuid'] = active_model['response']['@uuid']
                    module.params['current_state'] = current_state
                    module.params['node_ip'] = node_ip
		    module.params['model_label'] = model_label

                    return 'present'
        elif req.status_code == 400:
            module.params['uuid'] = None
            module.params['current_state'] = None
            module.params['node_ip'] = None
            module.params['model_label'] = None
            return 'absent'
        else:
            module.fail_json(msg="Unknown error", apierror=req.text)
    except requests.ConnectionError as connect_error:
        module.fail_json(msg="Connection Error; confirm Hanlon base_url.", apierror=str(connect_error))
    except requests.Timeout as timeout_error:
        module.fail_json(msg="Timeout Error; confirm status of Hanlon server", apierror=str(timeout_error))
    except requests.RequestException as request_exception:
        module.fail_json(msg="Unknown Request library failure", apierror=str(request_exception))


def state_exit_unchanged(module):
    uuid = module.params['uuid']
    current_state = module.params['current_state']
    node_ip = module.params['node_ip']
    model_label = module.params['model_label']

    module.exit_json(changed=False, current_state=current_state, node_ip=node_ip, uuid=uuid, model_label=model_label)


def create_argument_spec():
    argument_spec = dict()

    argument_spec.update(
        base_url=dict(required=True),
        smbios_uuid=dict(required=True),
        state=dict(default='present', choices=['present', 'absent'], type='str')
    )
    return argument_spec


def main():
    argument_spec = create_argument_spec()
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    hanlon_active_model_states = {
        'absent': {
            'absent': state_exit_unchanged,
            'present': state_destroy_active_model
        },
        'present': {
            'absent': state_exit_unchanged,
            'present': state_exit_unchanged
        }
    }

    hanlon_active_model_states[module.params['state']][check_active_model_state(module)](module)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
