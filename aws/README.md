# AWS provision new account



# Description

This procedure allows one to configure a new account that will be used to run interana_cluster in AWS.

Our solution creates a completely firewalled account using VPC and allow you to attach it to your Master AWS account to take advantages of AWS Consolidated Billing

It is extremely important that you only use the credentials with the new account in running scripts.  DO NOT PASTE IN YOUR MASTER ACCOUNT access keys.



# Steps

Master Account - Your original AWS account that is used for billing
Interana Account - The newly provision account that is used to run interana cluster.

TBD : interana-cluster-key!!

1) Git Clone the provision_tools repo, to a machine that has python installed (mac, linux, windows)
```
git clone 
cd provision_tools/
```

2) Using a new email address, sign-up for a new Amazon Account at https://aws.amazon.com/.  You will need a new email address and credit card other then your current address
Please safe keep your root email and password for initial login for the Interana Account you've just created


3) Login into the account and navigate to the IAM Service.  Create a new user with permissions as follows.
Say Yes when prompted "Generate and Access key For Each User" checked.
```
User : interana_admin
```
In the next screen DOWNLOAD the Secret and Access key to your repository

4) Got the roles tab in IAM Service.  Click on the interana_admin user you've created.  Attach Policy and pick the following role(s):
```
Role : AdministratorAccess
```
Now when prompted to download the security credentials, copy them to a awsconfig.py file in this folder like this

```
cp awsconfig.py.template awsconfig.py
vim awsconfig.py

Update the access_key, secret_key
for region, fill out your desired region ex. us-east-1
See this page for choices for region:
http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html#concepts-regions
```



5) the access keys and update the awsconfig.py.template file in this folder


6) Install the python requirements for this project
```
mkvirtualenv provision_tools
workon provision_tools
pip install -r requirements.txt 
```

7) Run the provision.py script as follows to generate a bucket policy to share the S3 bucket from your master account id
i.e.
```
python ./provision.py --s3_bucket 'my-bucket/my_path/*'  --interana_account_id 999999999999 --create
```

8) In the folder, you will see a s3_bucket_list.policy.  Copy it contents and add it to your master accounts
s3_bucket using the AWS Console:
```
https://console.aws.amazon.com/s3
```

Click on the bucket to be shared
Open the properties and and click on "permissions"
Edit the Bucket Policy

You can paste in the policy if there is no policy listed.   If there is policies listed, then add the policy in the "Statements" array to the existing one
i.e.
```
Statement : [
{ original policy....},
{ s3_share policy....}
]
```

9) Re run the ./provision.py with to check all permissions are correctly stated
```
python ./provision.py --s3_bucket 'my-bucket/my_path/*'  --interana_account_id 999999999999 --check
```
If the check is successfull, there will be a interana_cluster.json generated

10) Review the interana_cluster.json for sensitive information and please email it to 
```
help@interana.com
```

11) After a while, your provision account will be ready to go.  
You will see new instances created by our provisioner in the "Instances" page.


12) Once the interana cluster is created setup consolidated billing
Login to your Master Account and go to following
```
https://console.aws.amazon.com/billing/home?region#/consolidatedbilling
```

Send a request with the interana account_id as found in the interana_cluster.json

You will need to logon to the Interana Account to accept.







