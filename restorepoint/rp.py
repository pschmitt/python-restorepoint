#!/usr/bin/env bash
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from restorepoint import RestorePoint
import argparse
import logging
import os
import shutil
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
    subparsers = parser.add_subparsers(
        dest='action',
        help='Available commands'
    )
    subparsers.add_parser(
        'list',
        help='List devices'
    )
    backup_parser = subparsers.add_parser(
        'backup',
        help='Backup one or more devices'
    )
    backup_parser.add_argument(
        'DEVICE',
        default='all',
        nargs='*',
        help='Optinal device name to backup (Default: all)'
    )
    export_parser = subparsers.add_parser(
        'export',
        help='Export the latest backup of one or more devices'
    )
    export_parser.add_argument(
        '-d',
        '--destination',
        help='Destination directory (Default: PWD)',
        default=None,
        required=False
    )
    export_parser.add_argument(
        '-f',
        '--force-backup',
        help='Force a backup before exporting it',
        action='store_true',
        default=False
    )
    export_parser.add_argument(
        '-c',
        '--clean',
        help='Empty destination dir if set',
        action='store_true',
        default=False
    )
    export_parser.add_argument(
        'DEVICE',
        default='all',
        nargs='*',
        help='Optinal device name to export (Default: all)'
    )
    return parser.parse_args()


def empty_dir(directory):
    for f in os.listdir(directory):
        file_path = os.path.join(directory, f)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.error(e)


def determine_device_ids(rp, device_names):
    # Determine the device IDs
    device_ids = []
    for dev in device_names:
        dev_id = rp.get_device_id_from_name(dev)
        if not dev_id:
            logger.error('Could not determine device ID of device {}'.format(dev))
        else:
            device_ids.append(dev_id)
    return device_ids


def display_backup_results(rp, result):
    for dev_id, backup_result in result.iteritems():
        dev_name = rp.get_device(dev_id)['Name']
        print(
            '{}: {}'.format(
                dev_name,
                'Backup succeeded' if backup_result else 'Backup failed!'
            )
        )


def display_export_results(rp, res):
    device_ids = rp.get_all_device_ids()
    latest_backups = rp.latest_backups(device_ids)
    for backup_id, backup_result in res:
        dev_name = None
        for b in latest_backups:
            if b['ID'] == backup_id:
                dev_name = rp.get_device(b['DeviceID'])['Name']
        print(
            '{}: {}'.format(
                dev_name,
                'Export succeeded' if backup_result else 'Export failed!'
            )
        )


def main():
    args = parse_args()
    rp = RestorePoint(
        hostname=args.hostname,
        username=args.username,
        password=args.password,
        verify=not args.insecure
    )
    exit_code = 0
    if args.action == 'list':
        device_names = sorted(
            [x['Name'] for x in rp.list_devices()],
            key=lambda s: s.lower()
        )
        for dev in device_names:
            print(dev)
    elif args.action == 'backup':
        if args.DEVICE == ['all']:
            res = rp.backup_all_devices_block()
        else:
            # Determine the device IDs
            device_ids = determine_device_ids(rp, args.DEVICE)
            # Backup the devices whose IDs could be determined
            res = rp.backup_devices_block(device_ids)
        # Print results
        display_backup_results(rp, res)
        # Set the exit code to 1 if at least one backup failed
        exit_code = 0 if all(res.values()) else 1
    elif args.action == 'export':
        # Clean/empty the destination dir if requested
        if args.clean and args.destination is None:
            print(
                'You need to set the destination dir when --clean is set',
                file=sys.stderr
            )
            sys.exit(3)
        elif args.clean:
            empty_dir(args.destination)
        # Export backups
        if args.DEVICE == ['all']:
            if args.force_backup:
                backup_res = rp.backup_all_devices_block()
            res = rp.export_all_latest_backups(args.destination)
        else:
            # Determine the device IDs
            device_ids = determine_device_ids(rp, args.DEVICE)
            if args.force_backup:
                backup_res = rp.backup_devices_block(device_ids)
            # Export the devices whose IDs could be determined
            res = rp.export_latest_backups(device_ids, args.destination)
        # Print results
        if args.force_backup:
            display_backup_results(rp, backup_res)
            exit_code = 0 if all(backup_res.values()) else 1
        display_export_results(rp, res)
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
