import argparse
import subprocess
import os
from pathlib import Path

def run(*args):
        process = subprocess.run(args)
        process.check_returncode()

def run_docker(args):
    if args[0] == 'tor':
         return run_tor_scraper('tor', args[1:])
    if args[0] == 'fa':
         return run_tor_scraper('fa', args[1:])
    run_metadata_scraper(args)

def run_metadata_scraper(args):
    parser = argparse.ArgumentParser(
                        description='Furaffinity Backup Client Runner')

    parser.add_argument('--dbDir', type=str, help='Directory to store databases', required=True)
    parser.add_argument('--getFiles', type=bool, help='Whether to download files', default=False)

    parser.add_argument('--url', type=str, help='Server URL', required=True)
    parser.add_argument('--secret', type=str, help='Server authorization token', required=True)
    parser.add_argument('-a', type=str, help='Furaffinity cookie "a"', required=True)
    parser.add_argument('-b', type=str, help='Furaffinity cookie "b"', required=True)

    parser.add_argument('--batchSize', type=int, default=1000, help='Batch size for submissions')

    parser.add_argument('-e', '--env', type=str, nargs="*", help='additional environment variables')
    parser.add_argument('-d', '--delay', type=str, help='override crawl delay (in seconds)')


    args = parser.parse_args(args)

    # Parse command line args
    # Initialize submodules

    # Build the dockerfile if it doesn't exist

    subprocess.run(['docker', 'build', '-t', 'fascraper', '.'])

    # Run the dockerfile

    env_args = [arg for env in args.env for arg in ['-e', env]] if args.env else []
    if args.delay is not None:
        env_args += ['-e', f'FALR_DELAY={args.delay}']
    if args.getFiles:
        env_args += ['-e', 'GET_FILES=1']
    run('docker', 'run', '--rm',
                    '-v', f'{args.dbDir}:/app/dbs',                
                    *env_args,
                    'fascraper',
                    'python', 'client.py', args.url, args.secret, args.a, args.b, str(args.batchSize))

def run_tor_scraper(source, args):
    parser = argparse.ArgumentParser(
                        description='Furaffinity Tor Backup Runner')

    parser.add_argument('--ipfsDir', type=str, help='Directory to store ipfs repo', default='./ipfs')
    
    parser.add_argument('--url', type=str, help='Server URL', required=True)
    parser.add_argument('--port', type=int, help='Server HTTP port', required=True)
    parser.add_argument('--replicas', type=int, help='number of scrapers to run in parallel', default=1)
    parser.add_argument('--swarm', type=str, help='Swarm key', required=True)
    parser.add_argument('--peer_id', type=str, help='Bootstrap peer ID', required=True)
    parser.add_argument('--secret', type=str, help='Server authorization token', required=True)
    parser.add_argument('--wait', type=bool, help='Dont run the scraper', default=False)
    
    parser.add_argument('-e', '--env', type=str, nargs="*", help='additional environment variables')

    args = parser.parse_args(args)

    Path(f'{args.ipfsDir}/data').mkdir(parents=True, exist_ok=True)
    with open(f'{args.ipfsDir}/data/swarm.key', 'w') as f:
         f.write(
f"""/key/swarm/psk/1.0.0/
/base16/
{args.swarm}""")

    # Build the containers if they don't exist

    env = {
        **os.environ,
        'IPFS_DIR': args.ipfsDir,
        'SECRET': args.secret,
        'HOSTNAME': args.url,
        'PORT': str(args.port),
        'PRIVATE_PEER_ID': args.peer_id,
        'REPLICAS': str(args.replicas),
        'SOURCE': source,
    }

    if args.wait:
        env['WAIT'] = '1'

    subprocess.run(['docker', 'compose', 'build'], env=env)

    # Run the dockerfile

    subprocess.run(['docker', 'compose', 'up'], env=env)
