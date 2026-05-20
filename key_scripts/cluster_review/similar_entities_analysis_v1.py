import os
import pandas as pd
import numpy as np
import logging
import concurrent.futures
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import warnings

# Constants
DATA_DIR = "data"
OUTPUT_FILENAME = "similar_cluster_analysis.csv"
ML_PREFIX = "ml_"
URL = "https://example.com/entities/"  # Replace with your URL
ID_COLUMN = "clusterId1"  # Replace with the appropriate ID column name

# Setup logging
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.feature_extraction.text", message="The parameter 'token_pattern' will not be used since 'tokenizer' is not None'")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def add_hyperlink_column(df: pd.DataFrame, url: str, id_col: str) -> pd.DataFrame:
    """Add a new hyperlink column to the dataframe."""
    hyperlinks = [f'=HYPERLINK("{url}{df[id_col].iloc[i]}?tab=Manage+Cluster+Details")' for i in range(len(df))]
    df.insert(0, 'Hyperlink', hyperlinks)
    return df

def load_data(data_dir: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and return cluster details and similarities data."""
    try:
        files = os.listdir(data_dir)
        cluster_similarities_file = next(file for file in files if "cluster_similarities" in file)
        cluster_details_file = next(file for file in files if "cluster_details" in file)

        cluster_details_df = pd.read_csv(os.path.join(data_dir, cluster_details_file))
        cluster_similarities_df = pd.read_csv(os.path.join(data_dir, cluster_similarities_file))
        
        return cluster_details_df, cluster_similarities_df
    except Exception as e:
        logging.error(f"Error loading data: {str(e)}")
        raise

def custom_tokenizer(s):
    """Custom tokenizer that treats single characters as valid tokens."""
    return s.split()

def calculate_centroid_similarity(cluster1: pd.DataFrame, cluster2: pd.DataFrame, column_name: str) -> float:
    """Calculate and return the centroid similarity between two clusters based on the specified column."""
    combined_texts = pd.concat([cluster1, cluster2])[column_name].astype(str).replace({"nan": "", "None": ""}).values
    if not any(combined_texts):
        logging.warning("No valid vocabulary in combined_texts.")
        return 0

    # Handle gender column differently
    if column_name == "ml_gender":
        vectorizer = TfidfVectorizer(lowercase=True, tokenizer=custom_tokenizer, stop_words=None)
    else:
        vectorizer = TfidfVectorizer()

    try:
        vectorizer = vectorizer.fit(combined_texts)
        vectors = vectorizer.transform(combined_texts).toarray()
        centroid1 = np.mean(vectors[:len(cluster1)], axis=0)
        centroid2 = np.mean(vectors[len(cluster1):], axis=0)
        similarity = cosine_similarity([centroid1], [centroid2])[0, 0]
    except ValueError as e:
        logging.warning(f"Warning: {str(e)}")
        similarity = 0
    
    return similarity



def calculate_pair_similarity(args) -> tuple[tuple[str, str], dict[str, float]]:
    row, details_df, ml_columns = args
    cluster_id1, cluster_id2 = row['clusterId1'], row['clusterId2']
    rows_cluster1 = details_df[details_df['persistentId'] == cluster_id1]
    rows_cluster2 = details_df[details_df['persistentId'] == cluster_id2]
    pair_similarities = {}
    
    for col in ml_columns:
        all_empty_cluster1 = all(pd.isna(val) or str(val).strip() == "" for val in rows_cluster1[col])
        all_empty_cluster2 = all(pd.isna(val) or str(val).strip() == "" for val in rows_cluster2[col])
        if all_empty_cluster1 and all_empty_cluster2:
            pair_similarities[col] = "NA"
            continue
        similarity = calculate_centroid_similarity(rows_cluster1, rows_cluster2, col)
        pair_similarities[col] = similarity
    
    return (cluster_id1, cluster_id2), pair_similarities


def calculate_similarities(details_df: pd.DataFrame, similarities_df: pd.DataFrame, ml_prefix: str) -> pd.DataFrame:
    """..."""  # Previous docstring here
    
    ml_columns = [col for col in details_df.columns if col.startswith(ml_prefix)]
    
    with concurrent.futures.ProcessPoolExecutor() as executor:
        args = [(row, details_df, ml_columns) for _, row in similarities_df.iterrows()]
        results = executor.map(calculate_pair_similarity, args)
    
    columnwise_similarities = dict(results)
    columnwise_similarities_df = pd.DataFrame.from_dict(columnwise_similarities, orient='index')
    columnwise_similarities_df['clusterId1'], columnwise_similarities_df['clusterId2'] = zip(*columnwise_similarities_df.index)

    return columnwise_similarities_df

def add_additional_columns(columnwise_similarities_df: pd.DataFrame, details_df: pd.DataFrame, similarities_df: pd.DataFrame) -> pd.DataFrame:
    """Add additional columns to the results dataframe."""
    columnwise_similarities_df['count_clusterId1'] = columnwise_similarities_df['clusterId1'].apply(lambda x: details_df[details_df['persistentId'] == x].shape[0])
    columnwise_similarities_df['count_clusterId2'] = columnwise_similarities_df['clusterId2'].apply(lambda x: details_df[details_df['persistentId'] == x].shape[0])
    columnwise_similarities_df = columnwise_similarities_df.merge(similarities_df[['clusterId1', 'clusterId2', 'clusterPairSimilarity']], on=['clusterId1', 'clusterId2'], how='left')

    # Reorder columns
    desired_order = ['clusterId1', 'clusterId2', 'count_clusterId1', 'count_clusterId2', 'clusterPairSimilarity']
    other_columns = [col for col in columnwise_similarities_df.columns if col not in desired_order]
    new_column_order = desired_order + other_columns

    return columnwise_similarities_df[new_column_order]


def save_results(results_df: pd.DataFrame, output_path: str):
    """Save the results dataframe to a CSV file."""
    try:
        results_df.to_csv(output_path, index=False)
        logging.info(f"Results saved to: {output_path}")
    except Exception as e:
        logging.error(f"Error saving results: {str(e)}")
        raise


def main():
    """Main function to execute the script."""
    try:
        cluster_details_df, cluster_similarities_df = load_data(DATA_DIR)
        columnwise_similarities_df = calculate_similarities(cluster_details_df, cluster_similarities_df, ML_PREFIX)
        columnwise_similarities_df = add_additional_columns(columnwise_similarities_df, cluster_details_df, cluster_similarities_df)
        
        # Add hyperlinks using the constants
        columnwise_similarities_df = add_hyperlink_column(columnwise_similarities_df, URL, ID_COLUMN)
        
        save_results(columnwise_similarities_df, os.path.join(DATA_DIR, OUTPUT_FILENAME))
    except Exception as e:
        logging.error(f"Script execution failed: {str(e)}")

if __name__ == "__main__":
    main()
