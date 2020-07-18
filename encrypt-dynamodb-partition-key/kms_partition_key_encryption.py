import boto3
import botocore
from miscreant.aes.siv import SIV


region_name = 'us-east-1'
test_name = 'aes-civ-ddb-kms-test'
ddb_table_name = test_name
key_alias = 'alias/' + test_name
valid_partition_keys = ['123-123-1234', '456-456-4567']

kms = boto3.client('kms', region_name=region_name)
dynamodb = boto3.client('dynamodb', region_name=region_name)

def main():
    allocate_kms_key()
    allocate_ddb_table()
    #Allocate encryption keys, store encrypted rows
    plaintext_dek = allocate_dek()
    siv = SIV(plaintext_dek)

    for item_key in valid_partition_keys:
        p_key =  encrypt_pk(siv, item_key)
        response = dynamodb.put_item(
            TableName=ddb_table_name,
            Item={
                'PK': {
                    'B': p_key,
                },
                'PK_plain': {
                    "S": str(item_key)
                }
            }
        )
        if response:
            print("Wrote item with encrypted PK '{}', with plaintext {}".format(p_key, str(item_key)))
    #Re-build the SIV module from a fresk DEK to prove the key is deterministic.
    plaintext_dek = allocate_dek()
    siv = SIV(plaintext_dek)
    for item_key in valid_partition_keys:
        p_key =  encrypt_pk(siv, item_key)
        response = dynamodb.get_item(
            TableName=ddb_table_name,
            Key={
                'PK': {
                    'B': p_key,
                }
            }
        )
        if response:
            print("Read item with plaintext PK {}, with decrypted plaintext PK {}. Both should match.".format(response['Item']['PK_plain']['S'], decrypt_pk(siv, response['Item']['PK']['B'])))
def encrypt_pk(siv, pk):
    return siv.seal(bytes(pk, 'utf-8'))
def decrypt_pk(siv, pk):
    return siv.open(pk).decode('utf-8')
def allocate_dek():
    pk_dek = bytes('root', 'utf-8')
    try:
        response = dynamodb.get_item(
            TableName = ddb_table_name,
            Key={
                'PK': {
                    'B':pk_dek
                }
            },
            ConsistentRead=False,
        )
        dek = response['Item']['DEK']['B']
        return decrypt_dek(dek)
    except Exception as err:
        print(err)
        response = kms.generate_data_key(
            KeyId=key_alias,
            EncryptionContext={
                'dynamodb_tablename': ddb_table_name
            },
            KeySpec='AES_256'
        )
        ciphertext = response['CiphertextBlob']
        plaintext = response['Plaintext']
        response = dynamodb.put_item(
            TableName=ddb_table_name,
            Item={
                'PK': {
                    'B': pk_dek,
                },
                'DEK': {
                    "B": ciphertext
                }
            }
        )
        print(response)
        return plaintext
def encrypt_string(plaintext):
    ciphertext = None
    response = kms.encrypt(
        KeyId=key_alias,
        Plaintext=bytes(plaintext, 'utf-8'),
        EncryptionAlgorithm='SYMMETRIC_DEFAULT'
    )
    ciphertext = response['CiphertextBlob']
    return plaintext

def decrypt_dek(ciphertext):
    plaintext = None
    response = kms.decrypt(
        KeyId=key_alias,
        CiphertextBlob=ciphertext,
        EncryptionAlgorithm='SYMMETRIC_DEFAULT',
        EncryptionContext = {
            'dynamodb_tablename': ddb_table_name
        }
    )
    plaintext = response['Plaintext']
    return plaintext
def allocate_ddb_table():
    print("Making the DDB table in case it doesn't exist.")
    try:
        dynamodb.create_table(
            AttributeDefinitions=[
            {
                'AttributeName': 'PK',
                'AttributeType': 'B'
            },
            ],
            TableName=ddb_table_name,
            KeySchema=[
                {
                    'AttributeName': 'PK',
                    'KeyType': 'HASH'
                },
            ],
            BillingMode='PAY_PER_REQUEST',
        )
    except Exception as err:
        print(err)

def allocate_kms_key():
    #This isn't efficent in production, but it allows for simple reproducability in any AWS account
    try:
        response = kms.describe_key(KeyId=key_alias)
        key_id = response['KeyMetadata']['KeyId']
        return key_id
    except Exception as err:
        if err.response['Error']['Code'] == 'NotFoundException':
            response = kms.create_key(
                Description='Created to test KMS encrypt/decrypt for AES-CIV',
                KeyUsage='ENCRYPT_DECRYPT',
                CustomerMasterKeySpec='SYMMETRIC_DEFAULT',
                Origin='AWS_KMS'
            )
            key_id = response['KeyMetadata']['KeyId']
            response = kms.create_alias(
                AliasName=key_alias,
                TargetKeyId=key_id
            )
            return key_id
        else:
            raise err


if __name__ == '__main__':
    main()
