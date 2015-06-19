# AWS Snapshot and share tool

# Description

This procedure allows a interana customer to take a snapshot of ebs volumes on entire Interana cluster based on a tag.
and then optionally share them with an account.  

Be very sure of the interana_account_id you want to share with.  After the share is done, you will
need to go to the AWS UI if you want to unshare.

# Steps

Master Account - Your original AWS account that is used for billing. eg 111111111
Interana Account - The newly provision AWS account that is used to run interana cluster. eg 99999999

You should have credentials aws_access_key and aws_secret_key of your master account 
or leave these blank if you are using an instance profile, ~/.aws/configure, or any other pre-authorized method.
Example ~/.aws/credentials
```
[default]
aws_access_key_id = XXXXXXXXX
aws_secret_access_key = YYYYYYYYYYYYYYYYYYYYYYYY
```                                                                        

Note the AWS interana_account_id you want to share snapshots with.  

If you are uncertain please contact interana support for help.
support@interana.com


1) Git Clone the provision_tools repo, to a machine that has python installed (mac, linux, windows)
```
git clone 
cd provision_tools/
```

2) Login into your master account and nagivate to the EC2 services view.


3) Tag all interana instances with common tag, like  "Cluster:Interana".  If you have already a tag that is used
to filter on interana assets, then continue to the next step and note down that tag.


4) Use the Filter to search instances for your tag that you created in step (3). Verify that each instance belongs to 
Interana cluster is choose, and ONLY those instances are present (and not an other instances are present).
Note down the number of instances.


5) Install the python requirements for this project (perferably using virtualenv, must be run with root privs otherwise)
```
pip install -r requirements.txt 
```

6) Using the make_snapshot script in this folder, execute the following to take an adhoc snapshot of all devices associated with your tag.
````
./make_snapshot.py -p adhoc -t Cluster:Interana -r us-east-1
````

or
```
./make_snapshot.py -p adhoc -t Cluster:Interana -r us-east-1 -w <aws_access_key> -x <aws_secret_key>
```


7) Use the EC2 Servcies view, click on the snapshot pane and filter for Cluster:Interana
Ensure that the snapshots match the number of instances in step (4)


8) Run the make_snapshot and share with your "interana_account_id" you've noted down at beginning of procedure.
```
./make_snapshot.py -p adhoc -t Cluster:Interana -r us-east-1 -s 99999999
```

or

```
./make_snapshot.py -p adhoc -t Cluster:Interana -r us-east-1  -w <aws_access_key> -x <aws_secret_key> -s 99999999
```

9) After completing, send an email to interana support with the Tag that you choose, and number of snapshots

```
to: support@interana.com
We've created 15 snapshots with tag "Cluster:Interana" at 11:30 pm and shared with the account id 9999999
```







