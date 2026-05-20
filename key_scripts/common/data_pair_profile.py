import pandas as pd

def read_csv(file_path):
    """Reads a CSV file into a pandas DataFrame."""
    return pd.read_csv(file_path)

def analyze_column(column):
    """Analyzes a single column of a DataFrame."""
    return {
        'unique_values': column.nunique(),
        'most_common_value': column.value_counts().idxmax(),
        'most_common_value_count': column.value_counts().max(),
        'total_count': len(column)
    }

def profile_data(df):
    """Profiles each column in the DataFrame."""
    return {col: analyze_column(df[col]) for col in df.columns}

def identify_columns_for_grouping(data_profile, threshold=0.5):
    """Identifies columns for pre-grouping based on the threshold."""
    return [col for col, stats in data_profile.items() if stats['most_common_value_count'] / stats['total_count'] > threshold]

def analyze_correlations(df, columns_to_group):
    """Performs correlation analysis between columns."""
    correlated_pairs = []
    for col in columns_to_group:
        for other_col in df.columns:
            if col != other_col and df[col].equals(df[other_col]):
                correlated_pairs.append((col, other_col))
    return correlated_pairs

# Example Usage for Chunk-Based Processing with Output to CSV
file_path = './input/test.csv'
df = read_csv(file_path)

data_profile = profile_data(df)
columns_to_pre_group = identify_columns_for_grouping(data_profile)
correlated_column_pairs = analyze_correlations(df, columns_to_pre_group)

# Saving Data Profile to CSV
data_profile_df = pd.DataFrame.from_dict(data_profile, orient='index')
data_profile_df.to_csv('./output/data_profile_pair.csv', index_label='Column')

# Saving Columns to Pre-Group to CSV
columns_to_pre_group_df = pd.DataFrame(columns_to_pre_group, columns=['Column'])
columns_to_pre_group_df.to_csv('./output/columns_to_pre_group_pair.csv', index=False)

# Saving Correlated Column Pairs to CSV
correlated_column_pairs_df = pd.DataFrame(correlated_column_pairs, columns=['Column A', 'Column B'])
correlated_column_pairs_df.to_csv('./output/correlated_column_pairs.csv', index=False)