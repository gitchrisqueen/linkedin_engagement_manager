import json
import os
import subprocess
import sys


def deploy_stacks_in_order():
    # Get the directory of this current file as base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Change directory to the base directory
    os.chdir(base_dir)

    # Get the --all flag from the command line arguments
    all_flag = '--all' in sys.argv

    # Get the --stack flag from the command line arguments
    stack_flag = '--stack' in sys.argv


    if all_flag:
        print(f"Deploying All Stacks")
        subprocess.run(['npx', '-p', 'node@22', 'cdk', 'deploy', '--require-approval', 'never', '--all'], check=False)
    elif stack_flag:
        stack_index = sys.argv.index('--stack')
        stack_name = sys.argv[stack_index + 1]
        print(f"Deploying Stack: {stack_name}")
        subprocess.run(['npx', '-p', 'node@22', 'cdk', 'deploy', '--require-approval', 'never', stack_name], check=False)
    else:
        with open('cdk.json') as f:
            print(f"Deploying Sequentially")
            config = json.load(f)
            deploy_order = config['context']['deployOrder']
            for stack in deploy_order:
                print(f"Deploying stack: {stack}")
                subprocess.run(['npx', '-p', 'node@22', 'cdk', 'deploy', '--require-approval', 'never', stack],
                               check=False)


if __name__ == "__main__":
    deploy_stacks_in_order()
