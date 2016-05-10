# AWS provision new account



# Description

This procedure allows one to configure a new account that will be used to run an Interana cluster in AWS.

Our solution creates a completely firewalled account using VPC and allow you to attach it to your Master AWS account to take advantages of AWS Consolidated Billing

It is extremely important that you only use the credentials with the new account in running scripts.  DO NOT PASTE IN YOUR MASTER ACCOUNT access keys.

If encountering problems, refer to HELP.md


# Steps

Master Account - Your original AWS account that is used for billing

Interana Account - The newly provision account that is used to run interana cluster.

1) Git Clone the provision_tools repo, to a machine that has python installed (mac, linux, windows)
```
git clone 
cd provision_tools/
```

2) Using a new email address, sign-up for a new Amazon Account at https://aws.amazon.com/.  You will need a new email address and credit card other then your current address.
Please safe keep your root email and password for initial login for the Interana Account you've just created

3) Open - https://console.aws.amazon.com/billing/home#/account and note your Account ID.

4) Login into the account and navigate to the IAM Service.  Click on Users and create a new user with permissions as follows.

Say Yes when prompted "Generate and Access key For Each User" checked.
```
User : interana_admin
```
In the next screen DOWNLOAD the Secret and Access key to your repository

5) Click on the User you just created.  Scroll down to the Permissions Section.  Click on the interana_admin user you've created.  Attach Policy and pick the following role(s):
```
Role : AdministratorAccess
```

Copy the Secret and Access key to a ~/.aws/credentials 

```
[default]
aws_access_key_id = XXXXXXXXX
aws_secret_access_key = YYYYYYYYYYYYYYYYYYYYYYYY
```

Alernatively they can be used in command line directgly

6) Install the python requirements for this project (perferably using virtualenv or run with root privs)
```
pip install -r requirements.txt 
```

7) Run the provision.py script as follows to generate a bucket policy to share the S3 bucket from your interana account id.
For the s3_bucket path, you may specify just the bucket name (preferred) or a path if fine grain controls are prefered

Example ~/.aws/credentials
```
python ./provision.py --s3_bucket 'my-bucket/my_path/' -r us-east-1   --interana_account_id 999999999999 --action create -c mycustomer
```

or if using the command line option

```
python ./provision.py --s3_bucket 'my-bucket/my_path/' -r us-east-1  --interana_account_id 999999999999 --action create -c mycustomer -w <aws_access_key> -x <aws_secret_key>
```


8) In the folder, you will see a s3_bucket_list.policy.  Copy it contents and add it to your master accounts
s3_bucket using the AWS Console:
```
https://console.aws.amazon.com/s3
```

Click on the bucket to be shared.

Open the properties and and click on "permissions"

Click Edit the Bucket Policy...

You can paste in the policy if there is no policy listed.   If there is policies listed, then add the policy in the "Statements" array to the existing one
i.e.
```
Statement : [
{ original policy....},
{ s3_share policy....}
]
```

9) Re run the ./provision.py with to check all permissions are correctly stated.  You will need your account id from the My Account tab.
You must also have at least one file newly uploaded file (> 7 days)
in the s3 bucket under the path below so read access can be confirmed.

Example ~/.aws/credentials
```
python ./provision.py --s3_bucket 'my-bucket/my_path/' -r us-east-1 --interana_account_id 999999999999 --action check -c mycustomer
```

or if using the command line option

```
python ./provision.py --s3_bucket 'my-bucket/my_path/' -r us-east-1 --interana_account_id 999999999999 --action check -c mycustomer -w <aws_access_key> -x <aws_secret_key>
```

If the check is successfull, there will be a interana_cluster.json generated

10) Review the interana_cluster.json for sensitive information and please email it to 
```
help@interana.com
```

11)  You will shortly see new instances created by our provisioner in the "Instances" page.


12) Once the interana cluster is created setup consolidated billing
Login to your Master Account and go to following
```
https://console.aws.amazon.com/billing/home?region#/consolidatedbilling
```

Send a request with the email address you created in step 1.

You will need to logon to the Interana Account to accept.







