#!/bin/bash



# Read Password
echo -n Password: 
read -s password
echo

percent_encoded_password=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" $password)

# URI
URI="mongodb://celery_api:$percent_encoded_password@commons3.sca.iu.edu:27017/celery_api?authSource=celery_api"

mongoexport \
    --uri="$URI" \
    --collection="celery_taskmeta" \
    --out="celery_taskmeta.json"

mongoexport \
    --uri="$URI" \
    --collection="workflow_meta" \
    --out="workflow_meta.json"