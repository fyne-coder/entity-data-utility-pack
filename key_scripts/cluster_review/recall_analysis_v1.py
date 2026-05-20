import pandas as pd
import dask.dataframe as dd
import multiprocessing
from fuzzywuzzy import fuzz
from dask.diagnostics import ProgressBar

def similar(a, b):
    return fuzz.ratio(a, b)

def find_duplicates(df, blocking_col, id_col, threshold=80, show_full_name=True, url=None, additional_cols=None):
    duplicates = []
    
    if additional_cols is None:
        additional_cols = []
    
    for _, group in df.groupby(blocking_col):
        for i in range(len(group)):
            for j in range(i+1, len(group)):
                score_1 = fuzz.ratio(group[additional_cols[0]].iloc[i], group[additional_cols[0]].iloc[j])
                
                if score_1 >= threshold:
                    scores_rest = [
                        fuzz.ratio(group[col].iloc[i], group[col].iloc[j])
                        for col in additional_cols[1:]
                    ]
                    # Excel HYPERLINK formula
                    hyperlink_formula = f'=HYPERLINK("{url}{group[id_col].iloc[i]}?tab=Manage+Cluster+Details")'
                    
                    duplicate_entry = (
                        hyperlink_formula,
                        group[id_col].iloc[i] if show_full_name else "",
                        group[blocking_col].iloc[i],
                        group[id_col].iloc[j] if show_full_name else "",
                        group[blocking_col].iloc[j],
                        score_1,
                        *scores_rest
                    )
                    duplicates.append(duplicate_entry)

    col_names = ['URL_ID_1', f'{id_col}_1', f'{blocking_col}_1', f'{id_col}_2', f'{blocking_col}_2', f'Score_{additional_cols[0]}']
    col_names.extend([f'Score_{col}' for col in additional_cols[1:]])
    
    if not show_full_name:
        col_names.remove(f'{id_col}_1')
        col_names.remove(f'{id_col}_2')
    
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
        if not show_full_name:
            col_names = [col for col in col_names if id_col not in col]
        # Creating metadata DataFrame with accurate column names
        meta = pd.DataFrame(columns=col_names, dtype='float64')

        potential_duplicates = ddf.map_partitions(
            find_duplicates, blocking_col, id_col, threshold, show_full_name, url, additional_cols,
            meta=meta
        ).compute()
    
    potential_duplicates.to_csv(output_filepath, index=False)
    print(potential_duplicates)

# Example usage
input_filepath = './data/entity_records.csv'
output_filepath = './data/potential_duplicates.csv'
blocking_col = 'Date Of Birth'
id_col = 'Entity ID'
add_cols = ['Full Name', 'First Name', 'Last Name', 'Gender', 'Enriched Full Address']

find_and_save_duplicates(
    input_filepath=input_filepath,
    output_filepath=output_filepath,
    blocking_col=blocking_col,
    id_col=id_col,
    threshold=50,
    show_full_name=True,
    url="https://example.com/entities/",
    additional_cols= add_cols
)
