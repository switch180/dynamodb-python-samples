This python script writes items to a DynamoDB table in compressed and non-compressed forms. Once items are written, you can review the hourly CUR data with Athena to see what the TimeStorageByte-Hrs cost is for the storage. The metered usage in this line item is different from the size shown in the DescribeTable output.

This script was written to help estimate the cost for a DynamoDB table with billions of items. In this case, every byte counts. We initially used the [Zac Charles item size calculator](https://zaccharles.github.io/dynamodb-calculator/) and then moved on to the billing data soon thereafter. What we noticed is that it's difficult to estimate the GSI/LSI item size, and even if we knew the item structure in the indexes there is a "100 byte" overhead in the DynamoDB pricing page that suggests the estimated item size in the DescribeTable output isn't the actual metered usage. In our comparison of the outputs, we found the actual metered usage was sometimes greater and sometimes less than the zaccharles tool.

For this reason, the python script runner.py exists: When your multiplier is a in the billions, every byte counts. We need to get the storage bytes correct. As a result, it stores items in either GZIP or plain text format. In limited testing we saw storage savings of 21% with GZIP for a table with one LSI and one GSI.


#### Use

Inside the class DynamoDBItem, set your partition key name and include a list of keys that you want in the top level (copied put into the GZIP attribute). Modify these values to match your schema; they are used to pick attributes out when you store the item with GZIP.

Then, get your DynamoDB item in JSON format (NOT DynamoDB JSON) and put it in the directory of the runner script and name the file `item.json`. The python script will load the item and write it into DynamoDB, changing the partition key value by incrementing it just before writing.

Then, use the AWS CLI command at the top to make a DynamoDB table, or update the table name to match your own.

Then, run the script! It will store an arbitrary number of items in DynamoDB for you.

Finally, check the CUR data with Athena to see the actual storage cost:

```sql
select
identity_time_interval,
line_item_resource_id,
line_item_usage_type,
line_item_usage_amount,
line_item_unblended_cost,
line_item_blended_rate,
line_item_line_item_description
from basic2021
WHERE line_item_resource_id LIKE 'arn:aws:dynamodb:us-east-1:%:table/%-v%'
AND line_item_usage_type = 'TimedStorage-ByteHrs' and line_item_operation='StandardStorage'
ORDER BY line_item_resource_id, identity_time_interval ASC;
```

In the data, find the column `line_item_usage_amount` and multiply that by the number of hours in that month (i.e. 730 or 744) to get the metered size of the table in GB.


#### Limitations

- The script supports hash-only tables. This limit exists because the script creates an auto-incrementing partition key value starting with 0, counting up.
- Only one item format is expected: whatever is in `item.json`. All items are virtually identical; the only change is the partition key value
