"""Charts used in dashboard."""

import altair as alt
import streamlit as st
from pandas import DataFrame


@st.cache_data
def get_most_copies_sold_chart(data: DataFrame) -> alt.Chart:
    """Returns a bar chart of most copies sold when passed tracks/albums data."""

    return alt.Chart(data).mark_bar().encode(
        x=alt.X("title"),
        y=alt.Y("copies_sold:N")
    )


@st.cache_data
def get_most_popular_chart(data: DataFrame) -> alt.Chart:
    """Returns a bar chart of popular artists/tags and their sales."""

    return alt.Chart(data).mark_bar().encode(
        x=alt.X("name"),
        y=alt.Y("total_sales:N")
    )