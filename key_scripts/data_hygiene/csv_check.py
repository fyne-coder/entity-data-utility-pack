import csv

def check_csv_format_and_save_results(input_file_path, output_file_path):
    with open(input_file_path, 'r', encoding='utf-8', errors='replace') as input_file, \
         open(output_file_path, 'w', encoding='utf-8') as output_file:

        reader = csv.reader(input_file)
        column_count = None
        has_error = False

        for i, row in enumerate(reader, start=1):
            if column_count is None:
                column_count = len(row)
            elif len(row) != column_count:
                output_file.write(f"Row {i}: Inconsistent number of columns. Expected {column_count}, Found {len(row)}\n")
                has_error = True

            # Check each field for \n and \r characters
            for field in row:
                if '\n' in field or '\r' in field:
                    output_file.write(f"Row {i}: Contains newline or carriage return in field '{field}'\n")
                    has_error = True

        if has_error:
            print(f"Errors found. Details saved to {output_file_path}")
        else:
            print("No errors found in CSV format.")

try:
    # Replace with your actual file paths
    check_csv_format_and_save_results('ibm_upload.csv', 'csv_format_results.txt')
except UnicodeDecodeError as e:
    with open('csv_format_results.txt', 'w', encoding='utf-8') as output_file:
        output_file.write(f"File contains characters not supported in UTF-8. Error: {e}\n")
        print("Errors found. Details saved to csv_format_results.txt")
