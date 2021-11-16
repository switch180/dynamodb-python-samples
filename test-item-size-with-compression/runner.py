#import things
import boto3
import os
import json
import zlib
import argparse
import logging
import decimal
from boto3.dynamodb.types import TypeSerializer
from base64 import b64encode



#aws dynamodb create-table --attribute-definitions AttributeName="_id",AttributeType=S --table-name plain-v1 --key-schema AttributeName="_id",KeyType=HASH --billing-mode PAY_PER_REQUEST
compression_choices = ['gzip']
input_file = 'item.json' #Should be a JSON document, with one element with PK named '_id' of type String, where we will swap in the partition key value
logging.getLogger().setLevel(10)
logger = logging.getLogger('item-size')
log = logging.StreamHandler()
logger.addHandler(log)

#Print it all
logging.getLogger('urllib3').setLevel(logging.DEBUG)
logging.getLogger('boto3').setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.DEBUG)
loggers_dict = logging.Logger.manager.loggerDict
#print(loggers_dict)
def main():
    pass
    #Collect args
    mainargs = argparse.ArgumentParser(description='Watch as we measure WCUs, table size, and metered storage')
    mainargs.add_argument('--table-name', help='Provide a tablename, if we\'re writing items in this run.')
    mainargs.add_argument('--dry-run', help='we should not actually write items to DynamoDB, just print and end', action='store_true')
    mainargs.add_argument('--item-count', help='This influences the number of items we write to the table.', type=int, default=1)
    mainargs.add_argument('--compression-type', help="Choose the compression type (optional)", choices=compression_choices)
    args = mainargs.parse_args()
    dry_run = args.dry_run
    if getattr(args, 'compression_type'):
        compression_type = args.compression_type
    #load item
    item = load_item(input_file, args.item_count)
    if args.compression_type:
        if args.compression_type == compression_choices[0]: #gzip
            #print in compression type(s)
            logger.info("Printing the item in GZIP'd DynamoDB JSON format")
            item.set_mode(compression_choices[0])
            logger.info(json.dumps(item._wire(item.get_item()), default=default_type_error_handler))
    if getattr(args, 'table_name') and getattr(args, "item_count"):
        logger.debug("Following the write path.")
        table_name = args.table_name
        item_count = args.item_count
        client = boto3.resource('dynamodb')
        table = client.Table(table_name)
        if not dry_run:
            with table.batch_writer() as batch:
                for batch_item in item:
                    batch.put_item(Item=batch_item)
    elif getattr(args, 'table_name') or getattr(args, "item_count"):
        logger.error("We need a table name with item count.")
        raise Exception("If table name is provided, item count must also be given.")


def load_item(item_path, item_count):
    logger.debug("Reading file {}".format(item_path))
    with open(item_path, 'r') as datafile:
        return DynamoDBItem(datafile.read(), item_count)
class DynamoDBItem(object):
    partition_key_name = '_id' # CHANGE ME this is your partition key
    key_attributes = [partition_key_name, 'SK'] # CHANGE ME with your top level keys for indexing
    ser = TypeSerializer()
    def __init__(self, item_json, item_count):
        self.item_json = item_json
        self.item_dict = json.loads(self.item_json, parse_float=float_to_decimal)
        self.item_count = item_count
        self._index = 0
        self.set_mode('plain')
    def __str__(self):
        return "Item: PK is {}".format(self.item_dict[self.partition_key_name])
    def wire(self):
        return self.item_dict.copy()
    def _wire(self, item_dict):
        ddb_obj = {}
        for k,v in item_dict.items():
            ddb_obj[k] = self.ser.serialize(v)
        return ddb_obj
    def set_mode(self, mode):
        if mode == 'plain':
            self.get_item = self.wire
        elif mode == compression_choices[0]:
            self.get_item = self._gzip
    def _gzip(self):
        #get a no keys obj
        no_keys = self._no_keys()
        compression_name = 'b64-zip-v1'
        #GZIP it
        in_json = json.dumps(no_keys, default=default_type_error_handler)
        in_bytes = in_json.encode('utf-8')
        in_b64 = b64encode(zlib.compress(in_bytes))
        #Add keys back
        returnee =  dict()
        returnee[compression_name] = in_b64
        for key_name in self.key_attributes:
            returnee[key_name] = self.item_dict[key_name]
        return returnee

    def _no_keys(self):
        item_map = self.item_dict.copy()
        try:
            for key_name in self.key_attributes:
                del item_map[key_name]
        except KeyError as err:
            logger.error(err)
            logger.error("If you provide a key attribute, it should be in the item you give :-(")
            raise err
        return item_map
    def __next__(self):
        if self._index < self.item_count:
            item = self.get_item()
            item[self.partition_key_name] = str(self._index).zfill(7)
            self._index = self._index + 1
            return item
        else:
            raise StopIteration
    def __iter__(self):
        return self

# float_to_decimal: The DDB Type Serializer expects Decimals, not floats
# https://github.com/boto/boto3/issues/665
def float_to_decimal(fl):
    return decimal.Decimal(str(fl))


def default_type_error_handler(obj):
    # Cast Decimal to int, creating a precision problem we need to fix before production use
    if isinstance(obj, decimal.Decimal):
        return int(obj)
    # Fix a JSON decode error with the bytes/binary datatype
    elif isinstance(obj, bytes):
        return obj.decode('ascii')
    raise TypeError
if __name__ == '__main__':
    main()
