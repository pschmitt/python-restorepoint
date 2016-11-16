#!/usr/bin/env python
# coding: utf-8

'''
https://restorepoint.freshdesk.com/support/solutions/articles/9000098438-api-documentation
'''

from __future__ import unicode_literals
import copy
import requests
import logging
import time


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Silence requests warnings
requests.packages.urllib3.disable_warnings()
logging.getLogger('requests').setLevel(logging.WARNING)


class RestorePoint(object):
    def __init__(self, hostname, username, password, port=443, verify=True):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.verify = verify
        self.API = 'https://{}:{}'.format(hostname, port)
        self._cookies = self.login()

    def login(self):
        url = '{}/login'.format(self.API)
        data = {
            'username': self.username,
            'password': self.password,
            # 'rusername': self.username,
            # 'token': None,
            # 'answer': None
        }
        r = requests.post(url=url, data=data, verify=self.verify)
        r.raise_for_status()
        return r.history[0].cookies

    def __request(self, data):
        url = '{}/data'.format(self.API)
        logger.info('POST Data: {}'.format(data))
        r = requests.post(
            url=url,
            cookies=self._cookies,
            json=data,
            verify=self.verify
        )
        r.raise_for_status()
        j = r.json()
        logger.debug('JSON Response: {}'.format(j))
        if 'msg' in j:
            return j['msg']
        else:
            logger.error('No key named "msg" found in JSON response')
            return j

    def __rq(self, msg, params={}):
        data = {'msg': msg, 'params': params}
        return self.__request(data=data)

    def __list(self, object_type, params={}):
        data = {'msg': 'list{}'.format(object_type), 'params': params}
        return self.__request(data=data)

    def list_devices(self):
        return self.__list('devices')

    def list_devices_status(self):
        return self.__list('devicesstatus')

    def list_device_status(self, device_id):
        res = [x for x in self.list_devices_status() if x['ID'] == device_id]
        if res:
            return res[0]

    def list_backups(self, device_id):
        return self.__list('backups')

    def list_plugins(self):
        return self.__list('plugins')

    def list_domains(self):
        return self.__list('domains')

    def list_asset_types(self):
        return self.__list('assettypes')

    def list_roles(self):
        return self.__list('roles')

    def list_users(self):
        return self.__list('users')

    def list_commands(self):
        return self.__list('commands')

    def list_credentials(self):
        return self.__list('credentials')

    def list_agents(self):
        return self.__list('agents')

    def list_templates(self):
        return self.__list('templates')

    def list_rule_groups(self):
        return self.__list('rulegroups')

    def list_device_logs(self, params):
        # Example request data:
        # {device: {id: 38}, sparams: {num: 175, start: 0, search: "", order: "dt", isasc: false}}
        return self.__list('devicelogs', params)

    def list_device_syslogs(self, params):
        # Example request data:
        # {device: {id: 38}, sparams: {num: 175, start: 0, search: "", order: "dt", isasc: false}}
        return self.__list('devicesyslogs', params)

    def list_device_command_output(self, params):
        # Example request data:
        # {device: {id: 38}, sparams: {num: 175, start: 0, search: "", order: "dt", isasc: false}}
        return self.__list('devicecommandoutput', params)

    def get_keys(self):
        return self.__rq('getkeys')

    def get_device(self, device_id):
        return self.__rq(
            msg='viewdevice',
            params={'device': {'id': device_id}}
        )

    def test_user_password(self, password):
        return self.__rq(
            msg='testuserpw',
            params={'value': password}
        )

    def __get_all_device_ids(self):
        return [x['ID'] for x in self.list_devices()]

    def get_device_id_from_name(self, device_name):
        for dev in self.list_devices():
            if dev['Name'] == device_name:
                return dev['ID']

    def get_device_backups(self, device_id):
        return self.__rq(
            msg='devicebackups',
            params={'device': {'id': device_id}}
        )

    def backup_devices(self, device_ids):
        if type(device_ids) is not list:
            target_device_ids = [device_ids]
        else:
            target_device_ids = device_ids
        data = {'msg': 'backupdevices', 'params': {'ids': target_device_ids}}
        return self.__request(data=data)

    def backup_device_block(self, device_id, sleep_interval):
        backup_action = self.backup_devices(device_id)
        logger.info('Backup action: {}'.format(backup_action))
        device = self.get_device(device_id)
        while device['State'] != 'Idle':
            device = self.get_device(device_id)
            logger.info('Device Status: {}'.format(device['State']))
            time.sleep(sleep_interval)
        return device['BackupStatus']

    def backup_devices_block(self, device_ids, sleep_interval=2):
        backup_action = self.backup_devices(device_ids)
        logger.info('Backup action: {}'.format(backup_action))

        result = {}
        devices = copy.deepcopy(device_ids)
        while devices:
            for dev_id in devices:
                dev_info = self.get_device(dev_id)
                if dev_info['State'] == 'Idle':
                    devices.remove(dev_id)
                    result[dev_id] = dev_info['BackupStatus']
            logger.info(
                'Remaining devices: {}/{}'.format(
                    len(devices), len(device_ids)
                )
            )
            time.sleep(sleep_interval)
        return result

    def latest_backups(self, device_ids=[]):
        return self.__rq(
            msg='latestbackups',
            params={'ids': device_ids}
        )

    def device_errors(self, device_id):
        return self.__rq(
            msg='deviceerrors',
            params={'id': device_id}
        )

    def backup_all_devices(self):
        device_ids = self.__get_all_device_ids()
        return self.backup_devices(device_ids)

    def backup_all_devices_block(self):
        device_ids = self.__get_all_device_ids()
        return self.backup_devices_block(device_ids)

    def list_failed_backups(self):
        return [x for x in self.list_devices_status() if not x['BackupStatus']]
