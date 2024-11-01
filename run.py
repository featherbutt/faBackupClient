import subprocess
import sys

def run(*args):
    process = subprocess.run(args)
    process.check_returncode()

run('git', 'pull')
run('git', 'submodule', 'init')
run('git', 'submodule', 'update')

import docker

docker.run_docker(sys.argv[1:])