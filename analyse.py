import pandas as pd

# Load data from CSV files
df_properties = pd.read_csv('properties.csv')
df_private_sellers = pd.read_csv('private_seller_properties.csv')

# Combine both datasets into one if needed
df_all_properties = pd.concat([df_properties, df_private_sellers], ignore_index=True)


# Summary statistics
price_stats = df_all_properties['Price'].describe()
print("Summary Statistics of Property Prices:")
print(price_stats)


