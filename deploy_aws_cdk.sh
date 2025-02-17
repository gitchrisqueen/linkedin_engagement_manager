#!/bin/bash

# Load the .env file (optional, Docker Compose will load this automatically if the .env is in the root)
export $(grep -v '^#' .env | xargs)

# Set environment variable NO_PREBUILT_LAMBDA =1
export NO_PREBUILT_LAMBDA=1

echo "Choose deployment option:"
echo "1) Deploy all stacks at once"
echo "2) Deploy all stacks sequentially "
echo "3) Deploy specific stack"
read -p "Enter your choice (1 [default], 2, or 3): " choice

case $choice in
    2)
        poetry run python -m cqc_lem.aws.deploy
        ;;
    3)
        # Get list of stacks using AWS CDK
        echo "Available stacks:"
        # Store the stack list in an array
        stacks=()
        while IFS= read -r line; do
            stacks+=("$line")
        done < <(npx -p node@22 cdk list --app "python -m cqc_lem.aws.app")

        # Display stacks with numbers
        for i in "${!stacks[@]}"; do
            echo "$((i+1))) ${stacks[$i]}"
        done

        # Get user selection
        read -p "Enter the number of the stack to deploy: " stack_num

        # Validate input
        if [[ "$stack_num" =~ ^[0-9]+$ ]] && [ "$stack_num" -ge 1 ] && [ "$stack_num" -le "${#stacks[@]}" ]; then
            selected_stack="${stacks[$((stack_num-1))]}"
            poetry run python -m cqc_lem.aws.deploy --stack "$selected_stack"
        else
            echo "Invalid selection. Please choose a number between 1 and ${#stacks[@]}"
            exit 1
        fi
        ;;
    *)
        poetry run python -m cqc_lem.aws.deploy --all
        ;;
esac