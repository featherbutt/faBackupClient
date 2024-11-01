import argparse
import subprocess

def run(*args):
        process = subprocess.run(args)
        process.check_returncode()

def run_docker(args):
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