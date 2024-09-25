import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import scipy.stats as stats
import time
import numpy as np
import streamlit as st
import io
from io import StringIO
from scipy.stats.mstats import winsorize
import pandas as pd
import nbformat

# Function to import CSV from BytesIO object.
def import_notebook(uploaded_file):
    """Read a CSV file from the uploaded file."""
    try:
        df = pd.read_csv(uploaded_file)  # Read directly from the uploaded file
    except Exception as e:
        st.error(f"Error reading the CSV file: {e}")
        return None
    return df

def preprocess_data(df, notebook_cells, columns_to_drop):
    start_time = time.time()
    initial_rows = len(df)
    removed_rows_all = removed_rows_na = 0

    if columns_to_drop:
        df.drop(columns_to_drop, axis=1, inplace=True)
        st.success(f"Dropped columns: {', '.join(columns_to_drop)}")
        notebook_cells.append(nbformat.v4.new_markdown_cell(f"## Dropped Columns: {', '.join(columns_to_drop)}"))

    try:
        df.dropna(how='all', inplace=True)
        removed_rows_all = initial_rows - len(df)
    except Exception as e:
        st.error(f"Error removing rows with all missing values: {e}")

    try:
        df.replace('', np.nan, inplace=True)
        initial_rows_after_all = len(df)
        df.dropna(inplace=True)
        removed_rows_na = initial_rows_after_all - len(df)
    except Exception as e:
        st.error(f"Error removing rows with missing values: {e}")

    try:
        numerical_cols = df.select_dtypes(include=['int64', 'float64']).columns
        df[numerical_cols] = df[numerical_cols].fillna(df[numerical_cols].mean())
        imputed_numerical = df[numerical_cols].isnull().sum().sum()
    except Exception as e:
        st.error(f"Error imputing missing numerical values: {e}")
        imputed_numerical = 0

    try:
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            df[col] = df[col].fillna(df[col].mode()[0])
        imputed_categorical = df[categorical_cols].isnull().sum().sum()
    except Exception as e:
        st.error(f"Error imputing missing categorical values: {e}")
        imputed_categorical = 0

    try:
        initial_rows = len(df)
        df.drop_duplicates(inplace=True)
        removed_duplicates = initial_rows - len(df)
    except Exception as e:
        st.error(f"Error removing duplicate rows: {e}")
        removed_duplicates = 0

    try:
        for col in categorical_cols:
            if df[col].nunique() / len(df) < 0.5:
                df[col] = df[col].astype('category')
    except Exception as e:
        st.error(f"Error converting columns to category type: {e}")

    winsorized_rows = []
    winsorize_limits = [0.05, 0.05]
    try:
        for col in numerical_cols:
            original_data = df[col].copy()
            df[col] = winsorize(df[col], limits=winsorize_limits)
            winsorized_diff = (original_data != df[col]).sum()
            if winsorized_diff > 0:
                winsorized_rows.append(winsorized_diff)
    except Exception as e:
        st.error(f"Error winsorizing data: {e}")

    preprocess_time = time.time() - start_time
    st.write(f"Preprocessing took {preprocess_time:.2f} seconds")

    notebook_cells.append(nbformat.v4.new_markdown_cell("## Preprocessing Summary"))
    notebook_cells.append(nbformat.v4.new_code_cell(
        "initial_rows = len(df)\n"
        "df.dropna(how='all', inplace=True)\n"
        "df.replace('', np.nan, inplace=True)\n"
        "df.dropna(inplace=True)\n"
        "removed_rows_all = initial_rows - len(df)\n\n"
        "numerical_cols = df.select_dtypes(include=['int64', 'float64']).columns\n"
        "df[numerical_cols] = df[numerical_cols].fillna(df[numerical_cols].mean())\n"
        "imputed_numerical = df[numerical_cols].isnull().sum().sum()\n\n"
        "categorical_cols = df.select_dtypes(include=['object']).columns\n"
        "for col in categorical_cols:\n"
        "    df[col] = df[col].fillna(df[col].mode()[0])\n"
        "imputed_categorical = df[categorical_cols].isnull().sum().sum()\n\n"
        "initial_rows = len(df)\n"
        "df.drop_duplicates(inplace=True)\n"
        "removed_duplicates = initial_rows - len(df)\n\n"
        "for col in categorical_cols:\n"
        "    if df[col].nunique() / len(df) < 0.5:\n"
        "        df[col] = df[col].astype('category')\n\n"
        "from scipy.stats.mstats import winsorize\n"
        "for col in numerical_cols:\n"
        "    df[col] = winsorize(df[col], limits=[0.05, 0.05])"
    ))

    notebook_cells.append(nbformat.v4.new_markdown_cell(f"- Removed {removed_rows_all} rows with all missing values."))
    notebook_cells.append(nbformat.v4.new_markdown_cell(f"- Removed {removed_rows_na} rows with missing values."))
    imputation_summary = [
        f"- Imputed {imputed_numerical} missing numerical values." if imputed_numerical > 0 else "- No missing numerical values imputed.",
        f"- Imputed {imputed_categorical} missing categorical values." if imputed_categorical > 0 else "- No missing categorical values imputed.",
        f"- Removed {removed_duplicates} duplicate rows." if removed_duplicates > 0 else "- No duplicate rows removed.",
        f"- Winsorized: {len(winsorized_rows)} rows, {len(numerical_cols)} cols using limits {winsorize_limits}."
    ]
    for summary in imputation_summary:
        st.markdown(summary)

    st.write("**Data Information**")
    buffer = StringIO()
    df.info(buf=buffer)
    s = buffer.getvalue()
    st.text(s)
    notebook_cells.append(nbformat.v4.new_markdown_cell("## Data Information"))
    notebook_cells.append(nbformat.v4.new_code_cell("df.info()"))

    return df, categorical_cols, numerical_cols


