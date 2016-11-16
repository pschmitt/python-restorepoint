#!/usr/bin/env bash
# coding: utf-8


from __future__ import print_function
from __future__ import unicode_literals
from restorepoint import RestorePoint
import argparse
import logging
import sys


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-u',
        '--username',
        required=True,
        help='Username to connect to RestorePoint'
    )
    parser.add_argument(
        '-p',
        '--password',
        required=True,
        help='Password to connect to RestorePoint'
    )
    parser.add_argument(
        '-H',
        '--hostname',
        help='RestorePoint Hostname',
        required=True
    )
    parser.add_argument(
        '-k',
        '--insecure',
        action='store_true',
        help='Skip SSL cert verification',
        default=False
    )
    parser.add_argument(
        'DEVICE',
        default='all',
        nargs='*',
        help='Optinal device name to backup (Default: all)'
    )
    return parser.parse_args()


def main():
    args = parse_args()
    rp = RestorePoint(
        hostname=args.hostname,
        username=args.username,
        password=args.password,
        verify=not args.insecure
    )
    if args.DEVICE == 'all':
        res = rp.backup_all_devices_block()
    else:
        # Determine the device IDs
        device_ids = []
        for dev in args.DEVICE:
            dev_id = rp.get_device_id_from_name(dev)
            if not dev_id:
                logger.error('Could not determine device ID of device {}'.format(dev))
            else:
                device_ids.append(dev_id)
        # Backup the devices whose IDs could be determined
        res = rp.backup_devices_block(device_ids)
    # Print results
    for dev_id, backup_result in res.iteritems():
        dev_name = rp.get_device(dev_id)['Name']
        print(
            '{}: {}'.format(
                dev_name,
                'Backup succeeded ✓' if backup_result else 'Backup failed! ✗'
            )
        )
    # Set the exit code to 1 if at least one backup failed
    sys.exit(0 if all(res.values()) else 1)


if __name__ == '__main__':
    main()
