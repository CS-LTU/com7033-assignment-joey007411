import os
import sys
from pymongo import MongoClient, errors
import pandas as pd

def clean_value(v):
    if pd.isna(v): 
        return None
    if isinstance(v, str):
        s = v.strip()
        if s == '' or s.lower() in ('nan', 'n/a', 'none', 'null'):
            return None
        return s
    return v

def row_to_doc(row, cols):
    doc = {}
    for c in cols:
        val = clean_value(row.get(c))
        if c in ('id',):
            try:
                doc['_id'] = int(val) if val is not None else None
                doc['id'] = int(val) if val is not None else None
            except Exception:
                doc['id'] = val
        elif c in ('age', 'hypertension', 'heart_disease', 'stroke'):
            try:
                doc[c] = int(val) if val is not None else None
            except Exception:
                doc[c] = None
        elif c in ('avg_glucose_level', 'bmi'):
            try:
                doc[c] = float(val) if val is not None else None
            except Exception:
                doc[c] = None
        else:
            doc[c] = val
    if doc.get('_id') is None:
        doc.pop('_id', None)
    return doc

def push_csv(csv_path, mongo_uri, db_name, coll_name, drop=False, sep=','):
    df = pd.read_csv(csv_path, sep=sep, dtype=str)
    expected_cols = ['id','gender','age','hypertension','heart_disease','ever_married',
                     'work_type','Residence_type','avg_glucose_level','bmi','smoking_status','stroke']
    df.columns = [c.strip() for c in df.columns]
    cols = [c for c in expected_cols if c in df.columns]
    if not cols:
        raise ValueError("No expected columns found in CSV. Found: {}".format(list(df.columns)))
    docs = [ row_to_doc(row._asdict(), cols) for row in df.itertuples(index=False, name='Row') ]

    client = MongoClient(mongo_uri)
    db = client[db_name]
    coll = db[coll_name]
    if drop:
        coll.drop()
        print("Dropped existing collection:", coll_name)

    inserted = 0
    for doc in docs:
        try:
            if '_id' in doc:
                _id = doc.pop('_id')
                coll.update_one({'_id': _id}, {'$set': doc}, upsert=True)
            else:
                if 'id' in doc and doc['id'] is not None:
                    coll.update_one({'id': doc['id']}, {'$set': doc}, upsert=True)
                else:
                    coll.insert_one(doc)
            inserted += 1
        except errors.PyMongoError as e:
            print("Mongo error for doc id={} : {}".format(doc.get('id'), e))
    print(f"Processed {inserted} rows -> collection {db_name}/{coll_name}")
    client.close()

def main():
    csv_path = "healthcare-dataset-stroke-data.csv"
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    db_name = "healthcare"
    coll_name = "strokes"
    drop_collection = True  # Set to False if you don't want to drop existing data

    try:
        push_csv(csv_path, mongo_uri, db_name, coll_name, drop=drop_collection)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()