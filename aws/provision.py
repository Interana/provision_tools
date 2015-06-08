import argparse
import json
import os
import re
import sys

from boto import ec2, iam, s3
from boto.exception import S3ResponseError
from boto.s3.key import Key

from awsconfig import awsconfig


aws_access_key = awsconfig['aws_access_key']
aws_secret_key = awsconfig['aws_secret_key']
aws_region_name = awsconfig['aws_region_name']


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
        raise Exception("Could not connection to region {}, invalid credentials.  See awsconfig.py".format(region_name))

    return conn


def get_iam_connection(aws_access_key_id, aws_secret_access_key, region_name):
    conn = iam.connect_to_region(aws_access_key_id=aws_access_key_id,
                                 aws_secret_access_key=aws_secret_access_key,
                                 region_name=region_name)
    if conn is None:
        raise Exception("Could not connection to region {}, invalid credentials.  See awsconfig.py".format(region_name))

    return conn


def get_s3_connection(aws_access_key_id, aws_secret_access_key, region_name):
    conn = s3.connect_to_region(aws_access_key_id=aws_access_key_id,
                                aws_secret_access_key=aws_secret_access_key,
                                region_name=region_name)
    if conn is None:
        raise Exception("Could not connection to region {}, invalid credentials.  See awsconfig.py".format(region_name))

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


def provision_create(ec2_conn, iam_conn, interana_account_id, s3_bucket):
    """

    Make the s3 bucket policy and let user configure with it
    """
    check_account_setup(iam_conn)

    infile = 's3_bucket_list.policy.template'
    outfile = 's3_bucket_list.policy'

    all_lines = ''
    with open(infile, 'r') as tmp_fh, open(outfile, 'w') as out_fh:
        for line in tmp_fh:
            re_proxy = re.compile('<INTERANA_ACCOUNT_ID>')
            translate = re_proxy.sub(interana_account_id, line)

            re_proxy = re.compile('<BUCKET_PATH>')
            translate = re_proxy.sub(s3_bucket, translate)
            out_fh.write(translate)
            all_lines += translate.strip()

    print "****policy file***"

    print json.dumps(json.loads(all_lines), indent=True)


def provision_check(ec2_conn, iam_conn, s3_conn, interana_account_id, s3_bucket):
    """
    Check the s3 bucket share has list properties, but not write
    Use "dummy_<date>.txt at root of bucket
    Create interana_cluster.json and allow user to send that off.
    """
    check_account_setup(iam_conn)

    print "Checking Bucket for read only access."

    bucket_path = s3_bucket.split('/')
    bucket_name = bucket_path[0]
    bucket_prefix = ""
    if len(bucket_path) > 1:
        bucket_prefix = '/'.join(bucket_path[1:])
        bucket_prefix = bucket_prefix.replace('*', '')
    try:
        bucket = s3_conn.get_bucket(bucket_name)
        delim = "/"
        result_iter = list(bucket.list(bucket_prefix, delim))
        prefixes = [prefix.name for prefix in result_iter]
        if len(prefixes) < 1:
            raise Exception("Did not find any folders or files under {} and {}".format(bucket_prefix, delim))
    except S3ResponseError, e:
        raise Exception("Failed to verify access on bucket {} path {}.\n"
                        "Additional info : {}".format(bucket_prefix, bucket_prefix, e))

    def percent_cb(complete, total):
        sys.stdout.write('.')
        sys.stdout.flush()

    testfile = 'dummy.txt'

    try:
        k = Key(bucket)
        k.key = os.path.join(bucket_prefix, testfile)
        k.set_contents_from_filename(testfile, cb=percent_cb, num_cb=10)
    except S3ResponseError, e:
        print "Successfully verified read only access"
    else:
        print "FAILED: Was able to write to path {} file {}".format(k.key, testfile)


def main():
    """
    """
    parser = argparse.ArgumentParser(
        description="Provision account for Interana Cluster",
        epilog="""
Assumes requirements.txt has been installed
""")

    parser.add_argument('-m', '--interana_account_id', help='The master aws account id, without dashes', required=True)
    parser.add_argument('-s', '--s3_bucket', help='The s3_bucket specified, i.e. my-bucket/my_path/*', required='True')
    parser.add_argument('-a', '--action', help='Create or Check a configuration', choices=['create', 'check'],
                        required=True)

    args = parser.parse_args()

    ec2_conn = get_ec2_connection(aws_access_key, aws_secret_key, aws_region_name)
    iam_conn = get_iam_connection(aws_access_key, aws_secret_key, aws_region_name)
    s3_conn = get_s3_connection(aws_access_key, aws_secret_key, aws_region_name)

    if args.action == "create":
        provision_create(ec2_conn, iam_conn, args.interana_account_id, args.s3_bucket)
    elif args.action == "check":
        provision_check(ec2_conn, iam_conn, s3_conn, args.interana_account_id, args.s3_bucket)


if __name__ == "__main__":
    main()
