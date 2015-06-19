#!/usr/bin/env python
from datetime import datetime
from itertools import groupby
from time import sleep
import argparse
import sys
import traceback

from boto import ec2

# Number of snapshots to keep, when we rotate.  If we pick adhoc, we don't rotate those.
keep_week = 2
keep_day = 7
keep_month = 1

def get_ec2_connection(aws_access_key_id, aws_secret_access_key, region_name):
    """
    :param aws_access_key: if None, we will use the .aws/config on this system
    :param aws_secret_key: if None we wil use the .aws/config on this system
    :param region_name: This is a region string i.e. us-east-1
    :return: a ec2_connection objects
    """
    conn = ec2.connect_to_region(aws_access_key_id=aws_access_key_id,
                                 aws_secret_access_key=aws_secret_access_key,
                                 region_name=region_name)

    return conn


def print_list(llist):
    return '[%s]' % '\n'.join(map(str, llist))


def print_exception(e):
    (typeE, value, tracebackPrev) = sys.exc_info()
    print(str(typeE) + ':' + str(value))
    print(" PREV=\n" + print_list(traceback.extract_tb(tracebackPrev)))


def set_resource_tags_local(conn, resource, tags):
    for tag_key, tag_value in tags.iteritems():
        if tag_key not in resource.tags or resource.tags[tag_key] != tag_value:
            resource.add_tag(tag_key, tag_value)


def get_resource_tags_local(conn, resource_id):
    resource_tags = {}
    if resource_id:
        tags = conn.get_all_tags({'resource-id': resource_id})
        for tag in tags:
            # Tags starting with 'aws:' are reserved for internal use
            if not tag.name.startswith('aws:'):
                resource_tags[tag.name] = tag.value
    return resource_tags


def rotate_snapshots(vol, period):
    """
    For a given volume, find its snapshots and rotate them
    :param vol: An AWS Volumen object
    :param period: day, week month
    :return: Number of snapshots deleted
    """
    total_deletes = 0
    snapshots = vol.snapshots()
    deletelist = []
    for snap in snapshots:
        desc = snap.description

        if desc.find('WEEK Snapshot') > 0 and period == 'week':
            deletelist.append(snap)
        elif desc.find('DAY Snapshot') > 0 and period == 'day':
            deletelist.append(snap)
        elif desc.find('MONTH Snapshot') > 0 and period == 'month':
            deletelist.append(snap)

    def date_compare(snap1, snap2):
        if snap1.start_time < snap2.start_time:
            return -1
        elif snap1.start_time == snap2.start_time:
            return 0
        return 1

    deletelist.sort(date_compare)
    if period == 'day':
        keep = keep_day
    elif period == 'week':
        keep = keep_week
    elif period == 'month':
        keep = keep_month
    else:
        raise Exception("Invalid period {}".format(period))

    delta = len(deletelist) - keep
    for i in range(delta):
        del_message = 'Deleting snapshot ' + deletelist[i].description
        print del_message
        deletelist[i].delete()
        total_deletes += 1
    return total_deletes


