import pandas as pd, numpy as np, mongomock

# === Load CSVs ===
csv_files = [
    ('data/raw/2021-dec16.csv', 'data/cleaned/2021-dec16-cleaned.csv'),
    ('data/raw/2021-oct21.csv', 'data/cleaned/2021-oct21-cleaned.csv'),
    ('data/raw/2022-nov16.csv', 'data/cleaned/2022-nov16-cleaned.csv'),
    ('data/raw/2022-oct7.csv', 'data/cleaned/2022-oct7-cleaned.csv')
]

num_columns = [
    "C Inside Temp (c)", "DFS Depth (m)", "DTB Height (m)", "Total Water Column (m)",
    "Temperature (c)", "Salinity (ppt)", "ODO mg/L"
]

cleaned_dfs = []  # store all cleaned DataFrames for combining later

for raw_path, cleaned_path in csv_files:
    print(f"\nProcessing file: {raw_path}")

    df = pd.read_csv(raw_path)

    # Compute z-scores
    for col in num_columns:
        df[f'{col}_zscore'] = (df[col] - df[col].mean()) / df[col].std()

    # Drop outliers (|z| > 3)
    df_clean = df[(df[[f'{col}_zscore' for col in num_columns]].abs() <= 3).all(axis=1)]

    total_rows = len(df)
    rows_removed = total_rows - len(df_clean)
    rows_remaining = len(df_clean)

    print('Data Cleaning Report:')
    print(f'  Original rows: {total_rows}')
    print(f'  Rows removed: {rows_removed}')
    print(f'  Rows remaining: {rows_remaining}')

    # Prepare cleaned version
    df_clean = df_clean.drop(columns=[f'{col}_zscore' for col in num_columns])

    df_clean.rename(columns={
        'Time hh:mm:ss': 'Time_hh_mm_ss',
        'Date m/d/y': 'Date_mm_dd_yy',
        'Temperature (c)': 'Temperature_c',
        'Salinity (ppt)': 'Salinity_ppt',
        'ODO mg/L': 'ODO_mg_L'
    }, inplace=True)

    # Save individual cleaned file
    df_clean.to_csv(cleaned_path, index=False)
    print(f'  Cleaned file saved to: {cleaned_path}')

    cleaned_dfs.append(df_clean)

# === Combine all cleaned data for MongoDB ===
combined_df = pd.concat(cleaned_dfs, ignore_index=True)

# === Insert into MongoMock ===
client = mongomock.MongoClient()
db = client['water_quality_data']
collection = db['asv']
collection.insert_many(combined_df.to_dict('records'))
collection.create_index('Time_hh_mm_ss')

print('\nAll cleaned data inserted into mongomock successfully!')
