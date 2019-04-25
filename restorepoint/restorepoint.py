#!/usr/bin/env python
# coding: utf-8

'''
https://restorepoint.freshdesk.com/support/solutions/articles/9000098438-api-documentation
'''

from __future__ import print_function
from __future__ import unicode_literals
from dateutil.parser import parse
import pathos.multiprocessing as mp
import cgi
import copy
import functools
import json
import logging
import os
import requests
import time
import urllib.parse


# logging.basicConfig(level=logging.WARNING)
# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Silence requests warnings
requests.packages.urllib3.disable_warnings()
logging.getLogger('requests').setLevel(logging.WARNING)


class LoginException(Exception):
    pass


class PermissionException(Exception):
    pass


class GenericException(Exception):
    pass


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
        try:
            return r.history[0].cookies
        except Exception as exc:
            raise LoginException(exc)

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
            msg = j.get('msg', None)
            if msg == 'Error':
                error = j.get('error', None)
                logger.error('Request errored out: {}'.format(error))
                if error in ['Unauthorised', 'Unauthorized']:
                    raise PermissionException()
                else:
                    raise GenericException(error)
            return msg
        else:
            logger.error('No key named "msg" found in JSON response')
            return j

    def __rq(self, msg, params={}):
        data = {'msg': msg, 'params': params}
        return self.__request(data=data)

    def __list(self, object_type, params={}):
        data = {'msg': 'list{}'.format(object_type), 'params': params}
        return self.__request(data=data)

    def list_devices(self, ignore_disabled=False):
        devices = self.__list('devices').get('Rows')
        if ignore_disabled:
            return [x for x in devices if x['Disabled'] == 'No']
        return devices

    def list_devices_status(self):
        return self.__list('devicesstatus')

    def list_device_status(self, device_id):
        res = [x for x in self.list_devices_status() if x['ID'] == device_id]
        if res:
            return res[0]

    def list_backups(self, device_id):
        return self.__list('backups')

    def list_device_backups(self, device_id):
        return self.__rq(
            msg='devicebackups',
            params={'device': {'id': device_id}}
        )

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

    def get_all_device_ids(self, ignore_disabled=False):
        if ignore_disabled:
            return [x['ID'] for x in self.list_devices()
                    if x['Disabled'] == 'No']
        else:
            return [x['ID'] for x in self.list_devices()]

    def get_device_id_from_name(self, device_name):
        for dev in self.list_devices():
            if dev['Name'] == device_name:
                return dev['ID']

    def get_device_name_from_id(self, device_id):
        for dev in self.list_devices():
            if dev['ID'] == device_id:
                return dev['Name']

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
        # Wait a second before checking the status of backups, otherwise the
        # first device's backup result may be falsely set to False (ie. failed
        # state)
        time.sleep(1)
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

    def latest_backups(self, device_ids):
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
        device_ids = self.get_all_device_ids()
        return self.backup_devices(device_ids)

    def backup_all_devices_block(self):
        device_ids = self.get_all_device_ids()
        return self.backup_devices_block(device_ids)

    def list_failed_backups(self):
        return [x for x in self.list_devices_status() if not x['BackupStatus']]

    def export_backup(self, backup_id, dest_dir=None, chunk_size=2000):
        data = {
            'msg': 'exportbackup',
            'params': {
                'ids': [backup_id],
                'command': 'Browser',
                'configtype': '',
                'credentials': {'password': '', 'username': ''},
                'isdownload': True,
                'location': '',
                'value': ''
            }
        }
        url = '{}/data?data={}'.format(
            self.API,
            urllib.parse.quote(json.dumps(data), safe='{}:,[]')
        )
        logger.info('GET Data: {}'.format(data))

        r = requests.get(
            url=url,
            cookies=self._cookies,
            verify=self.verify,
            stream=True
        )
        filename = cgi.parse_header(r.headers['Content-Disposition'])[1]['filename']
        filepath = os.path.join(dest_dir if dest_dir else os.getcwd(), filename)
        logger.info('Export backup {} to {}'.format(backup_id, filepath))

        r.raise_for_status()
        with open(filepath, 'wb') as f:
            # r.raw.decode_content = True
            # shutil.copyfileobj(r.raw, f)
            for chunk in r.iter_content(chunk_size):
                f.write(chunk)
        return backup_id, filepath

    def export_latest_backups(self, device_ids, dest_dir=None):
        latest_backups = [b['ID'] for b in self.latest_backups(device_ids)]
        pool = mp.ProcessingPool()
        func = functools.partial(self.export_backup, dest_dir=dest_dir)
        res = pool.amap(func, latest_backups)
        while not res.ready():
            logger.info(
                'Remaining: {}/{}'.format(
                    len(latest_backups) - res._number_left,
                    len(latest_backups)
                )
            )
            time.sleep(1)
        return res.get()

        # exports = []
        # for b in latest_backups:
        #     logger.info(
        #         'Process backup {}. Progress: {}/{}'.format(
        #             b,
        #             latest_backups.index(b) + 1,
        #             len(latest_backups)
        #         )
        #     )
        #     exports.append(
        #         {
        #             'Backup ID': b,
        #             'Result': self.export_backup(b, dest_dir)
        #         }
        #     )
        # return exports

    def export_all_latest_backups(self, dest_dir=None):
        device_ids = self.get_all_device_ids()
        return self.export_latest_backups(device_ids, dest_dir)

    def abort_backup_job(self, job_id):
        return self.__rq(msg='abortjob', params={'jobid': job_id})

    def delete_backups(self, backup_ids):
        logger.info(
            'Delete backups: {}'.format(
                ', '.join([str(x) for x in backup_ids])
            )
        )
        return self.__rq(msg='deletebackupids', params={'ids': backup_ids})

    def prune_backups(self, device_id, keep=10):
        backups = self.get_device_backups(device_id)
        backups_sorted = sorted(
            backups,
            key=lambda x: parse(x['Dt']),
            reverse=True
        )
        backups_keep = backups_sorted[0:keep]
        backups_prune = [x for x in backups_sorted if x not in backups_keep]
        logger.debug('Pruning {} backups'.format(len(backups_prune)))
        if backups_prune:
            return self.delete_backups([x['ID'] for x in backups_prune])
