# Test Plan

To test this script you need the following test fixtures

1) An S3 bucket in a master account and UI access to change the "properies/permission" Edit Bucket Policy
With following setup

```
/ - root folder with some random files
datasets/ - an empty folder
datasets/2014 - random files
datasets/2013-glacier - files archived by glacier
```


2) A secondary account with a user called interana_admin and its associated accees key and secret keys


Interana Internally we use the following
```
<account_id> = 065366222751
<bucket_name> = provision-test
```


# Test Cases


## Ensure no bucket policy is applied and run the following
```
python provision.py -i <account_id> -s <bucket_name> -c acme -r us-east-1 -a check  -w wwwww -x xxxxx
```

Expected result:
```
Exception: Failed to verify access on bucket provision-test path .
```

## Create a root policy and edit bucket policy and replace
```
python provision.py -i <account_id> -s provision-test -c acme -r us-east-1 -a create -w wwwww -x xxxxx
python provision.py -i <account_id> -s provision-test -c acme -r us-east-1 -a check -w wwwww -x xxxxx
```

Expected result:
```
verified read only access to path .
```

## Create a folder policy and edit bucket policy and replace
```
python provision.py -i <account_id> -s <bucket_name>/datasets/2014 -c acme -r us-east-1 -a create -w wwwww -x xxxxx
python provision.py -i <account_id> -s <bucket_name>/datasets/2014 -c acme -r us-east-1 -a check -w wwwww -x xxxxx
```

Expected result:
```
verified read only access to path datasets/
```


## Attempting reading from a folder that doesn't match ACL
```
python provision.py -i <account_id> -s <bucket_name>/datasets/2014 -c acme -r us-east-1 -a create -w wwwww -x xxxxx
python provision.py -i <account_id> -s <bucket_name>/ -c acme -r us-east-1 -a check -w wwwww -x xxxxx
```

Expected Resuts
```
<class 'boto.exception.S3ResponseError'>:S3ResponseError: 403 Forbidden
<?xml version="1.0" encoding="UTF-8"?>
<Error><Code>AccessDenied</Code><Message>Access Denied</Message>
```


## Attempting reading from a folder that has glacier files
```
python provision.py -i <account_id> -s <bucket_name>/datasets/2013-glacier/ -c acme -r us-east-1 -a create -w wwwww -x xxxxx
python provision.py -i <account_id> -s <bucket_name>/datasets/2013-glacier/ -c acme -r us-east-1 -a check -w wwwww -x xxxxx
```

Expected Resuts
```
No files could be downloaded, moving to next folder. S3ResponseError: 403 Forbidden
<Error><Code>InvalidObjectState</Code><Message>The operation is not valid for the object's storage class</Message>
```

# Additional Tests 


## interana-logs bucket (check only)
```
./provision.py -i 681624442818 -s interana-logs -c acme -a check -r us-east-1 -w www -x xxx -u interana_admin
```

Expected Resuts
```
TBD
```


## interana-logs-us-west-2
```
./provision.py -i 681624442818 -s interana-logs-us-west-2/ -c acme -a check -r us-west-2 -w www -x xxx -u interana_logs_readonly
./provision.py -i 681624442818 -s interana-logs-us-west-2/ -c acme -a check -r us-west-2 -w www -x xxx -u interana_logs_readonly
```

Expected Resuts
```
TBD
```