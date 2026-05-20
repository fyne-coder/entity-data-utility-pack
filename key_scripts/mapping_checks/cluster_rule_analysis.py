import csv

# Define clustering rules
def rule_id_1_non_matching(record_a, record_b):
    return record_a['Rule_ID_1'] != record_b['Rule_ID_1'] and record_a['Rule_ID_1'] and record_b['Rule_ID_1']

def trusted_id_non_matching(record_a, record_b):
    return record_a['trusted_id'] != record_b['trusted_id'] and record_a['trusted_id'] and record_b['trusted_id']

def rule_id_1_matching(record_a, record_b):
    return record_a['Rule_ID_1'] == record_b['Rule_ID_1']

def trusted_id_matching(record_a, record_b):
    return record_a['trusted_id'] == record_b['trusted_id']

def rule_id_2_matching(record_a, record_b):
    return record_a['Rule_ID_2'] == record_b['Rule_ID_2']

# Settings for clustering rules
rule_settings = {
    "rule_id_1_non_matching": True,
    "trusted_id_non_matching": True,
    "rule_id_1_matching": True,
    "trusted_id_matching": True,
    "rule_id_2_matching": True
}

# Function to get active rules based on settings
def get_active_rules():
    rules = []
    if rule_settings["rule_id_1_non_matching"]:
        rules.append(rule_id_1_non_matching)
    if rule_settings["trusted_id_non_matching"]:
        rules.append(trusted_id_non_matching)
    if rule_settings["rule_id_1_matching"]:
        rules.append(rule_id_1_matching)
    if rule_settings["trusted_id_matching"]:
        rules.append(trusted_id_matching)
    if rule_settings["rule_id_2_matching"]:
        rules.append(rule_id_2_matching)
    return rules

# Read CSV function
def read_csv(file_path):
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)

def write_rules_summary_to_csv(rules, filename='rules_summary.csv'):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Rule Name', 'Description'])
        for rule in rules:
            # The description should be a simple explanation of the rule
            description = "A brief description of what the rule does."
            writer.writerow([rule.__name__, description])

# Extract IDs function
def extract_ids(rows):
    trusted_ids = set()
    rule_ids_1 = set()
    rule_ids_2 = set()

    for row in rows:
        trusted_ids.add(row['trusted_id'])
        rule_ids_1.add(row['Rule_ID_1'])
        rule_ids_2.add(row['Rule_ID_2'])

    return trusted_ids, rule_ids_1, rule_ids_2

# Generate insights function
def generate_insights(clusters, clustering_rules):
    insights = {}
    for cluster_id, records in clusters.items():
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                for rule in clustering_rules:
                    if rule(records[i], records[j]):
                        record_i_row = records[i]['RowNum']
                        record_j_row = records[j]['RowNum']
                        insights.setdefault(cluster_id, []).append(
                            (record_i_row, record_j_row, rule.__name__))
                        break
    return insights

# Analyze clusters function
def analyze_clusters(data):
    clusters = {}
    for row_num, row in enumerate(data):
        cluster_id = row["suggestedClusterId"]
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        row_with_num = row.copy()
        row_with_num['RowNum'] = row_num
        clusters[cluster_id].append(row_with_num)
    return clusters

# Function to write insights to CSV
def write_detailed_clustering_to_csv(insights, filename='insights_output.csv'):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ClusterId', 'Record1_Row', 'Record2_Row', 'RuleApplied', 'Outcome'])
        for cluster_id, rules in insights.items():
            for rule in rules:
                record1, record2, rule_name = rule
                outcome = "Clustered" if "matching" in rule_name else "Not Clustered"
                writer.writerow([cluster_id, record1, record2, rule_name, outcome])

# Updated Main function
def main():
    file_path = 'output.csv'
    data = read_csv(file_path)

    clustering_rules = get_active_rules()
    
    # Write rules summary to CSV
    write_rules_summary_to_csv(clustering_rules)
    
    clusters = analyze_clusters(data)
    insights = generate_insights(clusters, clustering_rules)

    # Save detailed clustering insights to a CSV file
    write_detailed_clustering_to_csv(insights)

    # Output insights to the console, if needed
    for cluster_id, rules in insights.items():
        print(f"Cluster {cluster_id}:")
        for rule in rules:
            record1, record2, rule_name = rule
            print(f"  Record {record1} and Record {record2}: {rule_name}")

if __name__ == "__main__":
    main()