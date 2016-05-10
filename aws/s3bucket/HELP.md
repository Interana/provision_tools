# Common Issues



## A client error (403) occurred when calling the HeadObject operation: Forbidden

This usually means that the policy applied does not match the parameters to the script.
When running the '''-a create''' ensure the policy is applied to the bucket and then 
the '''-a check''' function is run with exact same parameters


##  <class 'boto.exception.S3ResponseError'>:S3ResponseError: 403 Forbidden <Error><Code>AccessDenied</Code><Message>Access Denied</Message>

This usually occurs when the policy is not applied at the folder that is being checked.  IT also could mean no policy has been applied
check the bucket name and path if applicable


## <Error><Code>InvalidObjectState</Code><Message>The operation is not valid for the object's storage class</Message>

This occurs when the object is in glacier.  Ensure some objects exist that are in S3 standard storage type

