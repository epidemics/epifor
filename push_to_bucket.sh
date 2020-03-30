if [ -z "$1" ]; then
    echo "Needs two params: FILE TARGET_FILE (e.g. data-staging-gleam.json)"
    exit 1
fi

TGT="gs://static-covid/static/$2"

gsutil -h "Cache-Control:public, max-age=10" cp -Z -a public-read "$1" "$TGT"

echo "URL: https://storage.googleapis.com/static-covid/static/$2"
