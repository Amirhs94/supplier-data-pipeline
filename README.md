
# Project: Supplier Data Integration & Analysis Pipeline

## Objective
Parts Avatar is looking to integrate a new auto parts supplier to expand our inventory. We have received a sample data feed (`supplier_feed.csv`) containing their product stock levels and costs, along with a separate file (`product_metadata.csv`) that maps supplier part IDs to our internal product information.

Our goal is to build a reliable, automated pipeline to process this data, load it into a database, and perform an initial analysis to determine the viability of this supplier.

## The Challenge
The supplier's data feed is notoriously unreliable. It contains inconsistencies, missing values, and mixed data types that must be handled gracefully. Your task is to design and implement a small-scale ETL (Extract, Transform, Load) pipeline that is robust enough to handle these issues and produce clean, analytics-ready data.

## Datasets
* `data/supplier_feed.csv`: The raw, messy data from the new supplier.
* `data/product_metadata.csv`: Maps the supplier's parts to our internal system.

## Your Tasks
1.  **Extract & Transform:**
    * Write a Python script (`src/transform_data.py`) to read, clean, and standardize the `supplier_feed.csv` data.
    * **Problem-Solving:** You must make and document key decisions. For example: How do you handle "Low Stock"? How do you impute missing `cost_price` values? What is your strategy for standardizing the messy `entry_date` column? Justify your choices in this README.

2.  **Load:**
    * Create a simple SQLite database (`parts_avatar.db`).
    * Load the cleaned supplier data and the product metadata into two separate tables in the database. Ensure the data types are correct and consider setting up primary keys.

3.  **Analyze & Visualize:**
    * Write a Python script or a Jupyter Notebook to query the SQLite database and answer the following business questions:
        * What is the average cost price per product category?
        * Which top 5 parts have the highest stock levels right now?
        * How has the number of new parts entries from this supplier changed over time (on a monthly basis)?
    * Create at least two clear and informative visualizations (e.g., using Matplotlib, Seaborn, or Plotly) to present your findings.

4.  **Documentation:**
    * Update this `README.md` file to be a comprehensive report of your project.
    * Explain your data cleaning strategies and justify your decisions.
    * Describe the schema of your database tables.
    * Present your findings from the analysis, including the visualizations you created.
    * Provide clear instructions on how to run your entire pipeline from start to finish.

## Evaluation Criteria
* **Problem-Solving:** The logic and justification behind your data cleaning and transformation decisions.
* **Python & SQL Proficiency:** The quality, efficiency, and organization of your code.
* **Data Engineering Concepts:** The structure and robustness of your ETL pipeline.
* **Data Visualization & Communication:** The clarity and impact of your analysis and visualizations in the README report.

## Disclaimer: Data and Evaluation Criteria
Please be advised that the datasets utilized in this project are synthetically generated and intended for illustrative purposes only. Furthermore, they have been significantly reduced in terms of sample size and the number of features to streamline the exercise. They do not represent or correspond to any actual business data. The primary objective of this evaluation is to assess the problem-solving methodology and the strategic approach employed, not necessarily the best possible tailored solution for the data. 


## Report
---------------------------------------------

I made three python scripts: transform, load to db, and analyze.
The transform script tries to change the supplier and our data by:
Supplier used mixed formats like "Low Stock", "OOS", "1,200", "12.3.4", and "5k".
I created parse_stock_level()
Converted human labels → numeric:
"Low Stock" → 5
"Out of Stock" → 0
"In Stock" → 10
Removed commas and handled magnitude suffixes: "5k" → 5000, "3M" → 3,000,000.
Fixed malformed decimals: "12.3.4" → 12.34.
Cleaned formats such as "USD 35.5", "N/A", "23,000".
Converted to floats; set invalid or missing to NaN.
Imputed missing cost prices using the median cost within each category, ensuring more realistic estimates than global mean or zero-fill.
for the time and date i used cursor ai and chatgpt to know what is the date types used in the dataset. 
Supplier’s entry_date field had:
Excel serial numbers → converted using Excel epoch (1899-12-30).
UNIX timestamps → converted using pd.to_datetime(..., unit='s').
ISO timestamps with "T" separator → normalized to "YYYY-MM-DD HH:MM:SS".
Invalid or empty dates were set to NaT.
Finally we did a left joint so that we do not lose any of the data of the supplier and put our database marks on them. The result was a clean supplier csv that was ready to be uploaded into our database. 
## Database
In the load to db file I created a lightweight SQLite DB parts_avatar.db with two tables: product_metadata and supplier-clean
and added the cleaned csv into these tables. 

## Analyze
I used src/analyze.py to answer business questions. I uploaded the results in this repo. to quickly answer the questions:
1 - What is the average cost price per product category? 
Suspension	233.04317433516300
Brakes	229.97962281992000
Filters	229.86967819404400
Engine	228.69060179640700
Electronics	226.97163796814500
HVAC	226.68700486618000
Exhaust	224.52987508838100

2 - Which top 5 parts have the highest stock levels right now?
supplier_part_id	category	stock_level_clean
SP-471		Electronics	493.0
SP-200		HVAC	492.0
SP-345		Electronics	492.0
SP-305		Suspension	490.0
SP-228		Electronics	489.0

3 - How has the number of new parts entries from this supplier changed over time (on a monthly basis)?
month	new_parts
2024-01	1593
2024-02	1478
2024-03	1607
2024-04	1546
2024-05	1594
2024-06	1590
2024-07	1612
2024-08	1677
2024-09	1555
2024-10	1647
2024-11	1578
2024-12	1614
2025-01	1565
2025-02	1395
2025-03	1647
2025-04	1559
2025-05	1630
2025-06	1536
2025-07	1577

I made two report graphs one is for this trend and the other one for the cost per category. 
In order to run this data set you need to run Transform.py first then load to db then analyze.py. This ensures that the previous step has done it's job. we can automate this process so that whenever a new csv of a new supplier comes to our office, the automation runs these steps and stores it in our newly created database. 
