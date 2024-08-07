"""Functions for interacting with the database."""

from os import environ as ENV

from psycopg import connect, Connection, OperationalError
from psycopg.rows import dict_row
import streamlit as st
import pandas as pd


@st.cache_resource
def get_connection() -> Connection:
    """Creates and returns a connection to the database."""

    print("Connecting to database...")
    return connect(
        port=ENV["DB_PORT"],
        dbname=ENV["DB_NAME"],
        host=ENV["DB_ENDPOINT"],
        user=ENV["DB_USER"],
        password=ENV["DB_PASSWORD"],
        row_factory=dict_row
    )


def check_connection(_conn: Connection) -> Connection:
    """Check if the connection is still alive, if not,
    reestablishes and returns a connection."""

    try:
        with _conn.cursor() as cur:
            cur.execute("SELECT 1")
    except OperationalError:
        print("Reconnecting to the database...")
        _conn = get_connection()
    return _conn


@st.cache_data(ttl="1hr")
def get_popular_tracks(_conn: Connection, timeframe: str) -> pd.DataFrame:
    """Returns the 5 most sold tracks in the database."""

    print("Collating most popular tracks...")
    query = f"""
        SELECT T.title, A.name, COUNT(track_purchase_id) AS copies_sold, T.url as url
        FROM track_purchase AS TP
        JOIN track AS T
        USING(track_id)
        JOIN artist as A
        USING(artist_id)
        WHERE CURRENT_TIMESTAMP < TP.timestamp + INTERVAL '{timeframe}'
        GROUP BY T.title, A.name, T.url
        ORDER BY copies_sold DESC
        LIMIT 5
        ;
        """
    with _conn.cursor() as cur:
        cur.execute(query)
        data = cur.fetchall()
    return pd.DataFrame(data)


@st.cache_data(ttl="1hr")
def get_popular_albums(_conn: Connection, timeframe: str) -> pd.DataFrame:
    """Returns the 5 most sold albums in the database."""

    print("Collating most popular albums...")
    query = f"""
        SELECT AB.title, AT.name, COUNT(*) AS copies_sold, AB.url as url
        FROM album_purchase AS AP
        JOIN album AS AB
        USING(album_id)
        JOIN artist as AT
        USING(artist_id)
        WHERE CURRENT_TIMESTAMP < AP.timestamp + INTERVAL '{timeframe}'
        GROUP BY AB.title, AT.name, AB.url
        ORDER BY copies_sold DESC
        LIMIT 5
        ;
        """

    with _conn.cursor() as cur:
        cur.execute(query)
        data = cur.fetchall()

    return pd.DataFrame(data)


@st.cache_data(ttl="1hr")
def get_popular_artists(_conn: Connection, timeframe) -> pd.DataFrame:
    """Returns the 5 artists with the most sales in the database."""

    print("Collating most popular artists...")
    query = f"""
            SELECT A.artist_id, A.name, COUNT(DISTINCT AP.album_purchase_id) AS album_sales, COUNT(DISTINCT TP.track_purchase_id) AS track_sales, COUNT(DISTINCT AP.album_purchase_id) + COUNT(DISTINCT TP.track_purchase_id) AS total_sales, A.url as artist_url
            FROM
                artist AS A
            LEFT JOIN
                album AS AB ON A.artist_id = AB.artist_id
            LEFT JOIN
                album_purchase AS AP ON AB.album_id = AP.album_id
            LEFT JOIN
                track AS T ON A.artist_id = T.artist_id
            LEFT JOIN
                track_purchase AS TP ON T.track_id = TP.track_id
            WHERE
                CURRENT_TIMESTAMP < AP.timestamp + INTERVAL '{timeframe}'
            GROUP BY
                A.artist_id, A.name
            ORDER BY
                total_sales DESC
            LIMIT 5;
        ;
        """

    with _conn.cursor() as cur:
        cur.execute(query)
        data = cur.fetchall()

    return pd.DataFrame(data)


