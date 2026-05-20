import csv
import io

def find_non_utf8_and_line_breaks(input_file, output_file, log_file):
    line_break_in_column = False
    contains_escaped_quotes = {'""': False, '\\"': False}
    error_log = []
    nul_byte_log = []  # List to keep track of lines with NUL bytes and their content

    with io.open(input_file, 'r', encoding='utf-8', errors='ignore') as infile, \
         io.open(output_file, 'w', encoding='utf-8') as outfile, \
         io.open(log_file, 'w', encoding='utf-8') as logf:

        for line_number, line in enumerate(infile, 1):
            original_line = line
            # Check for NUL characters, log them, and then remove them
            if '\0' in line:
                nul_byte_log.append((line_number, original_line.strip().replace('\0', '\\0')))
                line = line.replace('\0', '')

            # Check if replacement character is present, indicating a non-UTF-8 character
            if '�' in line:
                error_log.append((line_number, original_line.strip()))

            # Replace the invalid character
            line = line.replace('�', '')

            try:
                row = next(csv.reader([line]))
            except csv.Error as e:
                logf.write(f"CSV parsing error on line {line_number}: {e}\n")
                continue

            for field in row:
                if '\n' in field or '\r' in field:
                    line_break_in_column = True
                    logf.write(f"Line break found in column on line {line_number}\n")

                if '""' in field:
                    contains_escaped_quotes['""'] = True
                if '\\"' in field:
                    contains_escaped_quotes['\\"'] = True

            # Write the corrected line to the output file
            outfile.write(line)

        # Output results to log file
        if line_break_in_column or contains_escaped_quotes['""'] or contains_escaped_quotes['\\"']:
            logf.write("Issues found in file:\n")
            if line_break_in_column:
                logf.write("File contains line breaks within column values\n")
            for quote, found in contains_escaped_quotes.items():
                if found:
                    logf.write(f"File contains escaped quotes using {quote}\n")
        else:
            logf.write("No issues found in file regarding line breaks or escaped quotes.\n")

        if error_log:
            logf.write("Invalid UTF-8 sequences found on the following lines:\n")
            for line_num, line_content in error_log:
                logf.write(f"Line {line_num}: {line_content}\n")

        if nul_byte_log:
            logf.write("NUL bytes found on the following lines and their content before removal:\n")
            for line_num, line_content in nul_byte_log:
                logf.write(f"Line {line_num}: {line_content}\n")
        else:
            logf.write("No NUL bytes found.\n")

# Example usage
find_non_utf8_and_line_breaks('ibm_upload.csv', 'latest_ibm_upload.csv', 'error_log.txt')
