#!/usr/bin/env python

import argparse
from calendar import timegm
from datetime import datetime
import json
import os
import re
import sys
import traceback

from boto import ec2, iam, s3
from boto.exception import S3ResponseError
from boto.s3.key import Key
from boto.s3.prefix import Prefix


def utctimestamp():
    return timegm(datetime.utcnow().timetuple())


def print_list(llist):
    return '[%s]' % '\n'.join(map(str, llist))


def print_exception(e):
    (typeE, value, tracebackPrev) = sys.exc_info()
    print(str(typeE) + ':' + str(value))
    print(" PREV=\n" + print_list(traceback.extract_tb(tracebackPrev)))


def get_ec2_connection(aws_access_key_id, aws_secret_access_key, region_name):
    """
    :param aws_access_key: if None, we will use the .aws/config on this system
    :param aws_secret_key: if None we wil use the .aws/config on this system
    :param region_name: This is a region string i.e. us-east-1
    :return: an ec2 connection object
    :rtype: EC2Connection
    """
    conn = ec2.connect_to_region(aws_access_key_id=aws_access_key_id,
                                 aws_secret_access_key=aws_secret_access_key,
                                 region_name=region_name)
    if conn is None:
        raise Exception("Could not get ec2 connection to region {}, invalid credentials.".format(region_name))

    return conn


def get_iam_connection(aws_access_key_id, aws_secret_access_key, region_name):
    conn = iam.connect_to_region(aws_access_key_id=aws_access_key_id,
                                 aws_secret_access_key=aws_secret_access_key,
                                 region_name=region_name)
    if conn is None:
        raise Exception("Could not get iam connection to region {}, invalid credentials.".format(region_name))

    return conn


def get_s3_connection(aws_access_key_id, aws_secret_access_key, region_name):
    conn = s3.connect_to_region(aws_access_key_id=aws_access_key_id,
                                aws_secret_access_key=aws_secret_access_key,
                                region_name=region_name)
    if conn is None:
        raise Exception("Could not get s3 connection to region {}, invalid credentials.".format(region_name))

    return conn


def check_account_setup(iam_conn):
    """
    Check the credentials, such that the admin access is setup and the user is interana_admin
    """
    print "Checking Account Setup for interana_admin and policies."

    user = iam_conn.get_user('interana_admin')

    if 'user_name' not in user['get_user_response']['get_user_result']['user']:
        raise Exception("User interana_admin was not found. Additional Info {}".format(user))

    all_policies = iam_conn.get_all_user_policies('interana_admin')
    if 'policy_names' not in all_policies['list_user_policies_response']['list_user_policies_result']:
        raise Exception("interana_admin user does not appear to had AdministorAccess policy attached")

    return user, all_policies


def create_cluster_json(ec2_conn, s3_bucket, user, all_policies, validated, clustername):
    interana_cluster = dict()

    interana_cluster['aws_access_key'] = ec2_conn.access_key
    interana_cluster['aws_secret_key'] = ec2_conn.secret_key
    interana_cluster['aws_region_name'] = ec2_conn.region.name
    interana_cluster['s3_bucket'] = s3_bucket
    interana_cluster['user'] = json.loads(json.dumps(user['get_user_response']['get_user_result']))
    interana_cluster['validated'] = validated
    interana_cluster['all_policies'] = json.loads(
        json.dumps(all_policies['list_user_policies_response']['list_user_policies_result']))
    interana_cluster['clustername'] = clustername

    if validated:
        with open('s3_bucket_list.policy') as fh:
            interana_cluster['s3_bucket_policy'] = json.load(fh)

    else:
        interana_cluster['s3_bucket_policy'] = dict()

    print "****interana_cluster.json contents.  Please email to support@interana.com***"
    with open('interana_cluster.json', 'w+') as fp_ic:
        json.dump(interana_cluster, fp_ic, indent=4)

    print json.dumps(interana_cluster, indent=True)


def provision_create(ec2_conn, iam_conn, interana_account_id, s3_bucket_path):
    """
    Make the s3 bucket policy and let user configure with it
    If we specify the root bucket, we have t remove the "Condition" as it does allow
    wildcard at root.
    """
    check_account_setup(iam_conn)

    infile = 's3_bucket_list.policy.template'
    outfile = 's3_bucket_list.policy'

    bucket_name, bucket_prefix = get_bucket_name_prefix(s3_bucket_path)

    all_lines = ''
    with open(infile, 'r') as tmp_fh, open(outfile, 'w') as out_fh:
        for line in tmp_fh:
            re_proxy = re.compile('<INTERANA_ACCOUNT_ID>')
            translate = re_proxy.sub(interana_account_id, line)

            re_proxy = re.compile('<BUCKET_NAME>')
            translate = re_proxy.sub(bucket_name, translate)

            re_proxy = re.compile('<BUCKET_PREFIX>')
            translate = re_proxy.sub(bucket_prefix, translate)

            out_fh.write(translate)
            all_lines += translate.strip()

    if len(bucket_prefix) < 1:
        with open(outfile, 'r') as in_fh:
            policy = json.load(in_fh)
            del policy['Statement'][1]['Condition']
            all_lines = json.dumps(policy)
            print "Download file to check GetObject Access {}".format(outfile)
            with open(outfile, 'w') as out_fh:
                json.dump(policy, out_fh, indent=4)

    print "****policy file {}***".format(outfile)

    print json.dumps(json.loads(all_lines), indent=True)