def make_snapshots(conn, period, tag_namevalue, share_account):
    """
    Bases on a scope, we will look for tags on both volumes and instances.  Once found we will snapshot those.
    If there are tags that we expect, use those, or else just keep it anonymous, and use the name

    :param conn: ec2 connection
    :param period: day, month, week, the category of the snapshot
    :param tag_namevalue: a tuple with key,value pair
    :param share_account: Amazon Account Id integer
    :return:
    """
    print 'Finding volumes that match the requested tag {}:{}'.format(tag_namevalue[0], tag_namevalue[1])
    vols_from_tags = conn.get_all_volumes(filters={'tag:' + tag_namevalue[0]: tag_namevalue[1]})

    reservations = conn.get_all_instances(filters={"tag:{}".format(tag_namevalue[0]): tag_namevalue[1]})
    all_instances = [instance for reservation in reservations for instance in reservation.instances]

    # So to snap on over, we need to backup everything that is not the root (/dev/sda1).
    # If there is ONLY one drive, then assume its the root.
    vols_from_instances = []
    ROOT_DRIVE = '/dev/sda1'
    for instance in all_instances:
        all_vols = conn.get_all_volumes(filters={'attachment.instance-id': instance.id})

        if len (all_vols) == 0:
            print "Warning: No volumes for instance {} are for backup".format(instance.id)
        elif len(all_vols) == 1:
            vols_from_instances += all_vols
        else:
            vols_from_instances += [vol for vol in all_vols if vol.attach_data.device != ROOT_DRIVE]

    sorted_vols = sorted(vols_from_instances + vols_from_tags, key=lambda x:x.id)
    deduped_vols = [next(x[1]) for x in groupby(sorted_vols, key=lambda x: x.id)]

    # Counters
    total_creates = 0
    total_deletes = 0
    count_errors = 0
    count_success = 0
    count_total = 0

    date_str = datetime.now().strftime("%Y%m%dT%H%M%S")
    for vi, vol in enumerate(deduped_vols):
        try:
            count_total += 1
            tags_volume = get_resource_tags_local(conn, vol.id)
            if 'Cluster' and 'Uid' in tags_volume:
                description = "{} Interana {} Snapshot {}-{} for volume {}".format(tags_volume['Cluster'],
                                                                                   period.upper(),
                                                                                   tags_volume['Uid'], date_str, vol.id)
            else:
                description = "{} Interana {} Snapshot {}-{} for volume {}".format(':'.join(tag_namevalue),
                                                                                   period.upper(),
                                                                                   'UidUnknown',
                                                                                   date_str,
                                                                                   vol.id)
                tags_volume[tag_namevalue[0]] = tag_namevalue[1]
            tags_volume['group_id'] = date_str

            if share_account is not None:
                description += " shared with account {}".format(share_account)
            current_snap = vol.create_snapshot(description)
            set_resource_tags_local(conn, current_snap, tags_volume)
            if share_account is not None:
                current_snap.share(user_ids=[share_account])

            print '** {} ** Snapshot created with description: {} and tags: {}'.format(vi, description,
                                                                                       str(tags_volume))

            total_creates += 1

            if period != 'adhoc':
                total_deletes += rotate_snapshots(vol, period)
            sleep(3)
        except Exception, e:
            print_exception(e)
            print 'Error in processing volume with id: ' + vol.id
            count_errors += 1
        else:
            count_success += 1

    result = '\nFinished making snapshots at {} with {} snapshots of {} possible.\n\n'.format(
        datetime.today().strftime('%d-%m-%Y %H:%M:%S'),
        count_success,
        count_total)

    message = result
    message += "\nTotal snapshots created: " + str(total_creates)
    message += "\nTotal snapshots errors: " + str(count_errors)
    message += "\nTotal snapshots deleted: " + str(total_deletes) + "\n"

    print '\n' + message + '\n'
    print result


def main():
    parser = argparse.ArgumentParser(description="Makes snapshots of ebs volumes on AWS",
                                     epilog='''
    Notes:
    Assumes we have applied tags to either volumes or instances.  
''')

    parser.add_argument('-p', '--period', choices=['day', 'week', 'month', 'adhoc'],
                        help='Specify period of snapshot',
                        required=True)

    parser.add_argument('-t', '--tag_namevalue',
                        help='Specify a tag name and value, i.e. mycustomtag:True',
                        required=True)

    parser.add_argument('-a', '--aws_access_key',
                        help='AWS Access key, None if using instance profile',
                        default=None)

    parser.add_argument('-x', '--aws_secret_key',
                        help='AWS Secret key, None if using instance profile',
                        default=None)

    parser.add_argument('-r', '--region',
                        help='region, i.e. us-east-1',
                        required=True)

    parser.add_argument('-s', '--share_account', 
                         help='Shares the snapshot with an account. Default no share is made', default=None)

    args = parser.parse_args()

    ec2_conn = get_ec2_connection(args.aws_access_key, args.aws_secret_key, args.region)

    if ec2_conn is None:
        raise Exception("Could not connect to AWS with supplied credentials")
    namevalue = tuple(args.tag_namevalue.split(':'))
    if len(namevalue) != 2:
        raise Exception("Invalid Tag name value pair {}".format(args.tag_namevalue))

    make_snapshots(ec2_conn, args.period, namevalue, args.share_account)


if __name__ == "__main__":
    main()
