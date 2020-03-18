if [ -z "$1" ]; then
    echo "Needs two params: FILE TARGET_FILE (e.g. data-staging-gleam.json)"
    exit 1
fi

TGT="gs://static-covid/static/$2"

gsutil cp "$1" "$TGT"
gsutil setmeta -h "Cache-Control:public, max-age=30" "$TGT"
gsutil acl ch -u AllUsers:R "$TGT"

echo "URL: https://storage.googleapis.com/static-covid/static/$2"
