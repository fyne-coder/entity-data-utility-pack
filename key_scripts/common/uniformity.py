import os
import pandas as pd
import numpy as np
import logging
import concurrent.futures
import warnings
import configparser
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm
import cProfile

# Load the configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Extract relevant configurations
# Extract relevant configurations
DATA_DIR = config['DEFAULT']['INPUT_DATA_DIR']
OUTPUT_DATA_DIR = config['DEFAULT']['OUTPUT_DATA_DIR']
INPUT_FILENAME = config['COMMON']['INPUT_FILENAME']
CLUSTER_DETAILS_FILENAME = config['COMMON']['CLUSTER_DETAIL_FILENAME']
UNIFORMITY_SCORE_COLUMN = config['UNIFORMITY_ANALYSIS']['UNIFORMITY_SCORE_COLUMN']
URL = config['COMMON']['URL']
ID_COLUMN = config['UNIFORMITY_ANALYSIS']['ID_COLUMN']
OUTPUT_FILENAME = os.path.join(OUTPUT_DATA_DIR, config['UNIFORMITY_ANALYSIS']['OUTPUT_FILENAME'])
BATCH_SIZE = 100  # You can adjust this value based on your dataset and available memory.
TEST_MODE = config['DEFAULT'].getboolean('TEST_MODE', fallback=False)

# Ensure the DATA_DIR exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
# Ensure the OUTPUT_DATA_DIR exists
if not os.path.exists(OUTPUT_DATA_DIR):
    os.makedirs(OUTPUT_DATA_DIR)

# Setup logging
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.feature_extraction.text", message="The parameter 'token_pattern' will not be used since 'tokenizer' is not None'")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def process_batch(rows_batch, cluster_sizes, clusters_dict, ml_columns, vectorizer):
    """Process a batch of rows and return the results."""
    results = []
    for row in rows_batch.itertuples(index=False):  # Using itertuples for efficient row iteration
        entity_id = getattr(row, ID_COLUMN)
        cluster_size = cluster_sizes.get(entity_id, 0)

        if cluster_size <= 1:
            continue  # Skip the row if the cluster is a singleton or not found

        cluster = clusters_dict.get(entity_id)  # Get the actual cluster data
        result_row = {ID_COLUMN: entity_id, UNIFORMITY_SCORE_COLUMN: getattr(row, UNIFORMITY_SCORE_COLUMN)}
        for col in ml_columns:
            similarity = calculate_similarity_within_cluster(cluster, col, vectorizer)  # Pass the vectorizer
            result_row[col] = similarity

        results.append(result_row)
    return results

def custom_tokenizer(s):
    """Custom tokenizer that treats single characters as valid tokens."""
    return s.split()

def add_hyperlink_column(df: pd.DataFrame, url: str, id_col: str) -> pd.DataFrame:
    """Add a new hyperlink column to the dataframe."""
    hyperlinks = [f'=HYPERLINK("{url}{df[id_col].iloc[i]}?tab=Manage+Cluster+Details")' for i in range(len(df))]
    df.insert(0, 'Hyperlink', hyperlinks)
    return df

def load_data(data_dir: str, input_filename: str, cluster_details_filename: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        input_df = pd.read_csv(os.path.join(data_dir, input_filename))
        cluster_details_df = pd.read_csv(os.path.join(data_dir, cluster_details_filename), low_memory=False)
        return input_df, cluster_details_df
    except Exception as e:
        logging.error(f"Error loading data: {str(e)}")
        raise

def process_row(row, cluster_sizes, clusters_dict, ml_columns, vectorizer):
    """Process a single row from input_df and return the result."""
    entity_id = row[ID_COLUMN]
    cluster_size = cluster_sizes.get(entity_id, 0)

    # Skip the calculation if the cluster is a singleton or not found
    if cluster_size <= 1:
        return None

    cluster = clusters_dict.get(entity_id)  # Get the actual cluster data
    result_row = {ID_COLUMN: entity_id, UNIFORMITY_SCORE_COLUMN: row[UNIFORMITY_SCORE_COLUMN]}
    for col in ml_columns:
        similarity = calculate_similarity_within_cluster(cluster, col, vectorizer)  # Pass the vectorizer
        result_row[col] = similarity

    return result_row

# Declare the vectorizer outside the function
vectorizer = TfidfVectorizer(lowercase=True, tokenizer=custom_tokenizer, stop_words=None)

def calculate_similarity_within_cluster(cluster: pd.DataFrame, column_name: str, vectorizer) -> float:
    texts = cluster[column_name].astype(str).replace({"nan": "", "None": ""}).values
    try:
        vectors = vectorizer.transform(texts)  # Keep the vectors in sparse format
        similarity_matrix = cosine_similarity(vectors)
        avg_similarity = (similarity_matrix.sum() - np.trace(similarity_matrix)) / (len(cluster) * (len(cluster) - 1))
    except ValueError as e:
        avg_similarity = 0
    return avg_similarity

def main():
    try:
        # Load the data and handle mixed data types warning
        input_df = pd.read_csv(os.path.join(DATA_DIR, INPUT_FILENAME), dtype={1: str, 10: str})
        cluster_details_df = pd.read_csv(os.path.join(DATA_DIR, CLUSTER_DETAILS_FILENAME), low_memory=False)

        # Fit the vectorizer here after loading cluster_details_df
        vectorizer.fit(cluster_details_df.astype(str).replace({"nan": "", "None": ""}).values.ravel())

        ml_columns = [col for col in cluster_details_df.columns if col.startswith("ml_")]
        
        cluster_sizes = cluster_details_df['persistentId'].value_counts().to_dict()
        clusters_dict = {key: group for key, group in cluster_details_df.groupby('persistentId')}

        # Create batches
        rows_batches = [input_df.iloc[i:i + BATCH_SIZE] for i in range(0, len(input_df), BATCH_SIZE)]
        cluster_sizes_list = [cluster_sizes] * len(rows_batches)
        clusters_dict_list = [clusters_dict] * len(rows_batches)
        ml_columns_list = [ml_columns] * len(rows_batches)
        
        # If TEST_MODE is enabled, limit to processing only 5 records
        if TEST_MODE:
            rows_batches = rows_batches[:1]
            cluster_sizes_list = cluster_sizes_list[:1]
            clusters_dict_list = clusters_dict_list[:1]
            ml_columns_list = ml_columns_list[:1]

        # Parallel processing of rows in batches
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(tqdm(executor.map(process_batch, rows_batches, cluster_sizes_list, clusters_dict_list, ml_columns_list, [vectorizer] * len(rows_batches)),
                                total=len(rows_batches), desc="Processing batches"))

        # Flatten the results list and filter out None values
        results_list = [item for sublist in results for item in sublist if item is not None] 
        results_df = pd.DataFrame(results_list)
        
        # Add hyperlinks to the results DataFrame
        results_df = add_hyperlink_column(results_df, URL, ID_COLUMN)

        # Save the results
        output_path = OUTPUT_FILENAME
        results_df.to_csv(output_path, index=False)
        logging.info(f"Results saved to: {output_path}")

    except Exception as e:
        logging.error(f"Script execution failed: {str(e)}")

if __name__ == "__main__":
 #   profiler = cProfile.Profile()
 #   profiler.enable()
    main()
 #   profiler.disable()
 #   profiler.print_stats(sort="cumulative")
