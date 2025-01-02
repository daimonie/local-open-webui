import requests
import click
import os
import time
import polars as pl
import glob
from lib.prompt import simple_api, get_header, PromptException

class PromptException(Exception):
    pass

@click.group()
def cli():
    """CLI interface for bank data processing"""
    pass

@cli.command()
def load():
    """Get a sample of the bank data"""
    try:
        print("Sampling bank data...")

        # Get list of CSV files in bankdata directory
        csv_files = glob.glob("bankdata/*.csv")
        
        # Initialize empty dict to store dataframes
        dataframes = {}
        
        for file_path in csv_files:
            # Read CSV into polars dataframe
            # Read CSV without headers and apply column mapping directly
            df = pl.read_csv(file_path, has_header=False)

            column_names = [f"col{i+1}" for i in range(len(df.columns))]
            column_names[0] = "date"
            column_names[1] = "from_banknr"
            column_names[2] = "to_banknr"
            column_names[3] = "from_name"
            column_names[14] = "merchant"
            column_names[8] = "balance_before"
            column_names[10] = "amount"
            column_names[17] = "desc"

            col_mapping = {
                df.columns[i]: name
                for i, name in enumerate(column_names)
            }
            # Rename columns using the mapping
            df = df.rename(col_mapping)

            # Get list of columns to keep (the named ones)
            cols_to_keep = [col for col in df.columns if not col.startswith("col")]
            
            # Select only the named columns
            df = df.select(cols_to_keep)
            # Extract bank account from filename
            bank_account = os.path.basename(file_path).split('-')[0]
            # Add bank_account as a new column
            df = df.with_columns(pl.lit(bank_account).alias("bank_account"))

            # Store dataframe and mapping
            file_name = os.path.basename(file_path)
            dataframes[file_name] = {
                "df": df,
                "mapping": col_mapping
            } 
        
        # Merge all dataframes together
        merged_df = None
        for file_name, data in dataframes.items():
            df = data["df"]
            if merged_df is None:
                merged_df = df
            else:
                merged_df = pl.concat([merged_df, df])
        
        print("\nMerged dataframe:")
        print(merged_df.head())
        print(f"\nTotal rows: {merged_df.height}")

        # Save merged dataframe to CSV
        output_path = os.path.join('bankdata', 'ingested.csv')
        merged_df.write_csv(output_path)
        print(f"\nSaved merged data to {output_path}")
    except Exception as e:
        raise PromptException(f"Error sampling data: {str(e)}")

def call_api(full_prompt, model="phi3:14b"):    
    url = 'http://open-webui:8080/api/chat/completions'
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": full_prompt}],
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 1.0
    }

    response = simple_api(url, method='POST', payload=payload)
    
    if 'choices' in response and len(response['choices']) > 0:
        return response['choices'][0]['message']['content']
    else:
        raise PromptException("Did not get a recognised response from API")


def parse_response(response, categories):
    """Parse the response from the API to extract the category.
    
    Args:
        response (str): The API response text
        categories (list): List of valid categories
        
    Returns:
        str: The matched category or 'debit' if no match found
    """
    # Convert response to lowercase for case-insensitive matching
    response_lower = response.lower()
    
    # Check if any category appears in the response
    for category in categories:
        if category.lower() in response_lower:
            return category
            
    return "debit"


def map_to_categories(from_name, desc):
    
    categories = [
        'Salary',
        'credit', 
        'debit',
        'mortgage',
        'groceries',
        'student debt',
        'donations', 
        'health insurance',
        'travel',
        'sports',
        'phone',
        'media subscriptions',
        'savings',
        'utilities',
        'frivolous', 
        "medical expenses",
        "plants"
    ]


    full_prompt = f"""
    I am trying to map transactions to the following categories: {", ".join(categories)}. if it does not belong to these categories, map it to either credit or debit. Note that by default, money is spent, so debit is the default category, not credit.

    The transaction is has the following details:
    - from_name: {from_name}
    - desc: {desc}

    What category does this transaction belong to? Only respond with the category name. Keep in mind that Jumbo is a supermarket, bouldering is a sport,
    and NS Groep is the dutch train network. All bol.com is mapped to frivolous. Gas stations (Tankstation in dutch) should be mapped to travel. Mobile gaming and boardgames are mapped to frivolous.
    Mobiele betaling is not something you can use to map, because I pay with my phone. If there is no from_name and it concerns a mobile payment, map it to debit. 
    Overstapservice maps to debit. If it contains a word like Boulder, then sports is the right category. Unive groene hart maps to debit. All insurances map to health insurance.
    
    
    An example response would be " Groceries, as this is a supermarket. "
    """

    model = "mistral:latest"

    # print(full_prompt)
    response = call_api(full_prompt, model)
    category = parse_response(response, categories)

    # print(f"[[{response}]] -> {category}")
    return category