# Function for univariate analysis
def univariate_analysis(df, categorical_cols, numerical_cols, notebook_cells):
    st.write("**Univariate Analysis**")

    # Plot for numerical columns
    for col in numerical_cols:
        st.write(f"### Distribution of {col}")
        fig, ax = plt.subplots()
        sns.histplot(df[col], kde=True, ax=ax)
        st.pyplot(fig)
        notebook_cells.append(nbformat.v4.new_code_cell(f"sns.histplot(df['{col}'], kde=True)"))

    # Plot for categorical columns
    for col in categorical_cols:
        st.write(f"### Count plot of {col}")
        fig, ax = plt.subplots()
        sns.countplot(x=df[col], ax=ax)
        st.pyplot(fig)
        notebook_cells.append(nbformat.v4.new_code_cell(f"sns.countplot(x=df['{col}'])"))


# Function for multivariate analysis
def multivariate_analysis(df, categorical_cols, numerical_cols, notebook_cells):
    st.write("**Multivariate Analysis**")

    # Pairplot for numerical columns
    if len(numerical_cols) > 1:
        st.write("### Pairplot of numerical columns")
        fig = sns.pairplot(df[numerical_cols])
        st.pyplot(fig)
        notebook_cells.append(nbformat.v4.new_code_cell("sns.pairplot(df[numerical_cols])"))

    # Heatmap of correlations for numerical columns
    st.write("### Correlation heatmap")
    correlation_matrix = df[numerical_cols].corr()
    fig, ax = plt.subplots()
    sns.heatmap(correlation_matrix, annot=True, fmt=".2f", cmap='coolwarm', ax=ax)
    st.pyplot(fig)
    notebook_cells.append(nbformat.v4.new_code_cell("sns.heatmap(correlation_matrix, annot=True, fmt='.2f', cmap='coolwarm')"))

    # Clustering
    clustering_analysis(df, numerical_cols, notebook_cells)

