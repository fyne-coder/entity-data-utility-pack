import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import warnings
import shutil
import glob
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s]: %(message)s',
                    handlers=[logging.FileHandler("debug.log"),
                              logging.StreamHandler()])

logging.info('Script started')

def load_data(file_path):
    logging.info('Loading data from: ' + file_path)
    pd_data = pd.read_csv(file_path, low_memory=False)
    pd_data = pd_data.astype(str)
    logging.info(f"Loaded data with shape: {pd_data.shape}")
    return pd_data

"""Load data from a CSV file and return it as a pandas DataFrame."""   
def load_data(file_path):
    
    # Load data using pandas
    pd_data = pd.read_csv(file_path, low_memory=False)

    # Convert all columns to string type
    pd_data = pd_data.astype(str)

    return pd_data


def plot_distribution(cluster_distribution_pd, output_dir):
    cluster_distribution_pd.to_csv(os.path.join(output_dir, 'cluster_distribution.csv'), index=False)

    bins = [0, 1, 5, 10, 25, 50, 100, 250, 500, np.inf]
    labels = ['1', '2-5', '6-10', '11-25', '26-50', '51-100', '101-250', '251-500', '500+']

    cluster_distribution_pd['group'] = pd.cut(cluster_distribution_pd['count'], bins=bins, labels=labels)
    grouped = cluster_distribution_pd.groupby('group').size()[::-1]

    plt.figure(figsize=(10, 6))
    bars = plt.barh(grouped.index, grouped.values, color='skyblue', edgecolor='black')

    plt.ylabel('Number of Records per Cluster')
    plt.xlabel('Number of Clusters')
    plt.title('Cluster Distribution by persistentId')
    plt.grid(True)

    plt.xscale('log')  # Set the scale of the x-axis to logarithmic

    def format_func(value, tick_number):
        # find number of multiples of 10
        N = int(np.log10(value))
        if N < 3:
            # use integer format if value < 1000
            return "{:,}".format(int(value))
        elif N == 3:
            # use K format if value >= 1000
            return "{:.1f}k".format(value / 1000)
        elif N == 6:
            # use M format if value >= 1,000,000
            return "{:.1f}M".format(value / 1_000_000)
        elif N == 9:
            # use G format if value >= 1,000,000,000
            return "{:.1f}G".format(value / 1_000_000_000)
        else:
            # use scientific notation for any other case
            return "{:.0e}".format(value)

    plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(format_func))

    for bar in bars:
        yval = bar.get_width()
        if yval > 0:
            if yval > 1000:
                yval_label = f"{yval / 1000:.1f}k"
            else:
                yval_label = str(int(yval))
            plt.text(
                yval + 5, bar.get_y() + bar.get_height() / 2, yval_label, va='center', fontweight='bold')

    plt.savefig(os.path.join(output_dir, 'cluster_distribution.png'))
    plt.close()


def calculate_match_scores(df, important_fields):
    if 'persistentId' in important_fields:
        important_fields.remove('persistentId')

    ml_fields = [field for field in important_fields if field.startswith('ml_')]

    df_with_match_scores = df[['persistentId'] + important_fields].copy()

    for field in ml_fields:
        df_with_match_scores[field + '_match'] = (df_with_match_scores[field] == '1').astype(int)
    
    ml_fields_match = [field + '_match' for field in ml_fields]  # Add '_match' suffix

    df_with_match_scores[ml_fields_match] = df_with_match_scores[ml_fields].apply(pd.to_numeric, errors='coerce')

    df_with_match_scores['match_score'] = df_with_match_scores[ml_fields_match].mean(axis=1)

    return df_with_match_scores[['persistentId'] + ml_fields_match + ['match_score']]


def plot_histogram(not_perfect_matches, output_dir):
    not_perfect_matches.to_csv(os.path.join(output_dir, 'histogram.csv'), index=False)

    bins = np.linspace(0, 1, 21)
    counts, _ = np.histogram(not_perfect_matches['match_score'], bins=bins)

    plt.figure(figsize=(12, 8))
    bars = plt.bar(bins[:-1], counts, width=(bins[1] - bins[0]) * 0.9, color='skyblue', edgecolor='black', log=True)

    for bar in bars:
        yval = bar.get_height()
        if yval > 0:
            if yval > 1000:
                yval_label = f"{yval / 1000:.1f}K"
            else:
                yval_label = str(int(yval))
            plt.text(bar.get_x() + bar.get_width() / 2, yval + 5, yval_label, ha='center', va='bottom', fontweight='bold')

    plt.title('Histogram of Match Score (Log Scale)', fontsize=16)
    plt.xlabel('Match Score', fontsize=14)
    plt.ylabel('Frequency (Log Scale)', fontsize=14)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.grid(True, which="both", ls="-", color='0.7')

    plt.savefig(os.path.join(output_dir, 'histogram.png'))
    plt.close()


def plot_field_averages(match_scores, important_fields, output_dir):
    ml_fields = [field for field in important_fields if field.startswith('ml_')]
    ml_fields_match = [field + '_match' for field in ml_fields]  # Add '_match' suffix

    field_averages = match_scores[ml_fields_match].mean().reset_index()
    field_averages.columns = ['Field', 'Average']

    plt.figure(figsize=(12, 8))
    field_averages.plot(x='Field', y='Average', kind='bar', alpha=0.7)
    plt.xlabel('ML Field')
    plt.ylabel('Match Score')
    plt.title('Average Match Score per ML Field')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the plot
    plt.savefig(os.path.join(output_dir, 'field_averages.png'))
    plt.close()  # Close the plot without displaying

