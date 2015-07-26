#!/usr/bin/env python

"""
A script for creating (or updating) a (read-only) public S3 bucket with a
retention policy of 30 days (unless otherwise configured) and a CORS policy
which allows HTTP GETs from any domain.

Before running this script you'll want to log into the AWS console and create a
new user and group in IAM, eg. XmppHttpUpload. The user should belong to the
group, and the group should have the `AmazonS3FullAccess` policy set (or a more
restrictive policy that only allows reads/writes from buckets created by it).
You'll then want to create an access key for the user, and add it (and its
secret) to the config file.

Alternatively, instead of specifying a config file, you may use the following
environment variables:

  - AWS_ACCESS_KEY_ID — Your AWS Access Key ID
  - AWS_SECRET_ACCESS_KEY — Your AWS Secret Access Key

The config file is looked for at `../config.yml` by default. To change this,
call the script with the --config argument set to a YAML file.
"""

import argparse
import yaml

from boto.s3.connection import Location
from boto.s3.connection import S3Connection
from boto.s3.cors import CORSConfiguration
from boto.s3.lifecycle import Lifecycle

def main(config):
    """
    Create an S3 bucket (or updates an exisitng one) which has reasonable
    defaults for use with the HTTP Upload component. The following config
    values will be used from the given config dict:

        - aws_access_key_id — Your AWS Access Key ID (must have S3 perms)
        - aws_secret_access_key — Your AWS Secret Access Key.
        - aws_s3_bucket — Your S3 bucket name. If it does not already exist, it
          will be created for you. It may include the special format strings
          `{aws_access_key_id}` and `{aws_s3_location}` which will be replaced
          with their similarly named config values.
        - aws_s3_location — The region (eg. us-east-1) where you want your
          bucket to live.
        - aws_s3_retenton_days — 0 for infinite retention, or the number of
          days which files must be retained. Defaults to 30.

    Args:
        config (dict): The config values.
    """
    try:
        s3_conn = S3Connection(
            config['aws_access_key_id'],
            config['aws_secret_access_key']
        )
    except NameError:
        s3_conn = S3Connection()

    s3_bucket = conn.create_bucket(
        config['aws_s3_bucket'].format(
            aws_access_key_id=config['aws_access_key_id']
            aws_s3_location=config['aws_s3_location']
        ).lower(),
        location=config['aws_s3_location']
    )
    s3_bucket.set_acl('public-read')

    cors_cfg = CORSConfiguration()
    cors_cfg.add_rule('GET', '*')
    s3_bucket.set_cors(cors_cfg)

    if config['aws_s3_retenton_days'] > 0:
        lifecycle = Lifecycle()
        lifecycle.add_rule(
            'retention',
            status='Enabled',
            expiration=Expiration(
                days=config['aws_s3_retention_days']
            )
        )

if __name__ == '__main__':
    config = {
        'aws_s3_bucket': 'xmpp-http-upload-{aws_access_key_id}',
        'aws_s3_location': ''
        'aws_s3_retention_days': 30
    }
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config",
        default='../config.yml',
        help='Specify alternate config file.'
    )
    args = parser.parse_args()

    with open(args.config, 'r') as ymlfile:
        config.update(yaml.load(ymlfile))

    main(config)
