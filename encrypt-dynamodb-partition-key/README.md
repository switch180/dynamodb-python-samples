This is a proof of concept script that uses AES-CIV to encrypt a DynamoDB partition key. AES-CIV is an authenticated encryption algorithm with a synthetic IV. The ciphertext is deterministic, and the same nonce can be reused safely. With AES-SIV with a static nonce, the same plaintext is passed to AES-SIV the output will be the same, which is a desirable behavior. [Read more about the algorithm](https://connect2id.com/blog/deterministic-encryption-with-aes-siv)

The script:
- Creates a DDB table for the items
- Allocates a KMS DEK for the AES-SIV algorithm. It's stored in the DDB table in its own row. All rows in the table use the same DEK for the partition key in this sample code
- Writes and then reads rows in the DDB table, proving the partition key ciphertext is the same by encrypting and then decrypting the partition key several times.

Sample output:
```text
% python3 kms_partition_key_encryption.py  
Making the DDB table in case it doesn't exist.
An error occurred (ResourceInUseException) when calling the CreateTable operation: Table already exists: aes-civ-ddb-kms-test
Wrote item with encrypted PK b'<redacted>', with plaintext 123-123-1234
Wrote item with encrypted PK b'<redacted>', with plaintext 456-456-4567
Read item with plaintext PK 123-123-1234, with decrypted plaintext PK 123-123-1234. Both should match.
Read item with plaintext PK 456-456-4567, with decrypted plaintext PK 456-456-4567. Both should match.
```

TL;DR: You can encrypt and your sensitive DynamoDB partition key with AES! You can work around the limitation of the [DynamoDB Encryption Client for Python](https://docs.aws.amazon.com/dynamodb-encryption-client/latest/devguide/python.html), which doesn't let you encrypt the partition key.

#### Resources
- [Inspired by this stackexchange post titled "Deterministic Encryption using AES"](https://crypto.stackexchange.com/questions/68032/deterministic-encryption-using-aes)
- [Miscreant AES-SIV library documentation](https://github.com/miscreant/miscreant.py#api).
- [AES-CIV RFC 5297](https://tools.ietf.org/html/rfc5297)