@st.cache_data(ttl="1hr")
def get_all_artists(_conn: Connection):
    """Returns all artists."""

    print("Collecting artists...")

    query = """
        SELECT name
        FROM artist
        ;
        """

    with _conn.cursor() as cur:
        cur.execute(query)
        data = cur.fetchall()
    return sorted([d["name"] for d in data])


@st.cache_data(ttl="1hr")
def get_sales_by_tag(_conn: Connection, timeframe: str) -> pd.DataFrame:
    """Returns the top 5 genre/tag by sales."""

    print("Counting sales by tag...")
    query = f"""
        SELECT t.name, SUM(album_table.album_total + track_table.track_total) AS total_sales
    FROM tag t
    INNER JOIN (
        SELECT ata.tag_id, COUNT(DISTINCT ap.album_purchase_id) as album_total
        FROM album_tag_assignment ata
        INNER JOIN album_purchase ap
        ON ata.album_id = ap.album_id
        WHERE CURRENT_TIMESTAMP < AP.timestamp + INTERVAL '{timeframe}'
        GROUP BY ata.tag_id)
        album_table ON album_table.tag_id = t.tag_id
    INNER JOIN (
        SELECT tta.tag_id, COUNT(DISTINCT tp.track_purchase_id) as track_total
        FROM track_tag_assignment tta
        INNER JOIN track_purchase tp
        ON tta.track_id = tp.track_id
        WHERE CURRENT_TIMESTAMP < TP.timestamp + INTERVAL '{timeframe}'
        GROUP BY tta.tag_id)
        track_table ON track_table.tag_id = t.tag_id
    GROUP BY t.tag_id
    ORDER BY total_sales DESC
    LIMIT 5
    ;
    """

    with _conn.cursor() as cur:
        cur.execute(query)
        data = cur.fetchall()

    return pd.DataFrame(data)


@st.cache_data(ttl="1hr")
def get_all_tags(_conn: Connection) -> list:
    """Returns all tags."""

    print("Collecting tags...")

    query = """
        SELECT name
        FROM tag
        ;
        """

    with _conn.cursor() as cur:
        cur.execute(query)
        data = cur.fetchall()
    return sorted([d["name"] for d in data])


@st.cache_data(ttl="1hr")
def get_sales_by_country(_conn: Connection) -> list[dict]:
    """Returns the sales for each country."""

    print("Counting sales by country...")
    query = """
        SELECT C.name as name, CAST(SUM(album_table.album_total + track_table.track_total) AS FLOAT) AS total_sales
        FROM country C
        INNER JOIN (
            SELECT AP.country_id, COUNT(DISTINCT AP.album_purchase_id) album_total
            FROM album_purchase AP
            GROUP BY AP.country_id
        ) album_table ON album_table.country_id = C.country_id
        INNER JOIN  (
            SELECT TP.country_id, COUNT(DISTINCT TP.track_purchase_id) track_total
            FROM track_purchase TP
            GROUP BY TP.country_id
        ) track_table ON track_table.country_id = C.country_id
        GROUP BY C.name
        ORDER BY total_sales DESC
        ;
        """

    with _conn.cursor() as cur:
        cur.execute(query)
        data = cur.fetchall()

    return data


@st.cache_data(ttl="1hr")
def get_all_album_titles(_conn: Connection):
    """Returns all album titles."""

    print("Getting album titles...")
    query = """
            SELECT title
            FROM album
            ;
            """

    with _conn.cursor() as cur:
        cur.execute(query)
        data = cur.fetchall()

    return sorted([d["title"] for d in data])


@st.cache_data(ttl="1hr")
def get_track_sales_by_artist(_conn: Connection, artist: str):
    """Returns all track info for a given artist."""

    print(f"Counting track sales for artist {artist}...")
    query = """
            SELECT DATE_TRUNC('hour', TP.timestamp) AS hour, COUNT(DISTINCT TP.track_purchase_id) as sales
            FROM artist AS A
            INNER JOIN track as T
            USING(artist_id)
            INNER JOIN track_purchase as TP
            USING(track_id)
            WHERE A.name = %s
            GROUP BY hour
            ;
        """

    with _conn.cursor() as cur:
        cur.execute(query, (artist, ))
        data = cur.fetchall()

    return pd.DataFrame(data)


