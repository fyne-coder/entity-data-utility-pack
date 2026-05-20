import pandas as pd
import dask.dataframe as dd
import multiprocessing
import configparser
import os
from fuzzywuzzy import fuzz
from dask.diagnostics import ProgressBar

# Load the configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Extract relevant configurations
INPUT_DATA_DIR = config['DEFAULT']['INPUT_DATA_DIR']
OUTPUT_DATA_DIR = config['DEFAULT']['OUTPUT_DATA_DIR']
INPUT_FILENAME = config['COMMON']['INPUT_FILENAME']
URL = config['COMMON']['URL']
OUTPUT_FILENAME = config['RECALL_ANALYSIS']['OUTPUT_FILENAME']
BLOCKING_COL = config['RECALL_ANALYSIS']['BLOCKING_COL']
ID_COL = config['RECALL_ANALYSIS']['ID_COL']
ADD_COLS = [col.strip() for col in config['RECALL_ANALYSIS']['ADD_COLS'].split(',')]

# Ensure the INPUT_DATA_DIR exists
if not os.path.exists(INPUT_DATA_DIR):
    os.makedirs(INPUT_DATA_DIR)

# Ensure the OUTPUT_DATA_DIR exists
if not os.path.exists(OUTPUT_DATA_DIR):
    os.makedirs(OUTPUT_DATA_DIR)

def similar(a, b):
    return fuzz.ratio(a, b) / 100

def find_duplicates(df, blocking_col, id_col, threshold, show_full_name=True, url=None, additional_cols=None):
    duplicates = []
    
    if additional_cols is None:
        additional_cols = []
    
    for _, group in df.groupby(blocking_col):
        for i in range(len(group)):
            for j in range(i+1, len(group)):
                score_1 = similar(group[additional_cols[0]].iloc[i], group[additional_cols[0]].iloc[j])
                
                if score_1 >= threshold:
                    scores_rest = [
                        similar(group[col].iloc[i], group[col].iloc[j])
                        for col in additional_cols[1:]
                    ]
                    # Excel HYPERLINK formula
                    hyperlink_formula = f'=HYPERLINK("{url}{group[id_col].iloc[i]}?tab=Manage+Cluster+Details")'
                    
                    if show_full_name:
                        duplicate_entry = (
                            hyperlink_formula,
                            group[id_col].iloc[i],
                            group[blocking_col].iloc[i],
                            group[id_col].iloc[j],
                            group[blocking_col].iloc[j],
                            score_1,
                            *scores_rest
                        )
                    else:
                        duplicate_entry = (
                            hyperlink_formula,
                            group[id_col].iloc[i],
                            group[id_col].iloc[j],
                            score_1,
                            *scores_rest
                        )
                    duplicates.append(duplicate_entry)

    col_names = ['URL_ID_1', f'{id_col}_1', f'{blocking_col}_1', f'{id_col}_2', f'{blocking_col}_2', f'Score_{additional_cols[0]}']
    col_names.extend([f'Score_{col}' for col in additional_cols[1:]])
    
    if show_full_name:
        col_names = ['URL_ID_1', f'{id_col}_1', f'{blocking_col}_1', f'{id_col}_2', f'{blocking_col}_2', f'Score_{additional_cols[0]}']
    else:
        col_names = ['URL_ID_1', f'{id_col}_1', f'{id_col}_2', f'Score_{additional_cols[0]}']

    col_names.extend([f'Score_{col}' for col in additional_cols[1:]])
    
    return pd.DataFrame(duplicates, columns=col_names)

def find_and_save_duplicates(input_filepath, output_filepath, blocking_col, id_col, threshold=50, show_full_name=True, url=None, additional_cols=None):
    df = pd.read_csv(input_filepath)
    print(df.columns.tolist())
    df.columns = [col.strip() for col in df.columns]

    try:
        print("\nFirst few rows of specified columns:")
        print(f"{id_col}: ", df[id_col].head().tolist())
        print(f"{blocking_col}: ", df[blocking_col].head().tolist())
        for additional_col in additional_cols:
            print(f"{additional_col}: ", df[additional_col].head().tolist())
    except KeyError as e:
        print(f"\nColumn not found: {e}")

    if id_col not in df.columns or blocking_col not in df.columns or not all(col in df.columns for col in additional_cols):
        raise ValueError("Specified ID, blocking, or additional column not found in input data.")
    
    n_cores = multiprocessing.cpu_count()
    ddf = dd.from_pandas(df, npartitions=n_cores)
    
    with ProgressBar():
        # Constructing column names dynamically based on the number of additional columns
        col_names = ['URL_ID_1', f'{id_col}_1', f'{blocking_col}_1', f'{id_col}_2', f'{blocking_col}_2', f'Score_{additional_cols[0]}']
        col_names.extend([f'Score_{col}' for col in additional_cols[1:]])
        # Constructing column names dynamically based on the number of additional columns
        if show_full_name:
            col_names = ['URL_ID_1', f'{id_col}_1', f'{blocking_col}_1', f'{id_col}_2', f'{blocking_col}_2', f'Score_{additional_cols[0]}']
        else:
            col_names = ['URL_ID_1', f'{id_col}_1', f'{id_col}_2', f'Score_{additional_cols[0]}']

        col_names.extend([f'Score_{col}' for col in additional_cols[1:]])
        # Creating metadata DataFrame with accurate column names
        meta = pd.DataFrame(columns=col_names, dtype='float64')

        potential_duplicates = ddf.map_partitions(
            find_duplicates, blocking_col, id_col, threshold, show_full_name, url, additional_cols,
            meta=meta
        ).compute()
    
    potential_duplicates.to_csv(output_filepath, index=False)
    print(potential_duplicates)


input_filepath = f'{INPUT_DATA_DIR}/{INPUT_FILENAME}'
output_filepath = f'{OUTPUT_DATA_DIR}/{OUTPUT_FILENAME}'

find_and_save_duplicates(
    input_filepath=input_filepath,
    output_filepath=output_filepath,
    blocking_col=BLOCKING_COL,
    id_col=ID_COL,
    threshold=0.50,  # This can be configurable as well if needed
    show_full_name=False,  # This too can be made configurable
    url=URL,
    additional_cols=ADD_COLS
)
