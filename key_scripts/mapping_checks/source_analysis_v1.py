import pandas as pd

def add_hyperlink_column(df, url, id_col):
    """Add a new hyperlink column to the dataframe."""
    hyperlinks = [f'=HYPERLINK("{url}{df[id_col].iloc[i]}")' for i in range(len(df))]
    df['Hyperlink'] = hyperlinks
    return df

def analyze_data(filename, field_a, field_b, filter_value=None, hyperlink_template=None):
    # Load data
    data = pd.read_csv(filename)
    
    # Optionally filter rows where Field A contains a configured value.
    filtered_data = data
    if filter_value:
        filtered_data = data[data[field_a].str.contains(filter_value, na=False)]

    # Group by Field B and count unique values in Field A
    mapping_counts = filtered_data.groupby(field_b)[field_a].nunique()
    
    # Filter and get only those Field B values that have multiple unique values in Field A
    multiple_mapped_values = mapping_counts[mapping_counts > 1]

    # Filter the dataframe to only include these values
    result_df = filtered_data[filtered_data[field_b].isin(multiple_mapped_values.index)].drop_duplicates(subset=field_b)

    # Add hyperlink column
    url_pattern = hyperlink_template or "https://example.com/entities/"
    result_df = add_hyperlink_column(result_df, url_pattern, field_b)

    # Filter to only have required columns and rename columns
    result_df = result_df[['Hyperlink', field_b]]
    result_df['Count'] = result_df[field_b].map(multiple_mapped_values)
    
    # Save to CSV
    result_df.to_csv('output_with_hyperlinks.csv', index=False)

if __name__ == "__main__":
    filename = input("Enter the file name: ")
    field_a = input("Enter Field A: ")
    field_b = input("Enter Field B: ")
    filter_value = input("Optional Field A filter value: ").strip() or None
    hyperlink_template = input("Optional hyperlink URL prefix: ").strip() or None

    analyze_data(filename, field_a, field_b, filter_value, hyperlink_template)
