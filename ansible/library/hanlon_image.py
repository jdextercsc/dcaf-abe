#!/usr/bin/python

DOCUMENTATION = '''
---
module: hanlon_image
short_description: Add a new image to Hanlon
description:
    -
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
    type:
        description:
            - The available OS templates for use with Hanlon.  From the CLI ./hanlon model templates
        required: true
        default: null
        aliases: []
    path:
        description:
            - The path to an ISO image for either an OS, hypervisor or microkernel
        required: true
        default: null
        aliases: []
    name:
        description: null
        required: false
        default: null
        aliases: []
    version:
        description:
            - The version of the OS
        required: false
        default: null
        aliases: []

notes:
    - This module should run from a system that can access Hanlon directly. Either by using local_action, or using delegate_to.
'''

import requests


def state_exit_unchanged(module):
    uuid = module.params['uuid']
    module.exit_json(changed=False, uuid=uuid)


def state_destroy_image(module):
    base_url = module.params['base_url']
    uuid = module.params['uuid']

    uri = "%s/image/%s" % (base_url, uuid)

    try:
        if not module.check_mode:
            req = requests.delete(uri)
            if req.status_code == 200:
                module.exit_json(changed=True)
            else:
                module.fail_json(msg="Unknown Hanlon API error", apierror=req.text)
        module.exit_json(changed=True)
    except requests.ConnectionError as connect_error:
        module.fail_json(msg="Connection Error; confirm Hanlon base_url.", apierror=str(connect_error))
    except requests.Timeout as timeout_error:
        module.fail_json(msg="Timeout Error; confirm status of Hanlon server", apierror=str(timeout_error))
    except requests.RequestException as request_exception:
        module.fail_json(msg="Unknown Request library failure", apierror=str(request_exception))

    module.exit_json(changed=False)


def state_create_image(module):
    base_url = module.params['base_url']
    url = "%s/image" % base_url
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    uuid = None

    payload = {
        'type': module.params['type'],
        'path': module.params['path']
    }

    if module.params['type'] == 'os':
        payload.update({
            'name': module.params['name'],
            'version': module.params['version']
        })

    try:
        if not module.check_mode:
            req = requests.post(url, data=json.dumps(payload), headers=headers)
            if req.status_code == 201:
                json_result = req.json()
                uuid = json_result['response']['@uuid']
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


def hanlon_get_request(uri):
    req = requests.get(uri)
    if req.status_code == 200:
        json_result = req.json()
        return json_result, True
    else:
        return None, False


def check_image_state(module):
    base_url = module.params['base_url']
    uri = "%s/image" % base_url
    module.params['uuid'] = None
    path = module.params['path']

    path_split = path.split("/")
    filename = path_split[len(path_split)-1]

    try:
        json_result, http_success = hanlon_get_request(uri)

        for response in json_result['response']:
            uri = response['@uri']
            image, http_success = hanlon_get_request(uri)
            if http_success:
                image_response = image['response']
                if image_response.get('@filename') == filename:
                    module.params['uuid'] = image_response['@uuid']
                    return 'present'
        return 'absent'
    except requests.ConnectionError as connect_error:
        module.fail_json(msg="Connection Error; confirm Hanlon base_url.", apierror=str(connect_error))
    except requests.Timeout as timeout_error:
        module.fail_json(msg="Timeout Error; confirm status of Hanlon server", apierror=str(timeout_error))
    except requests.RequestException as request_exception:
        module.fail_json(msg="Unknown Request library failure", apierror=str(request_exception))


def create_argument_spec():
    argument_spec = dict()

    argument_spec.update(
        base_url=dict(required=True, type='str'),
        type=dict(required=True, type='str'),
        path=dict(required=True, type='str'),
        name=dict(required=False, type='str'),
        version=dict(required=False, type='str'),
        state=dict(default='present', choices=['present', 'absent'], type='str'),
    )
    return argument_spec


def main():
    argument_spec = create_argument_spec()
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    hanlon_image_states = {
        'absent': {
            'absent': state_exit_unchanged,
            'present': state_destroy_image
        },
        'present': {
            'absent': state_create_image,
            'present': state_exit_unchanged,
        }
    }
    image_state = check_image_state(module)

    hanlon_image_states[module.params['state']][image_state](module)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
