import re
import sys

import yaml
import click
import boto3
import botocore
from crontab import CronTab

s3_client = None
bucket = None
pub_keys = {}

@click.group()
def main():
    pass

def get_pub_key(pub_key_name):
    global pub_keys

    if pub_key_name in pub_keys:
        return pub_keys[pub_key_name]

    try:
        response = s3_client.get_object(
            Bucket=bucket,
            Key=pub_key_name)
    except botocore.exceptions.ClientError as e:
        print(e.response)
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise Exception('Pub key `{}` not found'.format(pub_key_name))
        else:
            raise e

    pub_key = response['Body'].read().decode('utf-8')

    pub_keys[pub_key_name] = pub_key

    return pub_key

pub_key_regex = r'ssh-rsa\s.+\s(.+)$'

@main.command(help='Sync authorized_keys from S3')
@click.argument('configuration_name')
@click.option('-c','--config-filename', default='auth_keys.yml', help='YAML config file path')
@click.option('-o','--output-filename',
              default='/home/{user}/.ssh/authorized_keys',
              help='Output file path. Optional {user} variable in path')
def sync(configuration_name, config_filename, output_filename):
    global s3_client, bucket

    s3_client = boto3.client('s3')

    with open(config_filename) as file:
        config_file = yaml.load(file)

    bucket = config_file['bucket']
    config = config_file['configurations'][configuration_name]
        
    for user in config:
        user_pub_keys = config[user]
        with open(output_filename.format(user=user), 'r+') as file:
            out_lines = []
            keys_added = []

            for line in file:
                out_line = line

                if out_line.strip() == '':
                    continue

                match = re.match(pub_key_regex, line)
                if match != None:
                    key_name = match.groups()[0]

                    if key_name in user_pub_keys:
                        keys_added.append(key_name)
                        out_line = get_pub_key(key_name)

                out_lines.append(out_line)

            for key_name in user_pub_keys:
                if key_name not in keys_added:
                    out_lines.append(get_pub_key(key_name))

            for i in range(0, len(out_lines)):
                out_lines[i] = out_lines[i].replace('\n','')

            file.seek(0)
            file.truncate()
            file.write('\n'.join(out_lines))

@main.command(help='Installs script as cron job')
@click.argument('configuration_name')
@click.option('-c','--config-filename', default='auth_keys.yml', help='YAML config file path')
@click.option('-o','--output-filename',
              default='/home/{user}/.ssh/authorized_keys',
              help='Output file path. Optional {user} variable in path')
@click.option('--cron-schedule', default='*/15 * * * *', help='Cron schedule')
def install_cron(configuration_name, config_filename, output_filename, cron_schedule):
    job_id = 'keytothecity'

    cron = CronTab(user=True)

    jobs = cron.find_comment(job_id)
    if len(list(jobs)) > 0:
        click.echo('keytothecity already installed')
        sys.exit(0)

    command = 'keytothecity sync {} -c {} -o {}'.format(configuration_name, config_filename, output_filename)

    job = cron.new(command=command, comment=job_id)
    job.setall(cron_schedule)
    cron.write()
