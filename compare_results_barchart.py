#!/usr/bin/env python3
"""
Generate an interactive bar chart comparing Precision, Recall, and F1-score for each method in results.csv.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

# Path to results.csv
csv_path = os.path.join("toFinalReport", "Results", "results.csv")

# Read results.csv
try:
    df = pd.read_csv(csv_path)
except Exception as e:
    print(f"Error reading {csv_path}: {e}")
    exit(1)

# Check required columns
required_cols = {"DataSet", "Precision", "Recall", "F1-score"}
if not required_cols.issubset(df.columns):
    print(f"Missing columns in {csv_path}. Required: {required_cols}")
    exit(1)

# Melt dataframe for grouped bar chart

# Add Evaluated Pages to DataSet label for grouped bar chart
if "Evaluated Pages" in df.columns:
    df["DataSet_with_pages"] = df.apply(
        lambda row: f"{row['DataSet']} ({int(row['Evaluated Pages'])})", axis=1
    )
    melted = df.melt(id_vars=["DataSet_with_pages"], value_vars=["Precision", "Recall", "F1-score"],
                     var_name="Metric", value_name="Score")
    x_col_grouped = "DataSet_with_pages"
    x_label_grouped = "Method (Evaluated Pages)"
else:
    melted = df.melt(id_vars=["DataSet"], value_vars=["Precision", "Recall", "F1-score"],
                     var_name="Metric", value_name="Score")
    x_col_grouped = "DataSet"
    x_label_grouped = "Method"

# Create interactive grouped bar chart
fig = px.bar(
    melted,
    x=x_col_grouped,
    y="Score",
    color="Metric",
    barmode="group",
    text="Score",
    title="Keyword Extraction Performance Comparison",
    labels={x_col_grouped: x_label_grouped, "Score": "Score"},
    height=600,
    width=827  # A4 width in pixels (8.27 inches * 100 dpi)
)

fig.update_traces(texttemplate='%{text:.3f}', textposition='outside')
fig.update_layout(
    xaxis_title="Method",
    yaxis_title="Score",
    legend_title="Metric",
    yaxis=dict(range=[0, 1]),
    margin=dict(l=40, r=40, t=80, b=120),
    bargap=0.15,
    bargroupgap=0.1,
)

# Move legend inside chart area (top-right)
fig.update_layout(
    legend=dict(
        x=0.98,
        y=0.98,
        xanchor="right",
        yanchor="top",
        bgcolor="rgba(255,255,255,0.7)",
        bordercolor="black",
        borderwidth=1
    )
)

# Show Evaluated Pages in legend title
if "Evaluated Pages" in df.columns:
    evaluated_pages = int(df["Evaluated Pages"].sum())
    fig.update_layout(
        legend_title_text=f"Metric (Evaluated Pages: {evaluated_pages})"
    )


# Save as PNG
png_path = os.path.join("toFinalReport", "Results", "compare_results_barchart.png")
try:
    fig.write_image(png_path)
    print(f"Chart saved as PNG: {png_path}")
except Exception as e:
    print("Error saving PNG. You may need to install kaleido:")
    print("pip install -U kaleido")
    print(f"Error details: {e}")

# Create and save F1-score only bar chart
df["Dataset"] = df["DataSet"].str.split("_").str[-1]
df["Method"] = df["DataSet"].str.split("_").str[0]

# Add Evaluated Pages to DataSet label
if "Evaluated Pages" in df.columns:
    df["DataSet_with_pages"] = df.apply(
        lambda row: f"{row['DataSet']} ({int(row['Evaluated Pages'])})", axis=1
    )
    x_col = "DataSet_with_pages"
    x_label = "Method (Evaluated Pages)"
else:
    x_col = "DataSet"
    x_label = "Method"

fig_f1 = px.bar(
    df,
    x=x_col,
    y="F1-score",
    color="Dataset",
    text="F1-score",
    title="Keyword Extraction F1-score Comparison",
    labels={x_col: x_label, "F1-score": "F1-score", "Dataset": "Dataset"},
    height=600,
    width=827,
)
fig_f1.update_traces(texttemplate='%{text:.3f}', textposition='outside')
fig_f1.update_layout(
    xaxis_title="Method",
    yaxis_title="F1-score",
    yaxis=dict(range=[0, 1]),
    margin=dict(l=40, r=40, t=80, b=120),
    bargap=0.15,
)

# Move legend inside chart area (top-right)
fig_f1.update_layout(
    legend=dict(
        x=0.98,
        y=0.98,
        xanchor="right",
        yanchor="top",
        bgcolor="rgba(255,255,255,0.7)",
        bordercolor="black",
        borderwidth=1,
    )
)

# Show Evaluated Pages in legend title
if "Evaluated Pages" in df.columns:
    evaluated_pages = int(df["Evaluated Pages"].sum())
    fig_f1.update_layout(
        legend_title_text=f"Dataset (Evaluated Pages: {evaluated_pages})"
    )

png_f1_path = os.path.join("toFinalReport", "Results", "compare_results_f1_barchart.png")
try:
    fig_f1.write_image(png_f1_path)
    print(f"F1-score chart saved as PNG: {png_f1_path}")
except Exception as e:
    print("Error saving F1-score PNG. You may need to install kaleido:")
    print("pip install -U kaleido")
    print(f"Error details: {e}")
