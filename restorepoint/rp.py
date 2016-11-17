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
        'DEVICE',
        default='all',
        nargs='*',
        help='Optinal device name to export (Default: all)'
    )
    return parser.parse_args()


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


def main():
    args = parse_args()
    rp = RestorePoint(
        hostname=args.hostname,
        username=args.username,
        password=args.password,
        verify=not args.insecure
    )
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
    elif args.action == 'export':
        if args.DEVICE == ['all']:
            if args.force_backup:
                rp.backup_all_devices_block()
            res = rp.export_all_latest_backups(args.destination)
        else:
            # Determine the device IDs
            device_ids = determine_device_ids(rp, args.DEVICE)
            if args.force_backup:
                rp.backup_devices_block(device_ids)
            # Export the devices whose IDs could be determined
            res = rp.export_latest_backups(device_ids, args.destination)
        # Print results
        for backup_id, backup_result in res:
            print(
                '{}: {}'.format(
                    backup_result,
                    'Export succeeded ✓' if backup_result else 'Export failed! ✗'
                )
            )


if __name__ == '__main__':
    main()
