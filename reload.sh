#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

bash kubernetes/start-cluster.sh