import argparse
import subprocess

parser = argparse.ArgumentParser(
                    prog='run.py',
                    description='Furaffinity Backup Client Runner')

parser.add_argument('--dbDir', type=str, help='Directory to store databases', required=True)
parser.add_argument('--url', type=str, help='Server URL', required=True)
parser.add_argument('--secret', type=str, help='Server authorization token', required=True)
parser.add_argument('-a', type=str, help='Furaffinity cookie "a"', required=True)
parser.add_argument('-b', type=str, help='Furaffinity cookie "b"', required=True)

parser.add_argument('--batchSize', type=int, default=1000, help='Batch size for submissions')

args = parser.parse_args()

# Parse command line args
# Initialize submodules

subprocess.run(['git', 'submodule', 'init'])
subprocess.run(['git', 'submodule', 'update'])

# Build the dockerfile if it doesn't exist

subprocess.run(['docker', 'build', '-t', 'fascraper', '.'])

# Run the dockerfile

subprocess.run(['docker', 'run',
                '-v', f'{args.dbDir}:/app/dbs',
                'fascraper',
                'python', 'client.py', args.url, args.secret, args.a, args.b, str(args.batchSize)])