from dataCleanUp import collection
from flask import Flask, jsonify, request
import pandas as pd, numpy as np

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        "routes":{
            "/api": "Check if API is running",
            "/api/observations": "Return observations with optional filters",
            "/api/stats": "Summary statistics for numeric fields",
            "/api/outliers": "Return outliers by z-score or IQR",
        }
    })

@app.route('/api', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

@app.route('/api/observations', methods=['GET'])
def get_observations():
    start = request.args.get('start')
    end = request.args.get('end')
    min_temp = request.args.get('min_temp', type=float)
    max_temp = request.args.get('max_temp', type=float)
    min_sal = request.args.get('min_sal', type=float)
    max_sal = request.args.get('max_sal', type=float)
    min_odo = request.args.get('min_odo', type=float)
    max_odo = request.args.get('max_odo', type=float)
    limit = min(request.args.get('limit', 100, type=int), 1000)
    skip = request.args.get('skip', 0, type=int)

    query = {}

    if start or end:
        query['Time_hh_mm_ss'] = {}
        if start: query['Time_hh_mm_ss']['$gte'] = start
        if end: query['Time_hh_mm_ss']['$lte'] = end

    if min_temp is not None or max_temp is not None:
        query['Temperature_c'] = {}
        if min_temp is not None: query['Temperature_c']['$gte'] = min_temp
        if max_temp is not None: query['Temperature_c']['$lte'] = max_temp

    if min_sal is not None or max_sal is not None:
        query['Salinity_ppt'] = {}
        if min_sal is not None: query['Salinity_ppt']['$gte'] = min_sal
        if max_sal is not None: query['Salinity_ppt']['$lte'] = max_sal

    if min_odo is not None or max_odo is not None:
        query['ODO_mg_L'] = {}
        if min_odo is not None: query['ODO_mg_L']['$gte'] = min_odo
        if max_odo is not None: query['ODO_mg_L']['$lte'] = max_odo

    items = list(collection.find(query).skip(skip).limit(limit))
    for item in items:
        item['_id'] = str(item['_id'])

    return jsonify({'count': len(items), 'items': items})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    df = pd.DataFrame(list(collection.find()))
    num_columns = ['Temperature_c', 'Salinity_ppt', 'ODO_mg_L']

    stats = {}
    for col in num_columns:
        stats[col] = {
            'count': int(df[col].count()),
            'mean': float(df[col].mean()),
            'min': float(df[col].min()),
            'max': float(df[col].max()),
            '25%': float(df[col].quantile(0.25)),
            '50%': float(df[col].quantile(0.5)),
            '75%': float(df[col].quantile(0.75))
        }
    return jsonify(stats)

@app.route('/api/outliers', methods=['GET'])
def get_outliers():
    field = request.args.get('field')
    method = request.args.get('method', 'z-score')
    k = float(request.args.get('k', 3))

    # Load data from Mongo
    df = pd.DataFrame(list(collection.find()))

    # Defensive checks
    if df.empty:
        return jsonify({'error': 'No data in collection'}), 400
    if field not in df.columns:
        return jsonify({'error': f'Field {field} not found in data columns {list(df.columns)}'}), 400

    # Ensure numeric conversion
    df[field] = pd.to_numeric(df[field], errors='coerce')
    df = df.dropna(subset=[field])

    # Outlier detection
    if method == 'z-score':
        df['z'] = (df[field] - df[field].mean()) / df[field].std()
        outliers = df[np.abs(df['z']) > k]
    elif method == 'iqr':
        Q1 = df[field].quantile(0.25)
        Q3 = df[field].quantile(0.75)
        IQR = Q3 - Q1
        outliers = df[(df[field] < Q1 - k * IQR) | (df[field] > Q3 + k * IQR)]
    else:
        return jsonify({'error': 'Invalid method. Use z-score or iqr.'}), 400

    # Convert ObjectId and output
    outliers_list = outliers.to_dict(orient='records')
    for item in outliers_list:
        if '_id' in item:
            item['_id'] = str(item['_id'])

    return jsonify({'count': len(outliers_list), 'items': outliers_list})


if __name__ == '__main__':
    app.run(debug=True, port=8000)
