#!/bin/bash
#
# This script runs integration tests for different backends (local, lf-cloud, and gcs).
#
# Usage:
#   ./run.sh [-m <mode>] [-k <test_key>]
#
# Options:
#   -m <mode>    Specify the test mode: all, local, lf-cloud, or gcs (default: all)
#   -k <test_key> Optional pytest -k parameter to filter tests
#
# Examples:
#   Run all tests:
#   ./run.sh
#
#   Run only local tests:
#   ./run.sh -m local
#
#   Run only aws tests:
#   ./run.sh -k "aws"
#
#   Run only gcp tests:
#   ./run.sh -k "gcp"
#
#   Run local aws tests:
#   ./run.sh -m local -k "aws"
#
#   Run local gcp tests:
#   ./run.sh -m local -k "gcp"

echo "Verifying AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
    echo "User is logged in to AWS"
else
    echo "User is not logged in to AWS"
    exit 1
fi

echo "Verifying GCP credentials..."
if gcloud auth list --filter=status:ACTIVE --format="value(account)" &>/dev/null && gcloud auth application-default print-access-token &> /dev/null; then
    echo "GCP credentials are active"
else
    echo "GCP credentials are not active or have expired. Please run: \`gcloud auth application-default login\`"
    exit 1
fi
# Parse command line arguments
OPTION="all"
KEY=""
while getopts ":m:k:" opt; do
    case $opt in
        m)
            OPTION="$OPTARG"
            ;;
        k)
            KEY="$OPTARG"
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            exit 1
            ;;
    esac
done

# Validate option
case $OPTION in
    all|local|lf-cloud|gcs)
        echo "Selected mode: $OPTION"
        ;;
    *)
        echo "Invalid mode: $OPTION. Valid modes are: all, local, lf-cloud, gcs" >&2
        exit 1
        ;;
esac


pytest_command="pytest environments_integration_tests.py --disable-warnings --integration -s"
if [ ! -z "$KEY" ]; then
    pytest_command="$pytest_command -k $KEY"
fi

# Function to print cleanup instructions
print_cleanup_instructions() {
    local directory_path="$1"
    echo "=============================================================================="
    echo ""
    echo "Local integration tests failed"
    echo ""
    echo "BE SURE TO CLEAN UP ANY RESOURCES CREATED BY THE TESTS"
    echo ""
    echo "Navigate to: $directory_path"
    echo "Run the following commands (note you may need to run them multiple times for each environment):"
    echo "- lf destroy"
    echo "- lf environments delete"
    echo ""
    echo "=============================================================================="
}



pids=()

if [ "$OPTION" = "all" ] || [ "$OPTION" = "local" ]; then
    echo "Running local integration tests..."
    echo "Logs are written to: /tmp/local-integration-tests.log"
    TEST_MODE="local" $pytest_command &> /tmp/local-integration-tests.log &
    pids+=($!)
fi

if [ "$OPTION" = "all" ] || [ "$OPTION" = "lf-cloud" ]; then
    echo "Running LF Cloud integration tests..."
    echo "Logs are written to: /tmp/lf-cloud-integration-tests.log"
    TEST_MODE="lf-cloud" $pytest_command &> /tmp/lf-cloud-integration-tests.log &
    pids+=($!)
fi

if [ "$OPTION" = "all" ] || [ "$OPTION" = "gcs" ]; then
    echo "Running GCS integration tests..."
    echo "Logs are written to: /tmp/gcs_integration_tests.log"
    TEST_MODE="gcs" $pytest_command &> /tmp/gcs_integration_tests.log &
    pids+=($!)
fi

# Wait for all background processes to finish
for pid in "${pids[@]}"; do
    wait $pid
    results+=($?)
done

# Check results and print appropriate messages
failed=false
for i in "${!pids[@]}"; do
    if [ ${results[$i]} -ne 0 ]; then
        failed=true
        case $i in
            0)
                print_cleanup_instructions "test/integration/integration_tests/local-backend"
                ;;
            1)
                print_cleanup_instructions "test/integration/integration_tests/lf-cloud-backend"
                ;;
            2)
                print_cleanup_instructions "test/integration/integration_tests/lf-cloud-backend"
                ;;
        esac
    else
        case $i in
            0) echo "Local integration tests passed" ;;
            1) echo "LF Cloud integration tests passed" ;;
            2) echo "GCS integration tests passed" ;;
        esac
    fi
done

if [ "$failed" = true ]; then
    echo "Some tests failed"
    exit 1
else
    echo "All integration tests passed"
    exit 0
fi

echo "All integration tests passed"