@cli.command()
def ingest():
    """Ingest new bank data"""
    try:
        input_path = os.path.join('bankdata', 'ingested.csv')
        df = pl.read_csv(input_path)
        # Define regex patterns for automatic categorization
        category_patterns = [
            {'category': 'groceries', 'pattern': r'(?i)(jumbo|albert heijn|lidl|aldi|plus supermarkt|etos)'},
            {'category': 'sports', 'pattern': r'(?i)(bouldering|klimcentrum|sportschool|gym|boulderhal)'},
            {'category': 'travel', 'pattern': r'(?i)(ns groep|tankstation|shell|bp|esso)'},
            {'category': 'frivolous', 'pattern': r'(?i)(bol\.com|gaming|boardgame|bc burden)'}, 
            {'category': 'health insurance', 'pattern': r'(?i)(ditzo|asr)'},
            {'category': 'medical expenses', 'pattern': r'(?i)(infomedics)'},
            {'category': 'donations', 'pattern': r'(?i)(wnf|vrienden van xr)'},
            {'category': 'debit', 'pattern': r'(?i)(groene hart)'}
        ]

        # Create a new column with default value 'debit'
        df = df.with_columns(pl.lit('debit').alias('category'))

        # Apply each pattern and update category where matches are found
        for pattern in category_patterns:
            df = df.with_columns(
                pl.when(
                    pl.col('from_name').str.contains(pattern['pattern']) | 
                    pl.col('desc').str.contains(pattern['pattern'])
                )
                .then(pl.lit(pattern['category']))
                .otherwise(pl.col('category'))
                .alias('category')
            )


        # Get unique combinations of transaction details that don't have a category yet
        unique_transactions = df.filter(
            pl.col('category') == 'debit'
        ).select(
            ['from_name', 'desc']
        ).unique()

        # print(f"\nFound {unique_transactions.height} unique transaction patterns")
        # print("\nMapping transactions to categories...")

        # Map each unique combination to a category and create a new DataFrame with the results
        mapped_categories = []
        with click.progressbar(unique_transactions.iter_rows(), 
                             label='Mapping transactions',
                             length=unique_transactions.height) as progress_rows:
            for row in progress_rows:
                from_name, desc = row
                ai_category = map_to_categories(from_name, desc)
                mapped_categories.append({"from_name": from_name, "desc": desc, "ai_category": ai_category})
        
        # Create DataFrame with mapped categories
        mapped_df = pl.DataFrame(mapped_categories)
        
        # Update original DataFrame with AI categories
        df = df.join(
            mapped_df,
            on=['from_name', 'desc'],
            how='left'
        ).with_columns(
            pl.when(pl.col('category') == 'debit')
            .then(pl.col('category_right'))
            .otherwise(pl.col('category'))
            .alias('category')
        ).drop('category_right')

        print("Finished mapping transactions")    
        print(df.head())

        # Save processed DataFrame to CSV
        df.write_csv("bankdata/processed.csv")
        print("Successfully wrote processed data to bankdata/processed.csv")
    except Exception as e:
        raise PromptException(f"Error ingesting data: {str(e)}")

@cli.command()
def calculate():
    """Run calculations on bank data"""
    try:
        print("Running calculations...")
        # TODO: Implement calculation logic
    except Exception as e:
        raise PromptException(f"Error in calculations: {str(e)}")

if __name__ == '__main__':
    cli()
