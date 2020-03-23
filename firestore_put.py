import argparse
import logging
import json

from google.cloud import firestore


def main():
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("FILE", help="JSON file to upload.")
    ap.add_argument("DATASET", help="Target dataset.")
    ap.add_argument("-C", "--channel", default="staging", help="Target channel.")
    ap.add_argument("-d", "--debug", action="store_true", help="Debug logs.")
    args = ap.parse_args()
    if args.debug:
        logging.root.setLevel(logging.DEBUG)

    assert args.DATASET in ["gleam", "estimates", "countermeasures"]

    # Add a new document
    db = firestore.Client()
    doc_ref = db.collection("data").document(f"{args.channel}-{args.DATASET}")
    doc_ref.set({"json": json.dumps({"test": [43, 44]})})


if __name__ == "__main__":
    main()
