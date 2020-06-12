#!/bin/sh

# set -x
set -e

if [ "$GITLAB_URL" == "" ]; then
    echo "GITLAB_URL is required"
    exit 1
fi

if [ "$GITLAB_ACCESS_TOKEN" == "" ]; then
    echo "GITLAB_ACCESS_TOKEN is required"
    exit 1
fi

if [ "$FILTER_DATE_BEGIN" != "" ]; then
    export FILTER_DATE_BEGIN1=" --filter-by-date-begin $FILTER_DATE_BEGIN"
fi
if [ "$FILTER_DATE_END" != "" ]; then
    export FILTER_DATE_END1=" --filter-by-date-end $FILTER_DATE_END"
fi
if [ "$FILTER_AUTHOR" != "" ]; then
    export FILTER_AUTHOR1=" --filter-by-author $FILTER_AUTHOR"
fi
if [ "$FILTER_SEARCH" != "" ]; then
    export FILTER_SEARCH1=" --filter-by-search $FILTER_SEARCH"
fi
if [ "$FILTER_ONLY_MEMBER" == "true" ]; then
    export FILTER_ONLY_MEMBER1=" --filter-by-project-membership"
fi

if [ "$DEBUG" == "true" ]; then
    export DEBUG1=" --debug"
fi

python3 /gitlab-cli-reports/main.py \
  --host-url $GITLAB_URL \
  --access-token $GITLAB_ACCESS_TOKEN \
  $FILTER_DATE_BEGIN1 \
  $FILTER_DATE_END1 \
  $FILTER_AUTHOR1 \
  $FILTER_SEARCH1 \
  $FILTER_ONLY_MEMBER1 \
  $DEBUG1
  
