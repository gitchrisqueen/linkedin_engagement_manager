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

        #while IFS= read -r line; do
        #    stacks+=("$line")
        #done < <(npx -p node@22 cdk list --app "python -m cqc_lem.aws.app")

        # Get the list of stacks from the deploy order in the cdk.json file
        stacks=($(jq -r '.context.deployOrder[]' src/cqc_lem/aws/cdk.json))

        # Display stacks with numbers
        for i in "${!stacks[@]}"; do
            echo "$((i+1))) ${stacks[$i]}"
        done

       # Get user selection
       read -p "Enter the stack numbers to deploy (comma-separated): " stack_nums

       # Convert comma-separated string to array
       IFS=',' read -ra selected_nums <<< "$stack_nums"
       selected_stacks=()

       # Validate each input number and collect stack names
       valid=true
       for num in "${selected_nums[@]}"; do
           # Remove leading/trailing whitespace
           num=$(echo "$num" | tr -d '[:space:]')

           if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le "${#stacks[@]}" ]; then
               selected_stacks+=("${stacks[$((num-1))]}")
           else
               echo "Invalid selection: $num. Please choose numbers between 1 and ${#stacks[@]}"
               valid=false
               break
           fi
       done

       if [ "$valid" = true ]; then
           # Join stack names with spaces
           stack_list="${selected_stacks[*]}"
           poetry run python -m cqc_lem.aws.deploy --stack "$stack_list"
       else
           exit 1
       fi
       ;;
    *)
        poetry run python -m cqc_lem.aws.deploy --all
        ;;
esac


echo "Cleaning up old Docker images older than 7 days..."
docker image prune -a --filter "until=168h" -f

# Remove build cache only
echo "Cleaning up Docker build cache older than 7 days..."
docker builder prune --filter "until=168h" -f

