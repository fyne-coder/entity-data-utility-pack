import pandas as pd
import json
import os
import glob
from datetime import datetime
from weasyprint import HTML

def read_csv(file_path):
    """Reads a CSV file into a pandas DataFrame."""
    return pd.read_csv(file_path, low_memory=False)

def analyze_column(column, numeric_dummy_values, date_dummy_values, generic_dummy_values):
    """Analyzes a single column of a DataFrame."""
    # Convert to string and lower case for consistent dummy value matching
    column_as_str = column.astype(str).str.lower()

    analysis = {
        'total_values': len(column),
        'unique_values': column.nunique(),
        'top_10_common_values': column.value_counts().head(10).to_dict(),
        'null_values': column.isnull().sum(),
        'blank_values': (column == '').sum()
    }

    # Check for numeric dummy values if column is numeric
    if pd.api.types.is_numeric_dtype(column):
        analysis['numeric_dummy_values'] = column[column.isin(numeric_dummy_values)].count()
        analysis['top_5_numeric_dummy_values'] = column[column.isin(numeric_dummy_values)].value_counts().head(5).to_dict()

    # Check for date dummy values if column is a date
    if pd.api.types.is_datetime64_any_dtype(column):
        analysis['date_dummy_values'] = sum(column.isin(date_dummy_values))
        analysis['top_5_date_dummy_values'] = column[column.isin(date_dummy_values)].value_counts().head(5).to_dict()

    # Check for generic dummy text values
    analysis['text_dummy_values'] = column_as_str.isin(generic_dummy_values).sum()
    analysis['top_5_text_dummy_values'] = column_as_str[column_as_str.isin(generic_dummy_values)].value_counts().head(5).to_dict()

    # Check for sequential identifiers or standardized codes (assuming they are strings)
    if column.dtype == object:
        sequential_dummy = column_as_str.str.match(r'^0+$').sum()
        analysis['sequential_dummy_values'] = sequential_dummy
        if sequential_dummy > 0:
            analysis['top_5_sequential_dummy_values'] = column[column_as_str.str.match(r'^0+$')].value_counts().head(5).to_dict()

    return analysis

def profile_data(df):
    """Profiles the data in a DataFrame."""
    # Define dummy values for numeric and date columns
    numeric_dummy_values = [0, -1]
    date_dummy_values = [datetime(1900, 1, 1), datetime(9999, 12, 31)]
    generic_dummy_values = ['null', 'n/a', 'na', 'none', 'undefined', 'unknown', 'test', 'sample']
    
    profile = {}
    for col in df.columns:
        profile[col] = analyze_column(df[col], numeric_dummy_values, date_dummy_values, generic_dummy_values)
    return profile

def generate_html_report(data, output_html_path):
    """Generates a detailed HTML report with sections for each column."""
    html_content = '''
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
            .column-section { margin-bottom: 20px; }
            .column-header { background-color: #4CAF50; color: white; padding: 10px; }
            .column-data { background-color: #f2f2f2; padding: 5px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
    '''

    for col_data in data:
        col_name = col_data['Column']
        total_values = col_data['total_values']
        html_content += f'<div class="column-section">'
        html_content += f'<div class="column-header">{col_name}</div>'
        html_content += '<table class="column-data">'
        
        # Total values
        html_content += f'<tr><td>Total values</td><td>{total_values:,}</td></tr>'
        
        # Unique values and percentages
        unique_values = col_data['unique_values']
        unique_percentage = (unique_values / total_values * 100) if total_values else 0
        html_content += f'<tr><td>Unique values</td><td>{unique_values:,} ({unique_percentage:.2f}%)</td></tr>'

        # Numeric values with percentages
        for key in ['null_values', 'blank_values', 'text_dummy_values', 'sequential_dummy_values']:
            if key in col_data:
                value = col_data[key]
                percentage = (value / total_values * 100) if total_values else 0
                html_content += f'<tr><td>{key.replace("_", " ").capitalize()}</td><td>{value:,} ({percentage:.2f}%)</td></tr>'

        # Top common values and dummy value lists
        for key in ['top_10_common_values', 'top_5_text_dummy_values', 'top_5_sequential_dummy_values']:
            if key in col_data and isinstance(col_data[key], str):
                value_dict = json.loads(col_data[key])
                formatted_values = ', '.join([f"{k}: {v:,}" for k, v in value_dict.items()])
                html_content += f'<tr><td>{key.replace("_", " ").capitalize()}</td><td>{formatted_values}</td></tr>'

        html_content += '</table></div>'

    html_content += '</body></html>'

    with open(output_html_path, 'w') as file:
        file.write(html_content)

def save_output(data, base_filename, output_dir, format='csv'):
    """Saves the output data to files in the specified formats."""
    file_path_csv = os.path.join(output_dir, f"{base_filename}.csv")

    # Convert the dictionaries to JSON strings for CSV output only
    for col_data in data:
        for key in ['top_10_common_values', 'top_5_text_dummy_values', 'top_5_sequential_dummy_values']:
            if key in col_data and isinstance(col_data[key], dict):
                col_data[key] = json.dumps(col_data[key])

    # Save the CSV file
    if format == 'csv':
        df_to_save = pd.DataFrame(data)
        df_to_save.to_csv(file_path_csv, index=False)

    # Generate HTML and PDF reports without converting dictionaries to JSON strings
    file_path_html = os.path.join(output_dir, f"{base_filename}.html")
    generate_html_report(data, file_path_html)
    HTML(file_path_html).write_pdf(os.path.join(output_dir, f"{base_filename}.pdf"))

# Example Usage
input_dir = './input'  # Replace with your input directory path
output_dir = './output'  # Replace with your output directory path

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Process all CSV files in the input directory
for input_file in glob.glob(os.path.join(input_dir, '*.csv')):
    base_filename = os.path.splitext(os.path.basename(input_file))[0]
    df = read_csv(input_file)
    data_profile = profile_data(df)

    # Flatten the data for CSV, HTML, and PDF output
    flattened_data = []
    for col_name, col_data in data_profile.items():
        row_data = {'Column': col_name}
        for key, value in col_data.items():
            if isinstance(value, dict):
                # Convert dictionaries to a string representation
                row_data[key] = json.dumps(value)
            else:
                row_data[key] = value
        flattened_data.append(row_data)

    save_output(flattened_data, base_filename, output_dir)

print("Data profiling complete. Check the output directory for CSV, HTML, and PDF files.")