def get_bucket_name_prefix(s3_bucket_path):
    """
    """
    bucket_path = s3_bucket_path.split('/')
    bucket_name = bucket_path[0]
    bucket_prefix = ""
    if len(bucket_path) > 1:
        bucket_prefix = '/'.join(bucket_path[1:])

    return bucket_name, bucket_prefix


def provision_check(ec2_conn, iam_conn, s3_conn, s3_bucket_path, clustername, force):
    """
    Check the s3 bucket share has list properties, but not write
    Use "dummy_<date>.txt at root of bucket
    Create interana_cluster.json and allow user to send that off.
    @TODO should recursively check up the tree to be more sure.
    """
    user, all_policies = check_account_setup(iam_conn)

    bucket_name, bucket_prefix_orig = get_bucket_name_prefix(s3_bucket_path)

    bucket_prefix = bucket_prefix_orig
    delim = "/"

    if force:
        create_cluster_json(ec2_conn, s3_bucket_path, user, all_policies, False, clustername)

    iter = 0
    while bucket_prefix is not None:

        access = 'read allow' if iter == 0 else 'read deny'
        print "Checking Bucket for {} only access at prefix {}".format(access, "'{}'".format(bucket_prefix))
        try:
            bucket = s3_conn.get_bucket(bucket_name, validate=False)

            regions_allowed = []
            location = bucket.get_location()
            if location == '':
                regions_allowed = ['us-east-1']
            else:
                regions_allowed = [location]

            if ec2_conn.region.name not in regions_allowed:
                raise Exception(
                    "EC2 Region {} not in S3 region(s) {}. Excess charges will occur".format(ec2_conn.region.name,
                                                                                             regions_allowed))

            result_iter = list(bucket.list(bucket_prefix, delim))
            prefixes = [prefix.name for prefix in result_iter]
            if len(prefixes) < 1:
                raise Exception(
                    "Did not find any folders or files in prefix {} using delim {}".format(bucket_prefix, delim))
        except S3ResponseError, e:
            if iter == 0:
                print_exception(e)
                raise Exception("Failed to verify access on bucket {} path {}.\n".format(bucket_name, bucket_prefix))
        else:
            if iter > 0:
                raise Exception(
                    "Unexpected Read Access is granted on path on bucket prefix {}.\n".format(bucket_prefix))

        if len(bucket_prefix) > 0:
            bucket_prefix = '/'.join(bucket_prefix.split('/')[0:-1])
            iter += 1
        else:
            bucket_prefix = None

    # Now attempt to download a  file
    bucket = s3_conn.get_bucket(bucket_name, validate=False)

    file_list = bucket.list(bucket_prefix_orig, '')
    downloaded = 0
    for filel in file_list:
        if isinstance(filel, Prefix):
            continue
        local_name = os.path.basename(filel.key)
        if local_name == '' or local_name == '.':
            continue
        filel.get_contents_to_filename(local_name)
        downloaded += 1
        break

    if downloaded < 1:
        raise Exception("Could not download any files, is this the correct bucket prefix {}".format(bucket_prefix))

    testfile = 'dummy.txt'

    try:
        k = Key(bucket)
        k.key = os.path.join(bucket_prefix_orig, testfile + '.' + str(utctimestamp()))
        k.set_contents_from_filename(testfile)
    except S3ResponseError, e:
        print "Successfully verified read only access"
    else:
        raise Exception("FAILED: Was able to write to path {}".format(k.key))

    create_cluster_json(ec2_conn, s3_bucket_path, user, all_policies, True, clustername)


def main():
    """
    """
    parser = argparse.ArgumentParser(
        description="Provision account for Interana Cluster",
        epilog="""
Assumes requirements.txt has been installed
""")

    parser.add_argument('-i', '--interana_account_id', help='The interana account id, without dashes',
                        required=True)

    parser.add_argument('-s', '--s3_bucket', help='The s3_bucket and path spec. '
                                                  'Dont use wildcards, ex. my-bucket/my_path/',
                        required='True')

    parser.add_argument('-a', '--action', help='Create or Check a configuration', choices=['create', 'check'],
                        required=True)

    parser.add_argument('-w', '--aws_access_key',
                        help='AWS Access key, None if using instance profile',
                        default=None)

    parser.add_argument('-x', '--aws_secret_key',
                        help='AWS Secret key, None if using instance profile',
                        default=None)

    parser.add_argument('-r', '--region',
                        help='region, i.e. us-east-1',
                        required=True)

    parser.add_argument('-c', '--customername',
                        help='The canonical customer name, shortest possible, no trailing integers. eg. acme',
                        required=True)



    parser.add_argument('-f', '--force',
                        help='Forces a generation of interana_cluster.json even if we dont pass validation',
                        default=False, action='store_true')

    args = parser.parse_args()

    ec2_conn = get_ec2_connection(args.aws_access_key, args.aws_secret_key, args.region)
    iam_conn = get_iam_connection(args.aws_access_key, args.aws_secret_key, args.region)
    s3_conn = get_s3_connection(args.aws_access_key, args.aws_secret_key, args.region)

    if args.action == "create":
        provision_create(ec2_conn, iam_conn, args.interana_account_id, args.s3_bucket)
    elif args.action == "check":
        provision_check(ec2_conn, iam_conn, s3_conn, args.s3_bucket, args.customername, args.force)


if __name__ == "__main__":
    main()

""""
TEST PLAN
python provision.py -i <account_id> -s provision-test/datasets/* -c acme -a check
python provision.py -i <account_id> -s provision-test/datasets/* -c acme -a create

python provision.py -i <account_id> -s provision-test -c acme -a check
python provision.py -i <account_id> -s provision-test -c acme -a create
"""""