def clustering_analysis(df, numerical_cols, notebook_cells):
    st.write("### Clustering Analysis")
    
    # KMeans Clustering
    num_clusters = st.slider("Select number of clusters for KMeans", min_value=1, max_value=10, value=3)
    kmeans = KMeans(n_clusters=num_clusters, random_state=42)
    df['Cluster'] = kmeans.fit_predict(df[numerical_cols])

    # Visualizing the clusters
    st.write(f"#### KMeans Clustering with {num_clusters} Clusters")
    fig, ax = plt.subplots()
    sns.scatterplot(data=df, x=numerical_cols[0], y=numerical_cols[1], hue='Cluster', palette='viridis', ax=ax)
    st.pyplot(fig)
    notebook_cells.append(nbformat.v4.new_code_cell(f"kmeans = KMeans(n_clusters={num_clusters}, random_state=42)\n"
                                                    f"df['Cluster'] = kmeans.fit_predict(df[numerical_cols])\n"
                                                    f"sns.scatterplot(data=df, x='{numerical_cols[0]}', y='{numerical_cols[1]}', hue='Cluster', palette='viridis')"))


# Function for statistical analysis
def statistical_analysis(df, numerical_cols, notebook_cells):
    st.write("**Statistical Analysis**")

    # Descriptive statistics
    st.write("### Descriptive Statistics")
    descriptive_stats = df.describe()
    st.write(descriptive_stats)
    notebook_cells.append(nbformat.v4.new_code_cell("df.describe()"))

    # Shapiro-Wilk test for normality
    st.write("### Shapiro-Wilk Test for Normality")
    normality_results = []

    for col in numerical_cols:
        stat, p_value = stats.shapiro(df[col].dropna())
        normality_results.append({
            "Column": col,
            "Statistic": f"{stat:.3f}",
            "p-value": f"{p_value:.3f}",
            "Normal Distribution": "Yes" if p_value > 0.05 else "No"
        })
        notebook_cells.append(nbformat.v4.new_code_cell(
            f"stat, p_value = stats.shapiro(df['{col}'].dropna())\n"
            f"print(f'**{col}**: Statistics={{stat:.3f}}, p-value={{p_value:.3f}}')"
        ))

    # Display normality results as a table
    st.table(pd.DataFrame(normality_results))

    # Correlation analysis
    st.write("### Correlation Analysis")
    correlation_matrix = df[numerical_cols].corr()

    # Display correlation matrix as a table
    st.write("#### Correlation Coefficients")
    st.table(correlation_matrix)

    # Optional: Display a heatmap of correlations
    fig, ax = plt.subplots()
    sns.heatmap(correlation_matrix, annot=True, fmt=".2f", cmap='coolwarm', ax=ax)
    st.pyplot(fig)
    notebook_cells.append(nbformat.v4.new_code_cell("sns.heatmap(correlation_matrix, annot=True, fmt='.2f', cmap='coolwarm')"))

# Main function to run the Streamlit app
def main():
    st.title("Data Analysis App")
    
    # Instructions
    st.write("This app allows you to upload a CSV file, preprocess the data, and perform various analyses such as univariate, multivariate, and statistical analysis.")

    # Upload CSV file
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
    if uploaded_file is not None:
        with st.spinner("Loading data..."):
            df = import_notebook(uploaded_file)
            if df is None:
                return  # Exit if there's an error reading the file

            notebook_cells = []

            # Preprocess the data
            columns_to_drop = st.multiselect("Select columns to drop", df.columns.tolist())
            df, categorical_cols, numerical_cols = preprocess_data(df, notebook_cells, columns_to_drop)

            # Add download button for cleaned data
            if st.button("Download Cleaned Dataset"):
                cleaned_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(label="Download Cleaned Data",
                                   data=cleaned_data,
                                   file_name='cleaned_data.csv',
                                   mime='text/csv')
            
            # Univariate analysis
            if st.checkbox("Univariate Analysis"):
                univariate_analysis(df, categorical_cols, numerical_cols, notebook_cells)

            # Multivariate analysis
            if st.checkbox("Multivariate Analysis"):
                multivariate_analysis(df, categorical_cols, numerical_cols, notebook_cells)

            # Statistical analysis
            if st.checkbox("Statistical Analysis"):
                statistical_analysis(df, numerical_cols, notebook_cells)

            # Export notebook cells
            if st.button("Export Notebook"):
                notebook = nbformat.v4.new_notebook()
                notebook.cells = notebook_cells
                with open("analysis_notebook.ipynb", "w", encoding='utf-8') as f:  # Open in text mode with utf-8 encoding
                    nbformat.write(notebook, f)
                st.success("Notebook exported successfully!")

if __name__ == "__main__":
    main()