@st.cache_data(ttl="1hr")
def get_album_sales_by_artist(_conn: Connection, artist: str):
    """Returns all album info for a given artist."""

    print(f"Counting album sales for artist {artist}...")
    query = """
            SELECT DATE_TRUNC('hour', AP.timestamp) AS hour, COUNT(DISTINCT AP.album_purchase_id) as sales
            FROM artist AS A
            INNER JOIN album as AB
            USING(artist_id)
            INNER JOIN album_purchase as AP
            USING(album_id)
            WHERE A.name = %s
            GROUP BY hour
            ;
        """

    with _conn.cursor() as cur:
        cur.execute(query, (artist, ))
        data = cur.fetchall()

    return pd.DataFrame(data)


@st.cache_data(ttl="1hr")
def get_sales(_conn: Connection) -> pd.DataFrame:
    """Returns all sales data."""

    query = """
        SELECT A.name, COUNT(DISTINCT AP.album_purchase_id) AS album_sales, COUNT(DISTINCT TP.track_purchase_id) AS track_sales
        FROM artist as A
        LEFT JOIN album AS AB
        ON AB.artist_id = A.artist_id
        LEFT JOIN album_purchase AS AP
        ON AP.album_id = AB.album_id
        LEFT JOIN track as T
        ON T.artist_id = A.artist_id
        LEFT JOIN track_purchase as TP
        ON TP.track_id = T.track_id
        GROUP BY A.name;"""
    with _conn.cursor() as cur:
        cur.execute(query)
        data = cur.fetchall()
    return pd.DataFrame(data)


@st.cache_data(ttl="1hr")
def get_all_tag_names(_conn: Connection) -> list[str]:
    """Returns all tag names."""

    print("Getting tag names...")
    query = """
        SELECT T.name
        FROM tag as T
        ;
        """

    with _conn.cursor() as cur:
        cur.execute(query)
        data = cur.fetchall()

    return pd.DataFrame(data)


@st.cache_data(ttl="1hr")
def get_sales_for_chosen_artists(sales_data: pd.DataFrame, artist_names: list[str]):
    """Returns sales data only for passed artists."""
    return sales_data[sales_data["name"].isin(artist_names)]


@st.cache_data(ttl="1hr")
def get_track_sales_by_tag(_conn: Connection, tag_name: str) -> pd.DataFrame:
    """Returns all sales for a given tag."""

    print(f"Counting tag sales for tag {tag_name}...")
    query = """
        SELECT DATE_TRUNC('hour', TP.timestamp) AS hour, COUNT(DISTINCT TP.track_purchase_id) as sales
        FROM tag AS T
        INNER JOIN track_tag_assignment as TTA
        USING(tag_id)
        INNER JOIN track_purchase as TP
        USING(track_id)
        WHERE T.name = %s 
        GROUP BY hour
        ;
        """

    with _conn.cursor() as cur:
        cur.execute(query, (tag_name, ))
        data = cur.fetchall()

    return pd.DataFrame(data)


@st.cache_data(ttl="1hr")
def get_album_sales_by_tag(_conn: Connection, tag_name: str) -> pd.DataFrame:
    """Returns all sales for a given tag."""

    print(f"Counting tag sales for tag {tag_name}...")
    query = """
        SELECT DATE_TRUNC('hour', AP.timestamp) AS hour, COUNT(DISTINCT AP.album_purchase_id) as sales
        FROM tag AS T
        INNER JOIN album_tag_assignment as ATA
        USING (tag_id)
        INNER JOIN album_purchase as AP
        USING (album_id)
        WHERE T.name = %s
        GROUP BY hour
        ;
        """

    with _conn.cursor() as cur:
        cur.execute(query, (tag_name, ))
        data = cur.fetchall()

    return pd.DataFrame(data)