def main():
    input_dir = 'input'
    output_dir_base = 'output'
    output_dirs = []

    # Extract important_fields from first file only, assuming all files have the same schema
    important_fields = None

    for input_file in os.listdir(input_dir):
        if input_file.endswith('.csv'):
            # Create a new directory for each input file
            output_dir = os.path.join(output_dir_base, os.path.splitext(input_file)[0])
            os.makedirs(output_dir, exist_ok=True)
            output_dirs.append(output_dir)  # Keep track of the created directories

            data = load_data(os.path.join(input_dir, input_file))
            cluster_distribution = data['persistentId'].value_counts().reset_index()
            cluster_distribution.columns = ['persistentId', 'count']
            cluster_distribution_pd = cluster_distribution.copy()

            plot_distribution(cluster_distribution_pd, output_dir)

            filtered_data = cluster_distribution[cluster_distribution['count'] > 1]
            data = pd.merge(data, filtered_data, on='persistentId', how='inner')

            # Only extract important_fields for the first file
            if important_fields is None:
                important_fields = data.columns.tolist()
                important_fields.remove('persistentId')  # Remove 'persistentId' from the list
                important_fields = [str(field) for field in important_fields]

            important_fields_with_pid = important_fields + ['persistentId']
            data[important_fields_with_pid].to_csv(
                os.path.join(output_dir, 'important_fields_data.csv'), index=False
            )

            match_scores = calculate_match_scores(data, important_fields_with_pid)

            match_scores_sorted = match_scores[['persistentId'] + ['match_score']]

            match_scores.to_csv(os.path.join(output_dir, 'match_scores_sorted.csv'), index=False)

            not_perfect_matches = match_scores[match_scores['match_score'] <= 1]
            print('Not perfect match count:', len(not_perfect_matches))
            not_perfect_matches_pd = not_perfect_matches.copy()

            plot_histogram(not_perfect_matches_pd, output_dir)
            plot_field_averages(match_scores, important_fields_with_pid, output_dir)  # Pass important_fields_with_pid

            cluster_distribution_pd.to_csv(os.path.join(output_dir, 'cluster_distribution.csv'), index=False)
            not_perfect_matches_pd.to_csv(os.path.join(output_dir, 'histogram.csv'), index=False)

    return output_dirs, important_fields


def analyze_clusters(input_dir):
    logging.info(f'Analyzing clusters for directory: {input_dir}')
    
    # Load the data
    df = pd.read_csv(os.path.join(input_dir, 'histogram.csv'))
    cluster_distribution_df = pd.read_csv(os.path.join(input_dir, 'cluster_distribution.csv'))
    match_scores = pd.read_csv(os.path.join(input_dir, 'match_scores_sorted.csv'))

    logging.info(f"histogram.csv shape: {df.shape}")
    logging.info(f"cluster_distribution.csv shape: {cluster_distribution_df.shape}")
    logging.info(f"match_scores_sorted.csv shape: {match_scores.shape}")
    
    # Merge the original data with the cluster distribution data
    merged_df = match_scores.merge(cluster_distribution_df[['persistentId', 'count']], on='persistentId', how='inner')
    logging.info(f"Merged DataFrame shape: {merged_df.shape}")
    
    # Identify the clusters that are significantly larger than the average cluster size
    average_cluster_size = merged_df['count'].mean()
    large_clusters = merged_df[merged_df['count'] > average_cluster_size]

    # From these large clusters, identify those with a low match score
    low_match_score_threshold = 0.8  # This threshold can be adjusted based on your specific needs
    large_clusters_with_low_match_score = large_clusters[large_clusters['match_score'] < low_match_score_threshold]

    # Sort the clusters by size in descending order
    large_clusters_with_low_match_score_sorted = large_clusters_with_low_match_score.sort_values(
        by='count', ascending=False)

    # Save the sorted list of clusters to a CSV file
    large_clusters_with_low_match_score_sorted.to_csv(
        os.path.join(input_dir, 'sort_clusters_to_evaluate.csv'), index=False)

    # Plot the size and match score of the top 5 clusters
    if not large_clusters_with_low_match_score_sorted.empty:
        large_clusters_with_low_match_score_sorted.head(5).set_index('persistentId')[['count', 'match_score']].plot(
            kind='bar', secondary_y='match_score', figsize=(10, 6))
        plt.title('Top 5 Clusters to Evaluate')
        plt.xlabel('Cluster ID')
        plt.ylabel('Cluster Size')
        plt.savefig(os.path.join(input_dir, 'top_clusters_to_evaluate.png'))
        plt.close()  # Close the plot without displaying
    else:
        logging.warning('No clusters found that match the criteria for plotting.')


if __name__ == '__main__':
    logging.info("Main execution started")
    output_dirs, important_fields = main()
    for output_dir in output_dirs:
        analyze_clusters(output_dir)

    if not os.path.exists('processed'):
        os.makedirs('processed')

    for input_file in glob.glob("input/*.csv"):
        shutil.move(input_file, 'processed/')
        logging.info(f"Moved {input_file} to processed directory")
    logging.info("Main execution completed")