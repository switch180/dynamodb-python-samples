#### About
This is a proof of concept script that uses AES-SIV to encrypt a DynamoDB partition key. AES-SIV is an authenticated encryption algorithm with a synthetic IV. The ciphertext is deterministic, and the same nonce can be reused safely. With AES-SIV with a static nonce, when the same plaintext is passed to AES-SIV then the output will be the same. This desirable behavior allows us to read and write DDB rows using the ciphertext as the partition key, unlike other encryption algorithms that have ciphertexts that change with each run. [Read more about the algorithm](https://connect2id.com/blog/deterministic-encryption-with-aes-siv)

The script:
- Creates a DDB table for the items
- Allocates a KMS DEK for the AES-SIV algorithm. It's stored in the DDB table in its own row. All rows in the table use the same DEK for the partition key in this sample code
- Writes and then reads rows in the DDB table, proving the partition key ciphertext is the same by encrypting and then decrypting the partition key several times.

#### How to run

Simply install the modules in the requirements file and then run the python script. It can be run idempotently. It will create a table, create and store the DEK, and read/write the rows in order. If the table exists it continues, and if the DEK is already stored in the DDB table then it will read it and use it for operations. It's coded to operate in us-east-1, but that's changeable.

Sample output:
```text
% python3 kms_partition_key_encryption.py  
Making the DDB table in case it doesn't exist.
An error occurred (ResourceInUseException) when calling the CreateTable operation: Table already exists: aes-siv-ddb-kms-test
Wrote item with encrypted PK b'<redacted>', with plaintext 123-123-1234
Wrote item with encrypted PK b'<redacted>', with plaintext 456-456-4567
Read item with plaintext PK 123-123-1234, with decrypted plaintext PK 123-123-1234. Both should match.
Read item with plaintext PK 456-456-4567, with decrypted plaintext PK 456-456-4567. Both should match.
```

#### Why this matters
If you use KMS En/Decrypt APIs, the ciphertext will change with each each operation. If you encrypt the string "1234", the ciphertext will change each time because the IV changes with each API call. This means the KMS encrypt/decrypt APIs can't be used to encrypt a DynamoDB partition key. AES-SIV is a standards-based way to have a synthetic IV, yielding the same ciphertext for a given plaintext.

Benefits over other approaches:
- Unlike a hash, AES-SIV is encrypted with AES using a data encryption key. You can't use a rainbow table to decrypt AES.
- Unlike normal AES implementations, the IV is the same each time for a given plaintext which *I think* is the reason the ciphertext is the same.
- Unlike a roll-your-own encryption approach, AES-SIV is documented and researched.

This means that I can use something I know, which is a data encryption key, to encrypt a partition key that I can use to read and write a row while protecting the plaintext of the partition key.


TL;DR: You can encrypt and your sensitive DynamoDB partition key with AES! You can work around the limitation of the [DynamoDB Encryption Client for Python](https://docs.aws.amazon.com/dynamodb-encryption-client/latest/devguide/python.html), which doesn't let you encrypt the partition key.

#### Resources
- [Inspired by this stackexchange post titled "Deterministic Encryption using AES"](https://crypto.stackexchange.com/questions/68032/deterministic-encryption-using-aes)
- [Miscreant AES-SIV library documentation](https://github.com/miscreant/miscreant.py#api).
- [AES-
RFC 5297](https://tools.ietf.org/html/rfc5297)
